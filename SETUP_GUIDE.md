# Setup Guide — Invoice Validation AI Agent (Supabase, No Docker) 

## 1. What runs where

- **Next.js frontend** — your laptop, `http://localhost:3000`
- **FastAPI backend** — your laptop, `http://localhost:8000`
- **PostgreSQL database** — Supabase cloud
- **Original invoice PDFs/images** — private Supabase Storage bucket
- **OpenAI API** — optional; mock mode works without an API key

The browser never receives the database password, Supabase secret key, or OpenAI key.

---

## 2. Prerequisites

Install/check:

```powershell
python --version
node --version
npm --version
git --version
```

Recommended:

- Python 3.11
- Node.js 20+ (Node 22 is fine)
- VS Code
- Git

### Optional: Tesseract OCR

Normal digital PDFs do not need Tesseract. Install it only if you want to process scanned/image-only invoices.

After installing Tesseract on Windows, make sure `tesseract.exe` is on PATH, then test:

```powershell
tesseract --version
```

---

## 3. Create a Supabase project

1. Sign in to Supabase.
2. Create a new project.
3. Save the **database password** you choose.
4. Wait until the project is ready.

Official docs: https://supabase.com/docs

---

## 4. Create the database tables and private invoice bucket

In the Supabase dashboard:

1. Open **SQL Editor**.
2. Choose **New query**.
3. Open this project file:

```text
supabase/setup.sql
```

4. Copy the entire SQL file into the SQL Editor.
5. Click **Run**.

It creates:

- suppliers
- purchase_orders
- po_items
- invoices
- invoice_items
- validation_results
- audit_logs
- private Storage bucket: `invoices`

The FastAPI app also calls SQLAlchemy `create_all()` at startup, but running the SQL file gives you an explicit and inspectable cloud schema.

---

## 5. Get the Supabase PostgreSQL connection string

In Supabase, open the project's **Connect** dialog.

For a normal Windows laptop, the easiest choice is usually **Session pooler** because it works over IPv4.

Copy the connection string. It normally resembles:

```text
postgresql://postgres.PROJECT_REF:PASSWORD@POOLER_HOST:5432/postgres
```

Do **not** invent the pooler host. Copy it from Supabase.

If your password contains special URL characters such as `@`, `#`, `?`, `/`, `%` or spaces, URL-encode the password or choose a database password without those characters for the hackathon.

The backend automatically converts `postgresql://` to SQLAlchemy's `postgresql+psycopg://` format.

Supabase connection docs:
https://supabase.com/docs/guides/database/connecting-to-postgres

---

## 6. Get the Supabase URL and backend secret key

You need two values for Storage:

```text
SUPABASE_URL
SUPABASE_SECRET_KEY
```

### Project URL

Copy the project URL from the Supabase **Connect** dialog or project settings. It looks like:

```text
https://YOUR_PROJECT_REF.supabase.co
```

### Secret key

Open:

```text
Settings -> API Keys
```

For current Supabase projects, create/copy a **Secret key** beginning with:

```text
sb_secret_...
```

This key is server-only and bypasses normal Row Level Security. Never put it in frontend code, never prefix it with `NEXT_PUBLIC_`, and never commit `.env` to GitHub.

The project also supports the older `SUPABASE_SERVICE_ROLE_KEY` as a fallback for legacy projects, but `SUPABASE_SECRET_KEY` is preferred.

Supabase API key docs:
https://supabase.com/docs/guides/getting-started/api-keys

---

## 7. Create your `.env`

From the project root:

```powershell
Copy-Item .env.example .env
```

Open `.env` and replace the placeholders:

```env
DATABASE_URL=postgresql://postgres.PROJECT_REF:YOUR_DATABASE_PASSWORD@YOUR_POOLER_HOST:5432/postgres?sslmode=require

STORAGE_PROVIDER=supabase
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SECRET_KEY=sb_secret_YOUR_SECRET_KEY
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_BUCKET=invoices

LLM_PROVIDER=mock
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6-luna

PRICE_TOLERANCE_PERCENT=0.0
QUANTITY_TOLERANCE_PERCENT=0.0
AUTO_APPROVE_MAX_RISK=19

CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Start with `LLM_PROVIDER=mock`. This lets you verify the full database/storage/validation workflow without spending API credits.

---

## 8. Install and run the FastAPI backend

Open **Terminal 1** in VS Code.

From the project root:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

If PowerShell blocks activation, run once in that terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Check:

```text
http://localhost:8000/health
```

Expected shape:

```json
{
  "status": "ok",
  "llm_provider": "mock",
  "database": "supabase-postgresql",
  "storage_provider": "supabase"
}
```

FastAPI Swagger:

```text
http://localhost:8000/docs
```

---

## 9. Run the setup diagnostic

Keep the backend virtual environment activated, return to the project root, and run:

```powershell
cd ..
python scripts/check-setup.py
```

You want to see:

```text
[OK] Database connection
[OK] Supabase Storage bucket
[OK] Mock LLM mode (no API key required)
```

If either Supabase check fails, fix `.env` before continuing.

---

## 10. Install and run the Next.js frontend

Open **Terminal 2** in VS Code.

```powershell
cd frontend
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

The frontend `.env.local` contains **no secrets**. It only contains the FastAPI URL.

---

## 11. Load purchase-order demo data

In the frontend click:

```text
Load demo data
```

Or use Swagger:

```text
POST /api/v1/demo/seed
```

This creates:

- PO450 — ABC Ltd — Motor Controller — qty 10 — $800
- PO451 — XYZ Components — Industrial Temperature Sensor — qty 20 — $120
- PO452 — Nova Electronics — Control PCB Assembly — qty 5 — $450

---

## 12. Test the supplied invoices

Use files in:

```text
sample_data/invoices/
```

### A. Price mismatch

```text
invoice_inv101_price_mismatch.pdf
```

Expected:

```text
Invoice price: $850
PO price:      $800
Quantity:      10
Difference:    $50/unit
Impact:        $500
Status:        REVIEW_REQUIRED
```

### B. Clean invoice

```text
invoice_inv102_clean.pdf
```

Expected:

```text
AUTO_APPROVED
```

### C. Duplicate invoice

Upload this twice:

```text
invoice_inv103_duplicate.pdf
```

First upload should pass. Second should flag `DUPLICATE_INVOICE`.

### D. Supplier mismatch

```text
invoice_inv104_supplier_mismatch.pdf
```

Expected: supplier mismatch exception.

You can click **Open original** on an invoice review. The browser calls FastAPI, and FastAPI retrieves the private file from Supabase Storage. The secret key never reaches the browser.

---

## 13. Enable real OpenAI extraction/explanations

After the mock workflow is working, edit `.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL=gpt-5.6-luna
```

Restart the backend.

The project uses the LLM for:

- converting unstructured invoice text to a typed Pydantic schema
- explaining deterministic validation failures
- recommending the next human action

It does **not** use the LLM to decide whether `$850 > $800`, detect duplicate database IDs, calculate financial differences, or directly approve database records.

This separation makes the system reproducible and auditable.

---

## 14. Run automated tests

From Terminal 1:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Tests deliberately use local SQLite + local file storage, so your cloud database is not modified.

---

## 15. Optional local-only mode

If the internet/Supabase is unavailable during development, you can temporarily use:

```env
DATABASE_URL=sqlite:///./invoice_ai.db
STORAGE_PROVIDER=local
LLM_PROVIDER=mock
```

Then run the same backend/frontend commands. This does not require any credentials.

For the actual hackathon demo, switch back to Supabase.

---

## 16. CSV import format

The endpoint:

```text
POST /api/v1/purchase-orders/import-csv
```

accepts files with columns:

```csv
po_number,supplier,currency,status,sku,description,quantity,unit_price
PO900,Example Supplier,USD,OPEN,ITEM-1,Example Item,10,25.00
```

`sample_data/purchase_orders.csv` is included as an example.

---

## 17. Common errors

### `password authentication failed`

Check the password inside `DATABASE_URL`. If it contains URL-reserved characters, encode them.

### `could not translate host name` / cannot reach database

Use the **Session pooler** URL copied from the Supabase Connect dialog instead of manually typing the direct host.

### `Storage bucket not found`

Run `supabase/setup.sql` or create a private bucket named exactly:

```text
invoices
```

### Supabase Storage 401/403

Make sure `SUPABASE_SECRET_KEY` contains a backend secret key and not a public/publishable key.

### `Could not extract readable text`

If the PDF is scanned, install Tesseract OCR. Digital PDFs should work without it.

### frontend cannot reach backend

Check:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
CORS_ORIGINS=http://localhost:3000
```

Then restart both servers.

### OpenAI error

First switch back to:

```env
LLM_PROVIDER=mock
```

Confirm the rest of the app works, then debug the API key/model separately.

---

## 18. Recommended hackathon demo sequence

1. Show the dashboard and Supabase tables.
2. Click **Load demo data**.
3. Upload the clean invoice and show auto-approval.
4. Upload `INV101` and show the $500 deterministic price exception.
5. Open the original PDF through the private-file route.
6. Show the AI explanation.
7. Approve/reject/request review as a human.
8. Show the audit trail.
9. Upload the duplicate invoice twice.
10. Explain: **AI extracts and explains; deterministic software validates and decides routing.**

That gives a much stronger story than simply calling an LLM on a PDF.
