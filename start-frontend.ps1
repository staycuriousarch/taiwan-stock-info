# Start frontend: Vite dev server at http://localhost:5173
Set-Location "$PSScriptRoot\frontend"

# First run / missing deps: install automatically
if (-not (Test-Path "node_modules")) {
    Write-Host "First run: installing frontend dependencies (npm install)..." -ForegroundColor Yellow
    npm install
}

Write-Host "Starting frontend at http://localhost:5173  (press Ctrl+C to stop)" -ForegroundColor Green
npm run dev
