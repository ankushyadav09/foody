# ==============================================================================
# scripts/start_public_tunnel.ps1
# FOODY HUNTERS - Cloudflare Quick Tunnel Starter with Automatic Portal Links
# ==============================================================================
# Creates a temporary, secure HTTPS public tunnel to your local Flask app
# (http://127.0.0.1:5000) without requiring router port-forwarding or public firewall rules.
# Automatically detects the live trycloudflare.com URL and displays all 5 portal links.
# ==============================================================================

[CmdletBinding()]
param(
    [string]$TargetUrl = "http://127.0.0.1:5000",
    [string]$SimulatedUrl = $null,
    [switch]$TestOnly
)

# Keep ErrorActionPreference Continue so cloudflared stderr logs do not abort pipeline
$ErrorActionPreference = "Continue"

# -- Function: Display Formatted Portal Links Menu -----------------------------
function Show-PortalMenu {
    param (
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl
    )

    $cleanBase = $BaseUrl.Trim().TrimEnd('/')

    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "       FOODY HUNTERS - PUBLIC ACCESS" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "1. USER / CUSTOMER WEBSITE:" -ForegroundColor Yellow
    Write-Host "   $cleanBase/" -ForegroundColor Cyan
    Write-Host "   -> Public storefront: restaurant browsing, menus, cart, checkout & tracking" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "2. ADMIN CONTROL CENTER:" -ForegroundColor Yellow
    Write-Host "   $cleanBase/admin" -ForegroundColor Cyan
    Write-Host "   -> Master administration: passkey gate, fleet approvals, orders & platform governance" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "3. DELIVERY PARTNER PORTAL:" -ForegroundColor Yellow
    Write-Host "   $cleanBase/delivery/portal" -ForegroundColor Cyan
    Write-Host "   -> Unified rider portal: registration, verification notice & operations dispatch" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green

    # Support copying the Customer Website URL to system clipboard if available
    try {
        if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) {
            Set-Clipboard -Value "$cleanBase/" -ErrorAction SilentlyContinue
            Write-Host "  [CLIPBOARD] Customer Website ($cleanBase/) copied to system clipboard!" -ForegroundColor Magenta
        }
    } catch {
        # Safe to ignore if headless or clipboard is inaccessible
    }

    Write-Host "  [STATUS] Public Tunnel is LIVE and forwarding to $TargetUrl" -ForegroundColor Green
    Write-Host "  [NOTICE] Keep this PowerShell window open to keep the public tunnel alive." -ForegroundColor White
    Write-Host "  [STOP]   Press Ctrl + C at any time to shut down the public tunnel." -ForegroundColor Yellow
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host ""
}

# If running in test mode with a simulated URL, display menu and exit immediately
if ($TestOnly) {
    if (-not $SimulatedUrl) {
        $SimulatedUrl = "https://simulated-foody-test.trycloudflare.com"
    }
    Write-Host "[TEST MODE] Running simulation with URL: $SimulatedUrl" -ForegroundColor Magenta
    Show-PortalMenu -BaseUrl $SimulatedUrl
    return
}

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

# Advisory check for local Flask server connectivity on port 5000
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $iar = $tcp.BeginConnect("127.0.0.1", 5000, $null, $null)
    $connected = $iar.AsyncWaitHandle.WaitOne(400, $false)
    if ($connected -and $tcp.Connected) {
        $tcp.EndConnect($iar)
        Write-Host "[OK] Local Flask server detected responding at 127.0.0.1:5000." -ForegroundColor Green
    } else {
        Write-Host "[INFO] Local Flask server is not yet running on 127.0.0.1:5000." -ForegroundColor Yellow
        Write-Host "       Remember to run '.\scripts\start_local.ps1' in PowerShell 1." -ForegroundColor Gray
    }
    $tcp.Close()
} catch {
    # Non-fatal advisory check
}
Write-Host ""

Write-Host "Starting Cloudflare Quick Tunnel to $TargetUrl ..." -ForegroundColor Cyan
Write-Host "Waiting for Cloudflare to assign your public HTTPS URL..." -ForegroundColor Cyan
Write-Host ""

$urlDetected = $false
$pendingMenu = $false
$detectedUrl = $null
$tunnelExitedNormally = $false

try {
    # 4. Execute Cloudflare Quick Tunnel and stream output in real-time
    & $CloudflaredCmd tunnel --url $TargetUrl 2>&1 | ForEach-Object {
        $line = $_.ToString()
        Write-Host $line

        # Detect the real trycloudflare.com URL emitted by cloudflared
        if (-not $urlDetected -and $line -match '(https://[a-zA-Z0-9-]+\.trycloudflare\.com)') {
            $detectedUrl = $matches[1]
            $urlDetected = $true
            if ($line -match '\+[-+]+\+') {
                # Line already closed the banner box
                Show-PortalMenu -BaseUrl $detectedUrl
            } else {
                # Allow the closing box border line to print first for clean formatting
                $pendingMenu = $true
            }
        }
        elseif ($pendingMenu) {
            Show-PortalMenu -BaseUrl $detectedUrl
            $pendingMenu = $false
        }
    }

    # Ensure menu is printed if stream ended before the next line
    if ($pendingMenu -and $detectedUrl) {
        Show-PortalMenu -BaseUrl $detectedUrl
        $pendingMenu = $false
    }

    $tunnelExitedNormally = $true
}
catch [System.Management.Automation.PipelineStoppedException] {
    Write-Host ""
    Write-Host "[INFO] Public tunnel stopped by user (Ctrl+C)." -ForegroundColor Yellow
}
catch {
    Write-Host ""
    Write-Host "[ERROR] Tunnel execution error: $_" -ForegroundColor Red
}
finally {
    Write-Host ""
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host "  FOODY HUNTERS - Cloudflare Public Tunnel Ended" -ForegroundColor Cyan
    Write-Host "==================================================================" -ForegroundColor Cyan

    if (-not $urlDetected -and -not $tunnelExitedNormally) {
        Write-Host "[ERROR] Cloudflare tunnel terminated before a public URL could be established." -ForegroundColor Red
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] cloudflared process exit code: $LASTEXITCODE" -ForegroundColor Red
        }
        Write-Host "Please verify your internet connection and ensure outbound traffic to Cloudflare is permitted." -ForegroundColor Yellow
    }
}
