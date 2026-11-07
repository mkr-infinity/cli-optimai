@echo off
REM ============================================================
REM setup-windows.bat — Batch Launcher for Windows Setup
REM OptimAI Telegram Node (v1.3.0)
REM ============================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-windows.ps1"
if %ERRORLEVEL% neq 0 (
    echo.
    echo Setup encountered an error. Please ensure PowerShell and Python are installed.
    pause
)
