from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ExtractedLineItem(BaseModel):
    sku: str | None = None
    description: str = "Item"
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    line_total: float = Field(ge=0)

class InvoiceExtraction(BaseModel):
    invoice_number: str
    po_number: str | None = None
    supplier: str
    invoice_date: date | None = None
    currency: str = "USD"
    items: list[ExtractedLineItem]
    subtotal: float = Field(ge=0)
    tax: float = Field(ge=0)
    total: float = Field(ge=0)

    @field_validator("invoice_number", "supplier")
    @classmethod
    def must_not_be_blank(cls, v):
        if not v.strip(): raise ValueError("field must not be blank")
        return v.strip()

class ValidationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_code: str
    passed: bool
    severity: str
    expected_value: str | None
    actual_value: str | None
    difference: float | None
    message: str

class InvoiceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str | None
    description: str
    quantity: float
    unit_price: float
    line_total: float

class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_number: str
    po_number: str | None
    supplier_name: str
    invoice_date: date | None
    currency: str
    subtotal: float
    tax: float
    total: float
    original_filename: str
    status: str
    risk_score: int
    risk_level: str
    explanation: str
    recommendation: str
    extraction_provider: str
    created_at: datetime
    items: list[InvoiceItemOut] = []
    validations: list[ValidationOut] = []

class POItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str | None
    description: str
    quantity: float
    unit_price: float

class POOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    po_number: str
    currency: str
    status: str
    supplier_name: str
    items: list[POItemOut]

class DecisionIn(BaseModel):
    actor: str = "finance.manager@example.com"
    note: str = ""

class DashboardOut(BaseModel):
    total_invoices: int
    auto_approved: int
    review_required: int
    rejected: int
    total_value: float
    exception_rate: float
