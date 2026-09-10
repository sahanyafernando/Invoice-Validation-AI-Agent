Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path ".venv")) { py -3.11 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
