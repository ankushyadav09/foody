# ==============================================================================
# scripts/start_public_tunnel.ps1
# FOODY HUNTERS — Cloudflare Quick Tunnel Starter
# ==============================================================================
# Creates a temporary, secure HTTPS public tunnel to your local Flask app
# (http://127.0.0.1:5000) without requiring router port-forwarding or public firewall rules.
# ==============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  FOODY HUNTERS - Cloudflare Public Demo Tunnel" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Check if cloudflared is installed and available
$CloudflaredCmd = $null

$Cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if ($Cmd) {
    $CloudflaredCmd = $Cmd.Source
} else {
    # Check common Windows install locations
    $PossiblePaths = @(
        "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe",
        "$env:ProgramFiles\cloudflared\cloudflared.exe",
        "$PSScriptRoot\..\cloudflared.exe",
        "$PSScriptRoot\cloudflared.exe"
    )
    foreach ($p in $PossiblePaths) {
        if ($p -and (Test-Path $p)) {
            $CloudflaredCmd = $p
            break
        }
    }
}

# 2. If cloudflared is not installed, display instructions
if (-not $CloudflaredCmd) {
    Write-Host "[ERROR] Cloudflare Tunnel CLI ('cloudflared') was not found on your system." -ForegroundColor Red
    Write-Host ""
    Write-Host "To install cloudflared on Windows, choose either option below:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Option A (Recommended - Windows Package Manager):" -ForegroundColor White
    Write-Host "    winget install --id Cloudflare.cloudflared" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Option B (Direct Download):" -ForegroundColor White
    Write-Host "    Download 'cloudflared-windows-amd64.exe' from:" -ForegroundColor Gray
    Write-Host "    https://github.com/cloudflare/cloudflared/releases/latest" -ForegroundColor Cyan
    Write-Host "    Rename it to 'cloudflared.exe' and place it in this project folder." -ForegroundColor Gray
    Write-Host ""
    Write-Host "After installation, re-run this script:" -ForegroundColor Yellow
    Write-Host "  .\scripts\start_public_tunnel.ps1" -ForegroundColor White
    Write-Host "==================================================================" -ForegroundColor Cyan
    exit 1
}

Write-Host "[OK] Detected cloudflared at: $CloudflaredCmd" -ForegroundColor Green
Write-Host ""

# 3. Security and usage overview
Write-Host "------------------------------------------------------------------" -ForegroundColor DarkYellow
Write-Host "  SECURITY & DEMO NOTICE:" -ForegroundColor Yellow
Write-Host "  - Make sure Flask is already running in Terminal 1 (127.0.0.1:5000)." -ForegroundColor White
Write-Host "  - Cloudflare creates an outbound HTTPS tunnel to Cloudflare Edge." -ForegroundColor White
Write-Host "  - No router port-forwarding or inbound firewall rules required." -ForegroundColor White
Write-Host "  - The generated https://*.trycloudflare.com URL will be accessible" -ForegroundColor White
Write-Host "    to anyone on the internet who has the link (e.g., phone on mobile data)." -ForegroundColor White
Write-Host "  - Server-side RBAC protects admin accounts, but do NOT share" -ForegroundColor White
Write-Host "    administrator passwords or secret keys with untrusted parties." -ForegroundColor White
Write-Host "  - To STOP public access at any time: press Ctrl + C in this window." -ForegroundColor Yellow
Write-Host "------------------------------------------------------------------" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "Starting Cloudflare Quick Tunnel to http://127.0.0.1:5000 ..." -ForegroundColor Cyan
Write-Host "Look for the box in the output below containing your public URL:" -ForegroundColor Green
Write-Host "  Example: https://xxxx-xxxx-xxxx.trycloudflare.com" -ForegroundColor Cyan
Write-Host ""

# 4. Execute Cloudflare Quick Tunnel
& $CloudflaredCmd tunnel --url http://127.0.0.1:5000
