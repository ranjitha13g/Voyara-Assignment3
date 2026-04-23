# =============================================================================
#  Voyara -- AI Journey Companion -- Start All Servers
#  Usage:  powershell -ExecutionPolicy Bypass -File start-servers.ps1
# =============================================================================

$root  = $PSScriptRoot
$pwsh  = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"

Write-Host ""
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host "  |   Voyara -- AI Journey Companion -- Startup      |" -ForegroundColor Cyan
Write-Host "  +--------------------------------------------------+" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Write a temp script for the FastAPI backend, then launch it
# ---------------------------------------------------------------------------
Write-Host "  [1/2] Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Yellow

$backendPs1 = Join-Path $env:TEMP "travel_backend.ps1"

Set-Content -Path $backendPs1 -Encoding UTF8 -Value @"
`$host.UI.RawUI.WindowTitle = 'Voyara - Backend'
Write-Host ''
Write-Host '  Voyara Backend  (FastAPI + Gemini)' -ForegroundColor Cyan
Write-Host ''
Set-Location "$root\backend"
uvicorn agent:app --reload --port 8000
"@

cmd /c "start `"Voyara - Backend`" $pwsh -NoExit -ExecutionPolicy Bypass -File `"$backendPs1`""

Start-Sleep -Seconds 2

# ---------------------------------------------------------------------------
# 2. Start frontend -- Apache (XAMPP) if present, else Python http.server
# ---------------------------------------------------------------------------
Write-Host "  [2/2] Detecting web server for frontend ..." -ForegroundColor Yellow

$xamppHttpd  = "C:\xampp\apache\bin\httpd.exe"
$xamppHtdocs = "C:\xampp\htdocs\travel-planner"

if (Test-Path $xamppHttpd) {
    Write-Host "        XAMPP detected -- deploying to Apache htdocs ..." -ForegroundColor Green

    New-Item -ItemType Directory -Force -Path $xamppHtdocs | Out-Null
    Copy-Item "$root\frontend\*" -Destination $xamppHtdocs -Recurse -Force

    $apacheRunning = Get-Process -Name "httpd" -ErrorAction SilentlyContinue
    if (-not $apacheRunning) {
        Write-Host "        Starting Apache (httpd) ..." -ForegroundColor Yellow
        Start-Process $xamppHttpd
        Start-Sleep -Seconds 3
    } else {
        Write-Host "        Apache already running." -ForegroundColor DarkGreen
    }

    $frontendUrl = "http://localhost/travel-planner/"
    Write-Host "        Frontend URL: $frontendUrl" -ForegroundColor Green

} else {
    Write-Host "        XAMPP not found -- using Python HTTP server on port 8080" -ForegroundColor Yellow
    Write-Host "        (Install XAMPP from https://www.apachefriends.org for Apache support)" -ForegroundColor DarkGray

    $frontendPs1 = Join-Path $env:TEMP "travel_frontend.ps1"

    Set-Content -Path $frontendPs1 -Encoding UTF8 -Value @"
`$host.UI.RawUI.WindowTitle = 'Voyara - Frontend'
Write-Host ''
Write-Host '  Voyara Frontend  (Python HTTP Server :8080)' -ForegroundColor Cyan
Write-Host ''
Set-Location "$root\frontend"
python -m http.server 8080
"@

    cmd /c "start `"Voyara - Frontend`" $pwsh -NoExit -ExecutionPolicy Bypass -File `"$frontendPs1`""
    $frontendUrl = "http://localhost:8080"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Start-Sleep -Seconds 2
Write-Host ""
Write-Host "  +--------------------------------------------------+" -ForegroundColor Green
Write-Host "  |  All servers started!                            |" -ForegroundColor Green
Write-Host "  |                                                  |" -ForegroundColor Green
Write-Host "  |  Frontend : $frontendUrl" -ForegroundColor Green
Write-Host "  |  Backend  : http://localhost:8000                |" -ForegroundColor Green
Write-Host "  |  API Docs : http://localhost:8000/docs           |" -ForegroundColor Green
Write-Host "  |  Logs     : backend\logs\                        |" -ForegroundColor Green
Write-Host "  +--------------------------------------------------+" -ForegroundColor Green
Write-Host ""

Start-Process $frontendUrl
