@echo off
title VidForge AI Studio - 1-Click Launch
color 0b

echo =======================================================================
echo                 VIDFORGE AI VIDEO STUDIO LAUNCHER
echo =======================================================================
echo.

:: 1. Setup Ollama Environment & Start Server if not already active
set OLLAMA_MODELS=D:\AI\ollama-models
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
    cd /d "D:\AI\ComfyUI_windows_portable"
    start "ComfyUI Server" /min cmd.exe /k "run_nvidia_gpu.bat"
) else (
    echo [2/4] ComfyUI Portable is already running.
)

:: 3. Start VidForge Web Studio (FastAPI + Queue Worker) on Port 8700
echo [3/4] Starting VidForge Web UI & Background Engine (Port 8700)...
cd /d "D:\AI\VidForge\backend"
start "VidForge Studio" cmd.exe /k "uv run python main.py"

:: 4. Wait for Web UI to be ready, then open browser
echo [4/4] Waiting for services to initialize...
timeout /t 3 /nobreak >nul

echo Opening VidForge AI Studio in your browser...
start http://127.0.0.1:8700

echo.
echo =======================================================================
echo  VidForge Studio is LIVE at: http://127.0.0.1:8700
echo  - Ollama LLM: Running (Qwen 3.5:9B)
echo  - ComfyUI: Running (Wan 2.1 I2V 14B + Z-Image Turbo)
echo  - VidForge Web UI & Queue: Running
echo =======================================================================
echo.
pause
