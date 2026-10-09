# AgeixAISOC — Platform Stop Script
# Gracefully stops backend and frontend services.

Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Red
Write-Host "║         AgeixAISOC — Platform Stopper               ║" -ForegroundColor Red
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Red
Write-Host ""

# Stop background jobs
Get-Job -Name "ageix-*" -ErrorAction SilentlyContinue | Stop-Job | Remove-Job
Write-Host "[✓] Background jobs stopped" -ForegroundColor Green

# Kill uvicorn processes
$uvicornProcs = Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue
if ($uvicornProcs) {
    $uvicornProcs | Stop-Process -Force
    Write-Host "[✓] Backend (uvicorn) stopped" -ForegroundColor Green
} else {
    Write-Host "[•] No uvicorn process found" -ForegroundColor DarkGray
}

# Kill node / npm run dev processes on port 5173
$nodeProcs = Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "5173|frontend|vite" }
if ($nodeProcs) {
    $nodeProcs | Stop-Process -Force
    Write-Host "[✓] Frontend (Vite/Node) stopped" -ForegroundColor Green
} else {
    Write-Host "[•] No Node process for frontend found" -ForegroundColor DarkGray
}

# Also free port 8000 and 5173 just in case
netstat -ano | Select-String ":8000 " | ForEach-Object {
    $pid = $_ -replace '.*\s+(\d+)\s*$', '$1'
    if ($pid -and $pid -ne '0') {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
}
netstat -ano | Select-String ":5173 " | ForEach-Object {
    $pid = $_ -replace '.*\s+(\d+)\s*$', '$1'
    if ($pid -and $pid -ne '0') {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "AgeixAISOC has been stopped." -ForegroundColor Gray
