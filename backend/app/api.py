from pathlib import Path
import csv, io
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from app.db import get_db
from app.models import Supplier, PurchaseOrder, POItem, Invoice, InvoiceItem, AuditLog
from app.schemas import InvoiceOut, POOut, DecisionIn, DashboardOut
from app.services.document import validate_upload, extract_text_bytes
from app.services.storage import save_file, read_file, delete_file
from app.services.extraction import extract_invoice
from app.services.validation import validate_invoice
from app.services.explanation import explain
from app.services.seed import seed_demo

router = APIRouter()


def invoice_query(db):
    return db.query(Invoice).options(
        selectinload(Invoice.items), selectinload(Invoice.validations)
    )


def po_to_out(po):
    return POOut(
        id=po.id,
        po_number=po.po_number,
        currency=po.currency,
        status=po.status,
        supplier_name=po.supplier.name,
        items=po.items,
    )


@router.post("/demo/seed")
def seed(db: Session = Depends(get_db)):
    return {"created_purchase_orders": seed_demo(db), "message": "Demo data ready"}


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)):
    total = db.query(Invoice).count()
    auto = db.query(Invoice).filter(Invoice.status == "AUTO_APPROVED").count()
    review = db.query(Invoice).filter(Invoice.status == "REVIEW_REQUIRED").count()
    rejected = db.query(Invoice).filter(Invoice.status == "REJECTED").count()
    value = db.query(func.coalesce(func.sum(Invoice.total), 0)).scalar() or 0
    exceptions = db.query(Invoice).filter(Invoice.risk_score > 0).count()
    return DashboardOut(
        total_invoices=total,
        auto_approved=auto,
        review_required=review,
        rejected=rejected,
        total_value=round(float(value), 2),
        exception_rate=round((exceptions / total * 100) if total else 0, 1),
    )


@router.get("/purchase-orders", response_model=list[POOut])
def purchase_orders(db: Session = Depends(get_db)):
    pos = (
        db.query(PurchaseOrder)
        .options(selectinload(PurchaseOrder.supplier), selectinload(PurchaseOrder.items))
        .order_by(PurchaseOrder.id.desc())
        .all()
    )
    return [po_to_out(x) for x in pos]


@router.post("/purchase-orders/import-csv")
async def import_po_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = (await file.read()).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(raw)))
    created = 0
    for r in rows:
        required = ["po_number", "supplier", "description", "quantity", "unit_price"]
        if not all(r.get(k) for k in required):
            raise HTTPException(400, f"CSV requires columns: {', '.join(required)}")
        po = db.query(PurchaseOrder).filter_by(po_number=r["po_number"].strip()).first()
        if not po:
            supplier_name = r["supplier"].strip()
            supplier = db.query(Supplier).filter_by(name=supplier_name).first()
            if not supplier:
                supplier = Supplier(name=supplier_name)
                db.add(supplier)
                db.flush()
            po = PurchaseOrder(
                po_number=r["po_number"].strip(),
                supplier=supplier,
                currency=(r.get("currency") or "USD").strip(),
                status=(r.get("status") or "OPEN").strip(),
            )
            db.add(po)
            db.flush()
            created += 1
        po.items.append(
            POItem(
                sku=(r.get("sku") or None),
                description=r["description"].strip(),
                quantity=float(r["quantity"]),
                unit_price=float(r["unit_price"]),
            )
        )
    db.commit()
    return {"created_purchase_orders": created, "rows": len(rows)}


@router.get("/invoices", response_model=list[InvoiceOut])
def invoices(db: Session = Depends(get_db)):
    return invoice_query(db).order_by(Invoice.id.desc()).all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceOut)
def invoice(invoice_id: int, db: Session = Depends(get_db)):
    obj = invoice_query(db).filter(Invoice.id == invoice_id).first()
    if not obj:
        raise HTTPException(404, "Invoice not found")
    return obj


@router.get("/invoices/{invoice_id}/file")
def invoice_file(invoice_id: int, db: Session = Depends(get_db)):
    obj = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not obj:
        raise HTTPException(404, "Invoice not found")
    try:
        content = read_file(obj.file_path)
    except FileNotFoundError:
        raise HTTPException(404, "Stored invoice file not found")
    except Exception as exc:
        raise HTTPException(502, f"Could not retrieve stored invoice: {exc}")
    ext = Path(obj.original_filename).suffix.lower()
    media_type = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(ext, "application/octet-stream")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{obj.original_filename}"'},
    )


@router.post("/invoices/upload", response_model=InvoiceOut)
async def upload_invoice(file: UploadFile = File(...), db: Session = Depends(get_db)):
    filename = file.filename or "invoice.pdf"
    content = await file.read()
    try:
        validate_upload(filename, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    storage_ref = ""
    try:
        # Extract before cloud upload so obviously unreadable documents do not
        # consume persistent storage.
        text, used_ocr = extract_text_bytes(filename, content)
        if len(text.strip()) < 10:
            raise ValueError(
                "Could not extract readable text. If this is a scanned invoice, install Tesseract OCR."
            )

        data, provider = extract_invoice(text)
        storage_ref = save_file(filename, content)

        obj = Invoice(
            invoice_number=data.invoice_number,
            po_number=data.po_number,
            supplier_name=data.supplier,
            invoice_date=data.invoice_date,
            currency=data.currency,
            subtotal=data.subtotal,
            tax=data.tax,
            total=data.total,
            file_path=storage_ref,
            original_filename=filename,
            extracted_text=text,
            raw_extraction=data.model_dump(mode="json"),
            extraction_provider=provider,
        )
        for item in data.items:
            obj.items.append(InvoiceItem(**item.model_dump()))
        db.add(obj)
        db.flush()

        _, failures = validate_invoice(db, obj)
        obj.explanation, obj.recommendation = explain(obj, failures)
        db.add(
            AuditLog(
                invoice_id=obj.id,
                actor="system",
                action="VALIDATED",
                new_status=obj.status,
                note=f"provider={provider}; ocr={used_ocr}; risk={obj.risk_score}",
            )
        )
        db.commit()
        return invoice_query(db).filter(Invoice.id == obj.id).first()
    except Exception as exc:
        db.rollback()
        delete_file(storage_ref)
        raise HTTPException(422, f"Invoice processing failed: {exc}")


def decision(invoice_id: int, payload: DecisionIn, new_status: str, action: str, db: Session):
    obj = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not obj:
        raise HTTPException(404, "Invoice not found")
    previous = obj.status
    obj.status = new_status
    db.add(
        AuditLog(
            invoice_id=obj.id,
            actor=payload.actor,
            action=action,
            previous_status=previous,
            new_status=new_status,
            note=payload.note,
        )
    )
    db.commit()
    return {"id": obj.id, "status": obj.status}


@router.post("/invoices/{invoice_id}/approve")
def approve(invoice_id: int, payload: DecisionIn, db: Session = Depends(get_db)):
    return decision(invoice_id, payload, "APPROVED", "APPROVED", db)


@router.post("/invoices/{invoice_id}/reject")
def reject(invoice_id: int, payload: DecisionIn, db: Session = Depends(get_db)):
    return decision(invoice_id, payload, "REJECTED", "REJECTED", db)


@router.post("/invoices/{invoice_id}/request-review")
def review(invoice_id: int, payload: DecisionIn, db: Session = Depends(get_db)):
    return decision(invoice_id, payload, "REVIEW_REQUIRED", "REVIEW_REQUESTED", db)


@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(100).all()
    return [
        {
            "id": x.id,
            "invoice_id": x.invoice_id,
            "actor": x.actor,
            "action": x.action,
            "previous_status": x.previous_status,
            "new_status": x.new_status,
            "note": x.note,
            "created_at": x.created_at,
        }
        for x in logs
    ]
