from sqlalchemy.orm import Session
from app.models import Supplier, PurchaseOrder, POItem

DEMO_POS = [
    {"po_number":"PO450","supplier":"ABC Ltd","currency":"USD","status":"OPEN","items":[{"sku":"MC-100","description":"Motor Controller","quantity":10,"unit_price":800}]},
    {"po_number":"PO451","supplier":"XYZ Components","currency":"USD","status":"OPEN","items":[{"sku":"SEN-20","description":"Industrial Temperature Sensor","quantity":20,"unit_price":120}]},
    {"po_number":"PO452","supplier":"Nova Electronics","currency":"USD","status":"OPEN","items":[{"sku":"PCB-88","description":"Control PCB Assembly","quantity":5,"unit_price":450}]},
]

def seed_demo(db: Session):
    created = 0
    for data in DEMO_POS:
        if db.query(PurchaseOrder).filter_by(po_number=data["po_number"]).first(): continue
        supplier = db.query(Supplier).filter_by(name=data["supplier"]).first()
        if not supplier:
            supplier=Supplier(name=data["supplier"]); db.add(supplier); db.flush()
        po=PurchaseOrder(po_number=data["po_number"], supplier=supplier, currency=data["currency"], status=data["status"])
        for i in data["items"]: po.items.append(POItem(**i))
        db.add(po); created += 1
    db.commit()
    return created
