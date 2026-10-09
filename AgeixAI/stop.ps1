Write-Host "Stopping AgeixAISOC..." -ForegroundColor Red
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process npm -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "All stopped." -ForegroundColor Green
