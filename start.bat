@echo off
REM ============================================================
REM start.bat — Universal Launcher for Windows
REM OptimAI Telegram Node (v1.9.0)
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
