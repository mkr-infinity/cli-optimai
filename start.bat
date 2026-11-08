@echo off
REM ============================================================
REM start.bat — Universal Launcher for Windows
REM OptimAI Telegram Bot (v1.9.0)
REM ============================================================

setlocal enabledelayedexpansion

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo [!] Created .env from .env.example. Please edit .env with your credentials.
    ) else (
        echo [ERROR] .env file missing!
        pause
        exit /b 1
    )
)

set NODE_AUTO_START=true

findstr /R "^TELEGRAM_BOT_TOKEN=[0-9]" .env >nul 2>&1
if errorlevel 1 (
    echo.
    echo ======================================================================
    echo   ⛏️  Starting Official OptimAI Node (optimai-cli node start)...
    echo ======================================================================
    echo   Notice: Telegram Bot credentials not configured in .env.
    echo   Starting the official OptimAI mining node directly...
    echo.
    optimai-cli node start
    exit /b 0
)

if not exist data\data mkdir data\data >nul 2>&1
if not exist data\home mkdir data\home >nul 2>&1

set PY_BIN=python
if exist .venv\Scripts\python.exe (
    set PY_BIN=.venv\Scripts\python.exe
)

echo.
echo ======================================================================
echo   🚀 Starting OptimAI Telegram Bot and AI Miner on Windows...
echo ======================================================================
echo   • AI Miner:     NODE_AUTO_START=true
echo   • Telegram:     Send /start in Telegram once connected
echo ======================================================================
echo.

%PY_BIN% -m bot.main
