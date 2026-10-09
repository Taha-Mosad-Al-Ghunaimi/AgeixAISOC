# AgeixAISOC — One-Click Platform Startup
# Launches backend (uvicorn :8000) and frontend (Vite :5173) side-by-side.

$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$Venv = "$Root\venv"
$Backend = "$Root\backend"
$Frontend = "$Root\frontend"
$Log = "$Root\ageixsoc.log"

Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         AgeixAISOC — Platform Launcher              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── 1. Python virtual environment ────────────────────────────────────────
if (-not (Test-Path "$Venv\Scripts\Activate.ps1")) {
    Write-Host "[1/4] Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv $Venv
    if (-not $?) { Write-Host "Failed to create venv" -ForegroundColor Red; exit 1 }
}

Write-Host "[1/4] Activating Python virtual environment..." -ForegroundColor Green
& "$Venv\Scripts\Activate.ps1"

# ── 2. Install dependencies ─────────────────────────────────────────────
if (Test-Path "$Backend\requirements.txt") {
    Write-Host "[2/4] Installing Python dependencies..." -ForegroundColor Yellow
    pip install -q -r "$Backend\requirements.txt"
    if (-not $?) { Write-Host "pip install failed" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "[2/4] No requirements.txt found, skipping pip install" -ForegroundColor Yellow
}
Write-Host "[2/4] Dependencies installed" -ForegroundColor Green

# ── 3. Start backend (port 8000) ────────────────────────────────────────
Write-Host "[3/4] Starting backend on port 8000..." -ForegroundColor Yellow
$BackendJob = Start-Job -Name "ageix-backend" -ScriptBlock {
    param($Dir, $Venv)
    & "$Venv\Scripts\Activate.ps1"
    Set-Location $Dir
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
} -ArgumentList $Backend, $Venv

# ── 4. Start frontend (port 5173) ───────────────────────────────────────
Write-Host "[4/4] Starting frontend on port 5173..." -ForegroundColor Yellow
$FrontendJob = Start-Job -Name "ageix-frontend" -ScriptBlock {
    param($Dir)
    Set-Location $Dir
    npm run dev
} -ArgumentList $Frontend

Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║   AgeixAISOC is RUNNING                             ║" -ForegroundColor Green
Write-Host "║   Backend  →  http://localhost:8000                  ║" -ForegroundColor Cyan
Write-Host "║   Frontend →  http://localhost:5173                  ║" -ForegroundColor Cyan
Write-Host "║   Dashboard WS → ws://localhost:8000/ws/dashboard    ║" -ForegroundColor Cyan
Write-Host "║                                                       ║" -ForegroundColor DarkGray
Write-Host "║   Run .\stop_ageixsoc.ps1 to stop all services       ║" -ForegroundColor DarkGray
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Green

# Keep script alive so user can Ctrl+C
while ($true) {
    $back = Receive-Job -Job $BackendJob -ErrorAction SilentlyContinue
    $front = Receive-Job -Job $FrontendJob -ErrorAction SilentlyContinue
    if ($back) { Write-Host $back -ForegroundColor DarkGray }
    if ($front) { Write-Host $front -ForegroundColor DarkGray }
    if ($BackendJob.State -eq 'Failed' -or $FrontendJob.State -eq 'Failed') {
        Write-Host "A service stopped unexpectedly. Run stop_ageixsoc.ps1 to clean up." -ForegroundColor Red
        break
    }
    Start-Sleep -Seconds 2
}
