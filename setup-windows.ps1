# ============================================================
# setup-windows.ps1 — Automated Setup for Windows
# OptimAI Telegram Bot (v1.9.0)
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

# 6. Interactive Account Login Intake (180s Auto-Timeout)
try {
    if ([Environment]::UserInteractive) {
        $optimaiExe = "optimai-cli.exe"
        if (Test-Path ".\optimai-cli.exe") {
            $optimaiExe = ".\optimai-cli.exe"
        }
        $authStatus = & $optimaiExe auth status 2>$null
        $isAuth = $false
        if ($authStatus -match "authenticated|logged in|user:" -and $authStatus -notmatch "not authenticated|not logged in|unauthenticated") {
            $isAuth = $true
            Write-Host "`n  [✓] Official OptimAI CLI is already authenticated." -ForegroundColor Green
        }
        if (-not $isAuth) {
            Write-Host "`n======================================================================" -ForegroundColor Cyan
            Write-Host "  🔑 OPTIMAI ACCOUNT LOGIN (Optional — Auto-timeout: 3 minutes)" -ForegroundColor Cyan
            Write-Host "======================================================================" -ForegroundColor Cyan
            Write-Host "  Choose your sign-in method to connect this node to your OptimAI account:`n"
            Write-Host "  1) Browser Login: optimai-cli auth login (Recommended)" -ForegroundColor White
            Write-Host "     Sign in via the OptimAI Node Dashboard in your browser and complete login.`n"
            Write-Host "  2) Legacy Login (email/password): optimai-cli auth login --legacy" -ForegroundColor White
            Write-Host "     If you prefer to use email/password instead of browser login.`n"
            Write-Host "  [Enter 1 or 2, or press Enter to skip / 180s timeout]: " -NoNewline

            $methodChoice = ""
            $loginTimer = [System.Diagnostics.Stopwatch]::StartNew()
            while ($loginTimer.Elapsed.TotalSeconds -lt 180) {
                if ([Console]::KeyAvailable) {
                    $key = [Console]::ReadKey($true)
                    if ($key.Key -eq [ConsoleKey]::Enter) { break }
                    $methodChoice += $key.KeyChar
                    Write-Host $key.KeyChar -NoNewline
                }
                Start-Sleep -Milliseconds 50
            }
            Write-Host ""
            $methodChoice = $methodChoice.Trim()

            if ($methodChoice -eq "1") {
                Write-Host "`n==> Launching Browser Login (optimai-cli auth login)..." -ForegroundColor Green
                & $optimaiExe auth login --no-open --paste
                Write-Host "`n[✓] Login flow complete.`n" -ForegroundColor Green
            } elseif ($methodChoice -eq "2") {
                Write-Host "`n==> Legacy Login (optimai-cli auth login --legacy):" -ForegroundColor Green
                Write-Host "  Enter your OptimAI email: " -NoNewline
                $emailInput = [Console]::ReadLine()
                Write-Host "  Enter your OptimAI password: " -NoNewline
                $pwdInput = [Console]::ReadLine()
                if ($emailInput -and $pwdInput) {
                    "$emailInput`n$pwdInput" | & $optimaiExe auth login --legacy
                    Write-Host "`n[✓] Legacy login submitted.`n" -ForegroundColor Green
                } else {
                    Write-Host "`n[!] Email or password empty. Login skipped.`n" -ForegroundColor Yellow
                }
            } else {
                Write-Host "`n[!] Account login skipped or timed out." -ForegroundColor Yellow
                Write-Host "    You can sign in at any time from Telegram (/login or /login --legacy) or terminal.`n"
            }
        }
    }
} catch {
    # Non-interactive fallback
}

# 7. Interactive Credentials Intake (60s Auto-Timeout)
$configured = $false
$tokenVal = ""
$idsVal = ""

try {
    if ([Environment]::UserInteractive) {
        $hasExisting = $false
        if (Test-Path $envFile) {
            $envContent = Get-Content $envFile -Raw
            if ($envContent -match "TELEGRAM_BOT_TOKEN=\d+" -and $envContent -match "TELEGRAM_ALLOWED_IDS=\d+") {
                $hasExisting = $true
                Write-Host "`n  [✓] Active Telegram credentials detected in .env." -ForegroundColor Green
                Write-Host "      Press Enter to keep current credentials, or enter 'r' within 60s to reconfigure: " -NoNewline
                $reconfig = ""
                $reconfigTimer = [System.Diagnostics.Stopwatch]::StartNew()
                while ($reconfigTimer.Elapsed.TotalSeconds -lt 60) {
                    if ([Console]::KeyAvailable) {
                        $key = [Console]::ReadKey($true)
                        if ($key.Key -eq [ConsoleKey]::Enter) { break }
                        $reconfig += $key.KeyChar
                        Write-Host $key.KeyChar -NoNewline
                    }
                    Start-Sleep -Milliseconds 50
                }
                Write-Host ""
                if ($reconfig -notmatch "^[rR]") {
                    $configured = $true
                }
            }
        }

        if (-not $configured) {
            Write-Host "`n======================================================================" -ForegroundColor Cyan
            Write-Host "  🤖 TELEGRAM CREDENTIALS CONFIGURATION (Auto-timeout: 60 seconds)" -ForegroundColor Cyan
            Write-Host "======================================================================" -ForegroundColor Cyan
            Write-Host "  Enter your credentials below, or press Enter to skip and configure later.`n"

            function Get-InputWithTimeout($promptText, $timeoutSec = 60) {
                Write-Host "$promptText " -NoNewline
                $result = ""
                $timer = [System.Diagnostics.Stopwatch]::StartNew()
                while ($timer.Elapsed.TotalSeconds -lt $timeoutSec) {
                    if ([Console]::KeyAvailable) {
                        $key = [Console]::ReadKey($true)
                        if ($key.Key -eq [ConsoleKey]::Enter) {
                            Write-Host ""
                            return $result.Trim()
                        } elseif ($key.Key -eq [ConsoleKey]::Backspace) {
                            if ($result.Length -gt 0) {
                                $result = $result.Substring(0, $result.Length - 1)
                                Write-Host "`b `b" -NoNewline
                            }
                        } else {
                            $result += $key.KeyChar
                            Write-Host $key.KeyChar -NoNewline
                        }
                    }
                    Start-Sleep -Milliseconds 50
                }
                Write-Host "`n[Timeout reached (60s)]"
                return ""
            }

            $tokenVal = Get-InputWithTimeout "  1. Enter your TELEGRAM_BOT_TOKEN (from @BotFather):" 60
            $idsVal = Get-InputWithTimeout "  2. Enter your TELEGRAM_ALLOWED_IDS (numeric ID from @userinfobot):" 60

            if ($tokenVal -ne "" -and $idsVal -ne "") {
                $content = Get-Content $envFile
                $newContent = @()
                $hasToken = $false
                $hasIds = $false
                $hasAutoStart = $false
                foreach ($line in $content) {
                    if ($line -match "^TELEGRAM_BOT_TOKEN=") {
                        $newContent += "TELEGRAM_BOT_TOKEN=$tokenVal"
                        $hasToken = $true
                    } elseif ($line -match "^TELEGRAM_ALLOWED_IDS=") {
                        $newContent += "TELEGRAM_ALLOWED_IDS=$idsVal"
                        $hasIds = $true
                    } elseif ($line -match "^NODE_AUTO_START=") {
                        $newContent += "NODE_AUTO_START=true"
                        $hasAutoStart = $true
                    } else {
                        $newContent += $line
                    }
                }
                if (-not $hasToken) { $newContent += "TELEGRAM_BOT_TOKEN=$tokenVal" }
                if (-not $hasIds) { $newContent += "TELEGRAM_ALLOWED_IDS=$idsVal" }
                if (-not $hasAutoStart) { $newContent += "NODE_AUTO_START=true" }
                Set-Content -Path $envFile -Value $newContent
                Write-Host "`n  [✓] Telegram credentials successfully configured in .env!" -ForegroundColor Green
                $configured = $true
            } else {
                Write-Host "`n  [!] Credentials setup skipped or timed out." -ForegroundColor Yellow
                Write-Host "      Please edit .env manually before starting: notepad .env`n"
            }
        }
    }
} catch {
    Write-Warn "Credentials Intake" "Non-interactive environment detected. Skipping prompt."
}

if ($configured) {
    Write-Host "`n======================================================================" -ForegroundColor Cyan
    Write-Host "  🚀 Credentials Configured! Starting OptimAI Bot & AI Miner..." -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot "start.bat")
} else {
    Write-Host "`n======================================================================" -ForegroundColor Cyan
    Write-Host "  🎉 Windows Setup Complete! Node is Ready to Run!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Cyan
    Write-Host "  1. Enter your Telegram credentials:  notepad .env" -ForegroundColor Yellow
    Write-Host "  2. Start Bot and AI Miner together:  .\start.bat" -ForegroundColor Green
    Write-Host "  3. Telegram Bot Control:             Send /start in Telegram" -ForegroundColor White
    Write-Host "======================================================================`n"
}
