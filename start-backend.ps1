# Start backend: FastAPI at http://localhost:8000
$env:PYTHONUTF8 = 1
Set-Location "$PSScriptRoot\backend"

# First run / missing deps: install automatically
if (-not (Test-Path ".venv")) {
    Write-Host "First run: installing backend dependencies (uv sync)..." -ForegroundColor Yellow
    uv sync
}

Write-Host "Starting backend at http://localhost:8000  (press Ctrl+C to stop)" -ForegroundColor Green
uv run uvicorn app.main:app --reload
