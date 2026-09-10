# InvoiceGuard — Explainable Invoice Validation AI Agent

A hackathon-ready Accounts Payable agent that extracts supplier invoices, matches them against purchase orders, runs deterministic validation rules, flags exceptions, explains them with AI, and keeps an audit trail.

## Recommended stack

```text
Next.js + TypeScript
        |
        v
FastAPI + Python
        |
        +--> PyMuPDF / optional Tesseract OCR
        +--> deterministic validation engine
        +--> OpenAI structured extraction + explanations
        |
        +--> Supabase PostgreSQL
        +--> private Supabase Storage
```

**Docker is not required.**

## Start here

Read:

1. [`SETUP_GUIDE.md`](SETUP_GUIDE.md) — exact Windows/VS Code/Supabase setup
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design and request flow
3. [`supabase/setup.sql`](supabase/setup.sql) — database + private Storage bucket

## What users can do

- load or import purchase-order records
- upload PDF/JPG/PNG invoices
- extract invoice number, PO, supplier, dates, currency, totals and line items
- detect PO, supplier, price, quantity, currency, arithmetic and duplicate problems
- see risk score + evidence for every validation rule
- receive an AI-written exception explanation and recommendation
- approve, reject or request manual review
- reopen the original invoice through a protected backend route
- inspect audit history and dashboard metrics

## Important design rule

```text
AI: understands messy document text and explains findings
Python: performs calculations, rules, risk scoring and workflow routing
Database: stores auditable business state
```

The LLM never gets direct permission to mark an invoice valid in the database.

## Zero-credential mode

For learning or offline testing:

```env
DATABASE_URL=sqlite:///./invoice_ai.db
STORAGE_PROVIDER=local
LLM_PROVIDER=mock
```

For the intended hackathon setup, copy `.env.example` to `.env` and add Supabase credentials. You can still keep `LLM_PROVIDER=mock` until you are ready to use OpenAI.

## Main folders

```text
invoice-validation-ai-agent/
├── backend/
│   ├── app/
│   │   ├── api.py
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── core/config.py
│   │   └── services/
│   │       ├── document.py
│   │       ├── extraction.py
│   │       ├── explanation.py
│   │       ├── storage.py
│   │       ├── validation.py
│   │       └── seed.py
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── app/
│   └── lib/
├── sample_data/
├── scripts/
├── supabase/
│   └── setup.sql
├── .env.example
├── SETUP_GUIDE.md
├── ARCHITECTURE.md
└── README.md
```

## Security notes

- `.env` is ignored by Git.
- Supabase secret/service-role credentials are backend-only.
- OpenAI credentials are backend-only.
- the Storage bucket is private.
- invoice text is treated as untrusted input; prompts inside invoices are explicitly ignored by the extraction instruction.
- file extension, signature and size are validated.
- structured LLM output is validated with Pydantic.
- business decisions use deterministic rules.

## Tests

```powershell
cd backend
python -m pytest -q
```

The included tests use isolated SQLite/local storage and cover API health, seeding, price mismatch, clean invoice, duplicate detection, extraction, and original-file retrieval.
