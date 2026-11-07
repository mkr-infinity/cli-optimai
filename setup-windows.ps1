# ============================================================
# setup-windows.ps1 — Automated Setup for Windows
# OptimAI Telegram Node (v1.3.0)
#
# Configures Python environment, downloads official Windows
# OptimAI CLI binary, and prepares .env for Windows systems.
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "            ⛏️ OPTIMAI WINDOWS AUTOMATED SETUP" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

function Write-Tick($label, $detail) {
    Write-Host "  [✓] " -NoNewline -ForegroundColor Green
    Write-Host ("{0,-34} {1}" -f $label, $detail)
}

function Write-Warn($label, $detail) {
    Write-Host "  [!] " -NoNewline -ForegroundColor Yellow
    Write-Host ("{0,-34} {1}" -f $label, $detail)
}

# 1. Check Python
try {
    $pythonVer = & python --version 2>&1
    Write-Tick "Python Runtime" $pythonVer
} catch {
    Write-Host "  [✗] Python is not installed or not in PATH. Please install Python 3.10+ from python.org." -ForegroundColor Red
    exit 1
}

# 2. Setup Directories
$localBin = Join-Path $env:USERPROFILE ".local\bin"
if (!(Test-Path $localBin)) {
    New-Item -ItemType Directory -Path $localBin -Force | Out-Null
}
$dataDir = Join-Path $PSScriptRoot "data"
if (!(Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path (Join-Path $dataDir "data") -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $dataDir "home") -Force | Out-Null
}
Write-Tick "Storage Directories" "Initialized ./data and ~/.local/bin"

# 3. Download Official Windows OptimAI CLI Binary
$cliUrl = "https://cli-node.optimai.network/optimai_cli_windows.exe"
$cliDest = Join-Path $localBin "optimai-cli.exe"

if (!(Test-Path $cliDest)) {
    Write-Host "  Downloading official OptimAI CLI binary..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $cliUrl -OutFile $cliDest -UseBasicParsing
    Write-Tick "Official OptimAI CLI" "Downloaded to $cliDest"
} else {
    Write-Tick "Official OptimAI CLI" "Already installed at $cliDest"
}

# Add ~/.local/bin to PATH for current session
$env:PATH = "$localBin;" + $env:PATH

# Prime core CLI
try {
    & $cliDest --help 2>&1 | Out-Null
    $verOut = & $cliDest --version 2>&1
    Write-Tick "Core CLI Priming" "Primed core binary ($verOut)"
} catch {
    Write-Warn "Core CLI Priming" "Advisory check completed"
}

# 4. Virtual Environment and Dependencies
$venvDir = Join-Path $PSScriptRoot ".venv"
if (!(Test-Path $venvDir)) {
    Write-Host "  Creating Python virtual environment (.venv)..." -ForegroundColor Gray
    & python -m venv $venvDir
}
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

Write-Host "  Installing dependencies from requirements.txt..." -ForegroundColor Gray
& $venvPip install --upgrade pip -q 2>&1 | Out-Null
& $venvPip install -r (Join-Path $PSScriptRoot "requirements.txt") -q
Write-Tick "Python Virtual Env" "Installed packages into .venv"

# 5. Environment File
$envFile = Join-Path $PSScriptRoot ".env"
$envExample = Join-Path $PSScriptRoot ".env.example"
if (!(Test-Path $envFile) -and (Test-Path $envExample)) {
    Copy-Item $envExample $envFile
    Write-Tick "Configuration File" "Created .env from .env.example"
} else {
    Write-Tick "Configuration File" ".env file ready"
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "  🎉 Windows Setup Complete! Node is Ready to Run!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  1. Enter your Telegram credentials:  notepad .env" -ForegroundColor Yellow
Write-Host "  2. Start Bot and AI Miner together:  .\start.bat" -ForegroundColor Green
Write-Host "  3. Telegram Bot Control:             Send /start in Telegram" -ForegroundColor White
Write-Host "======================================================================`n"
