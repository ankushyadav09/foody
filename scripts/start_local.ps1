# ==============================================================================
# scripts/start_local.ps1
# FOODY HUNTERS — Local Server Starter
# ==============================================================================
# Starts Flask bound strictly to 127.0.0.1:5000 with debug OFF.
# Keep this terminal running while the public tunnel runs in Terminal 2.
# ==============================================================================

$ErrorActionPreference = "Stop"

# Resolve project root directory
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path "$ProjectRoot\app.py")) {
    $ProjectRoot = Get-Location
}
Set-Location $ProjectRoot

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  FOODY HUNTERS - Starting Local Flask Application" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Activate virtual environment if present
$VenvActivate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "[OK] Activating virtual environment (.venv)..." -ForegroundColor Green
    & $VenvActivate
} else {
    Write-Host "[INFO] .venv activation script not found; using active Python environment." -ForegroundColor Yellow
}

# 2. Set strict local tunnel-compatible environment variables
$env:HOST = "127.0.0.1"
$env:PORT = "5000"
$env:FLASK_DEBUG = "0"

Write-Host "[OK] Environment Variables Configured:" -ForegroundColor Green
Write-Host "     HOST        = $env:HOST (bound locally; no inbound firewall rules needed)" -ForegroundColor Gray
Write-Host "     PORT        = $env:PORT" -ForegroundColor Gray
Write-Host "     FLASK_DEBUG = $env:FLASK_DEBUG (debugger disabled for security)" -ForegroundColor Gray
Write-Host ""
Write-Host "Local URL: http://127.0.0.1:5000" -ForegroundColor White
Write-Host "Tunnel Ready: Open Terminal 2 and run .\scripts\start_public_tunnel.ps1" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# 3. Launch Flask
python app.py
