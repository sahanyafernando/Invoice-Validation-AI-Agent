$ErrorActionPreference = "Stop"
if (!(Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "Created .env from .env.example. Add your Supabase credentials before using cloud mode." -ForegroundColor Yellow
}
Write-Host "Open two VS Code terminals:" -ForegroundColor Cyan
Write-Host "Terminal 1: .\scripts\run-backend.ps1"
Write-Host "Terminal 2: .\scripts\run-frontend.ps1"
Write-Host "Full instructions: SETUP_GUIDE.md" -ForegroundColor Green
