# Nerve AI Backend — Windows install (Python 3.11–3.13)
# Run from Backend/:  powershell -ExecutionPolicy Bypass -File scripts/install_windows.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "Python:" (python --version)
python -m pip install --upgrade pip

Write-Host "`nInstalling dependencies (may take a few minutes)..."
python -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nIf install failed, try Python 3.11:" -ForegroundColor Yellow
    Write-Host "  py -3.11 -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

Write-Host "`nOK. Start API:" -ForegroundColor Green
Write-Host "  uvicorn main:app --reload --port 8000"
