# API-only demo commands

```powershell
Invoke-RestMethod -Method Post http://localhost:8000/api/v1/demo/seed
Invoke-RestMethod http://localhost:8000/api/v1/purchase-orders
curl.exe -X POST -F "file=@sample_data/invoices/invoice_inv101_price_mismatch.pdf" http://localhost:8000/api/v1/invoices/upload
Invoke-RestMethod http://localhost:8000/api/v1/invoices
Invoke-RestMethod http://localhost:8000/api/v1/dashboard
```
