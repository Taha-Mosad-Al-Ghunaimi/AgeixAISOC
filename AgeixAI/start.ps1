Write-Host "AgeixAISOC Platform starting..." -ForegroundColor Cyan
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Auto-create venv if missing
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv .\venv
    & ".\venv\Scripts\Activate.ps1"
    pip install -q -r .\backend\requirements.txt
} else {
    & ".\venv\Scripts\Activate.ps1"
}

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '.\backend'; & '..\venv\Scripts\Activate.ps1'; uvicorn main:app --reload --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '.\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "npx n8n"

Write-Host "Platform RUNNING! Dashboard: http://localhost:5173 | Backend: http://localhost:8000 | n8n: http://localhost:5678" -ForegroundColor Green
