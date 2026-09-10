from app.schemas import InvoiceExtraction
from app.services.extraction import mock_extract

def test_mock_extract():
    text="""ABC Ltd\nInvoice ID: INV101\nSupplier: ABC Ltd\nPO: PO450\nInvoice Date: 2026-09-10\nCurrency: USD\nItem: Motor Controller\nSKU: MC-100\nQuantity: 10\nUnit Price: $850\nLine Total: $8,500\nSubtotal: $8,500\nTax: $0\nTotal: $8,500"""
    x=mock_extract(text)
    assert x.invoice_number=="INV101"
    assert x.po_number=="PO450"
    assert x.items[0].unit_price==850
    assert x.total==8500
