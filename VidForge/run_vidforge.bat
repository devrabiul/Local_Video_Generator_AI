@echo off
title VidForge AI Studio - Launcher
color 0b

echo =======================================================================
echo                 VIDFORGE AI VIDEO STUDIO LAUNCHER
echo =======================================================================
echo.

set SCRIPT_DIR=%~dp0
set AI_ROOT=%SCRIPT_DIR%..
cd /d "%AI_ROOT%"

:: 1. Setup Ollama Environment & Start Server if not already active
set OLLAMA_MODELS=%AI_ROOT%\ollama-models
netstat -ano | findstr "11434" >nul
if %errorlevel% neq 0 (
    echo [1/4] Starting Ollama Server (Port 11434)...
    start "Ollama Server" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
) else (
    echo [1/4] Ollama Server is already running.
)

:: 2. Start ComfyUI Portable if not already active
netstat -ano | findstr "8188" >nul
if %errorlevel% neq 0 (
    echo [2/4] Starting ComfyUI Portable (Port 8188)...
    cd /d "%AI_ROOT%\ComfyUI_windows_portable"
    start "ComfyUI Server" /min cmd.exe /k "run_nvidia_gpu.bat"
) else (
    echo [2/4] ComfyUI Portable is already running.
)

:: 3. Start VidForge Web Studio (FastAPI + Queue Worker) on Port 8700
echo [3/4] Starting VidForge Web UI & Background Engine (Port 8700)...
cd /d "%SCRIPT_DIR%backend"
start "VidForge Studio" cmd.exe /k "uv run python main.py"

:: 4. Wait for Web UI to be ready, then open browser
echo [4/4] Waiting for services to initialize...
timeout /t 3 /nobreak >nul

echo Opening VidForge AI Studio in your browser...
start http://127.0.0.1:8700

echo.
echo =======================================================================
echo  VidForge Studio is LIVE at: http://127.0.0.1:8700
echo  - Ollama LLM: Running (Port 11434)
echo  - ComfyUI: Running (Port 8188)
echo  - VidForge Web UI: Running (Port 8700)
echo =======================================================================
echo.
pause
