from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "sample_data" / "invoices"

def test_health(client):
    r=client.get("/health")
    assert r.status_code==200
    assert r.json()["status"]=="ok"
    assert r.json()["storage_provider"]=="local"

def test_seed_and_dashboard(client):
    r=client.post("/api/v1/demo/seed")
    assert r.status_code==200
    assert r.json()["created_purchase_orders"]==3
    p=client.get("/api/v1/purchase-orders")
    assert p.status_code==200
    assert len(p.json())==3
    d=client.get("/api/v1/dashboard")
    assert d.status_code==200
    assert d.json()["total_invoices"]==0

def upload(client, filename):
    p=SAMPLES/filename
    with p.open("rb") as f:
        return client.post("/api/v1/invoices/upload",files={"file":(filename,f,"application/pdf")})

def test_price_mismatch_end_to_end(client):
    client.post("/api/v1/demo/seed")
    r=upload(client,"invoice_inv101_price_mismatch.pdf")
    assert r.status_code==200
    j=r.json()
    assert j["invoice_number"]=="INV101"
    assert j["status"]=="REVIEW_REQUIRED"
    assert j["risk_score"]==30
    failed={v["rule_code"] for v in j["validations"] if not v["passed"]}
    assert failed=={"PRICE_MISMATCH"}
    finding=next(v for v in j["validations"] if v["rule_code"]=="PRICE_MISMATCH")
    assert finding["difference"]==50
    assert "financial impact 500.00" in finding["message"]

def test_clean_and_duplicate_paths(client):
    client.post("/api/v1/demo/seed")
    clean=upload(client,"invoice_inv102_clean.pdf").json()
    assert clean["status"]=="AUTO_APPROVED"
    first=upload(client,"invoice_inv103_duplicate.pdf").json()
    assert first["status"]=="AUTO_APPROVED"
    second=upload(client,"invoice_inv103_duplicate.pdf").json()
    assert second["status"]=="REVIEW_REQUIRED"
    failed={v["rule_code"] for v in second["validations"] if not v["passed"]}
    assert "DUPLICATE_INVOICE" in failed


def test_original_file_can_be_retrieved(client):
    client.post("/api/v1/demo/seed")
    uploaded=upload(client,"invoice_inv102_clean.pdf")
    assert uploaded.status_code==200
    invoice_id=uploaded.json()["id"]
    r=client.get(f"/api/v1/invoices/{invoice_id}/file")
    assert r.status_code==200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
