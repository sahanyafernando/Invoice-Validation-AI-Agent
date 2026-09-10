from dataclasses import dataclass
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from app.models import Invoice, PurchaseOrder, ValidationResult
from app.core.config import settings

RISK_WEIGHTS = {
    "PO_NOT_FOUND": 80,
    "DUPLICATE_INVOICE": 80,
    "SUPPLIER_MISMATCH": 60,
    "PO_STATUS": 55,
    "CURRENCY_MISMATCH": 45,
    "UNMATCHED_LINE": 35,
    "PRICE_MISMATCH": 30,
    "QUANTITY_MISMATCH": 25,
    "ARITHMETIC_MISMATCH": 20,
}

def norm(s: str | None) -> str:
    return " ".join((s or "").lower().replace("ltd.", "ltd").split())

def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()

def add(invoice, code, passed, severity, expected, actual, message, difference=None):
    invoice.validations.append(ValidationResult(
        rule_code=code, passed=passed, severity=severity,
        expected_value=None if expected is None else str(expected),
        actual_value=None if actual is None else str(actual),
        difference=difference, message=message,
    ))

def within_percent(actual, expected, tolerance_percent):
    if expected == 0: return actual == 0
    return abs(actual-expected) / abs(expected) * 100 <= tolerance_percent

def validate_invoice(db: Session, invoice: Invoice):
    invoice.validations.clear()
    risk = 0

    duplicates = db.query(Invoice).filter(
        Invoice.invoice_number == invoice.invoice_number,
        Invoice.supplier_name == invoice.supplier_name,
        Invoice.id != invoice.id,
    ).count()
    duplicate = duplicates > 0
    add(invoice, "DUPLICATE_INVOICE", not duplicate, "CRITICAL" if duplicate else "INFO",
        "unique invoice", f"{duplicates} previous match(es)",
        "Invoice number is unique." if not duplicate else "Potential duplicate invoice already exists.")
    if duplicate: risk += RISK_WEIGHTS["DUPLICATE_INVOICE"]

    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number == invoice.po_number).first() if invoice.po_number else None
    add(invoice, "PO_NOT_FOUND", po is not None, "CRITICAL" if po is None else "INFO",
        invoice.po_number, invoice.po_number if po else "not found",
        "Purchase order found." if po else "Referenced purchase order was not found.")
    if not po:
        risk += RISK_WEIGHTS["PO_NOT_FOUND"]
    else:
        supplier_ok = norm(po.supplier.name) == norm(invoice.supplier_name)
        add(invoice, "SUPPLIER_MISMATCH", supplier_ok, "HIGH" if not supplier_ok else "INFO",
            po.supplier.name, invoice.supplier_name,
            "Supplier matches PO." if supplier_ok else "Invoice supplier does not match the PO supplier.")
        if not supplier_ok: risk += RISK_WEIGHTS["SUPPLIER_MISMATCH"]

        status_ok = po.status.upper() == "OPEN"
        add(invoice, "PO_STATUS", status_ok, "HIGH" if not status_ok else "INFO",
            "OPEN", po.status, "PO is open." if status_ok else "PO is not open for invoicing.")
        if not status_ok: risk += RISK_WEIGHTS["PO_STATUS"]

        currency_ok = po.currency.upper() == invoice.currency.upper()
        add(invoice, "CURRENCY_MISMATCH", currency_ok, "HIGH" if not currency_ok else "INFO",
            po.currency, invoice.currency, "Currency matches." if currency_ok else "Invoice currency differs from the PO.")
        if not currency_ok: risk += RISK_WEIGHTS["CURRENCY_MISMATCH"]

        used_po_ids = set()
        for inv_item in invoice.items:
            candidates = sorted(po.items, key=lambda p: max(similar(inv_item.description, p.description), 1.0 if inv_item.sku and p.sku == inv_item.sku else 0), reverse=True)
            po_item = candidates[0] if candidates else None
            match_score = max(similar(inv_item.description, po_item.description), 1.0 if po_item and inv_item.sku and po_item.sku == inv_item.sku else 0) if po_item else 0
            matched = bool(po_item and match_score >= 0.55 and po_item.id not in used_po_ids)
            if not matched:
                add(invoice, "UNMATCHED_LINE", False, "HIGH", "matching PO line", inv_item.description, "Invoice line could not be matched to a PO line.")
                risk += RISK_WEIGHTS["UNMATCHED_LINE"]
                continue
            used_po_ids.add(po_item.id)

            price_ok = within_percent(inv_item.unit_price, po_item.unit_price, settings.price_tolerance_percent)
            diff = inv_item.unit_price - po_item.unit_price
            impact = diff * inv_item.quantity
            add(invoice, "PRICE_MISMATCH", price_ok, "MEDIUM" if not price_ok else "INFO",
                f"{po_item.unit_price:.2f}", f"{inv_item.unit_price:.2f}",
                "Unit price matches PO." if price_ok else f"Unit price differs by {diff:.2f} per unit; financial impact {impact:.2f}.", diff)
            if not price_ok: risk += RISK_WEIGHTS["PRICE_MISMATCH"]

            qty_ok = within_percent(inv_item.quantity, po_item.quantity, settings.quantity_tolerance_percent)
            qdiff = inv_item.quantity - po_item.quantity
            add(invoice, "QUANTITY_MISMATCH", qty_ok, "MEDIUM" if not qty_ok else "INFO",
                f"{po_item.quantity:g}", f"{inv_item.quantity:g}",
                "Quantity matches PO." if qty_ok else f"Invoice quantity differs from ordered quantity by {qdiff:g}.", qdiff)
            if not qty_ok: risk += RISK_WEIGHTS["QUANTITY_MISMATCH"]

    calculated_subtotal = round(sum(x.line_total for x in invoice.items), 2)
    arithmetic_ok = abs(calculated_subtotal - invoice.subtotal) <= 0.01 and abs((invoice.subtotal + invoice.tax) - invoice.total) <= 0.01
    add(invoice, "ARITHMETIC_MISMATCH", arithmetic_ok, "MEDIUM" if not arithmetic_ok else "INFO",
        f"subtotal={calculated_subtotal:.2f}; total={invoice.subtotal + invoice.tax:.2f}",
        f"subtotal={invoice.subtotal:.2f}; total={invoice.total:.2f}",
        "Invoice arithmetic is consistent." if arithmetic_ok else "Invoice subtotal/tax/total arithmetic is inconsistent.")
    if not arithmetic_ok: risk += RISK_WEIGHTS["ARITHMETIC_MISMATCH"]

    invoice.risk_score = min(100, risk)
    invoice.risk_level = "LOW" if invoice.risk_score < 20 else "MEDIUM" if invoice.risk_score < 50 else "HIGH"
    failures = [v for v in invoice.validations if not v.passed]
    invoice.status = "AUTO_APPROVED" if not failures and invoice.risk_score <= settings.auto_approve_max_risk else "REVIEW_REQUIRED"
    return po, failures
