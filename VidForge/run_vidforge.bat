@echo off
title VidForge AI Studio - Launcher
color 0b

echo =======================================================================
echo                 VIDFORGE AI VIDEO STUDIO LAUNCHER
echo =======================================================================
echo.

:: Paths are resolved from this script's location, so the workspace can live on any drive
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "AI_ROOT=%%~fI"
if not defined VIDFORGE_COMFYUI_PORTABLE set "VIDFORGE_COMFYUI_PORTABLE=%AI_ROOT%\ComfyUI_windows_portable"
if not defined OLLAMA_MODELS set "OLLAMA_MODELS=%AI_ROOT%\ollama-models"

:: 1. Start Ollama if not already active
netstat -ano | findstr "11434" >nul
if %errorlevel% neq 0 (
    echo [1/5] Starting Ollama Server ^(Port 11434^)...
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        start "Ollama Server" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
    ) else (
        start "Ollama Server" /min ollama serve
    )
) else (
    echo [1/5] Ollama Server is already running.
)

:: 2. Start ComfyUI Portable if not already active
netstat -ano | findstr "8188" >nul
if %errorlevel% neq 0 (
    if exist "%VIDFORGE_COMFYUI_PORTABLE%\run_nvidia_gpu.bat" (
        echo [2/5] Starting ComfyUI Portable ^(Port 8188^)...
        pushd "%VIDFORGE_COMFYUI_PORTABLE%"
        start "ComfyUI Server" /min cmd.exe /k "run_nvidia_gpu.bat"
        popd
    ) else (
        echo [2/5] ComfyUI not found at "%VIDFORGE_COMFYUI_PORTABLE%" - start it manually on port 8188.
    )
) else (
    echo [2/5] ComfyUI is already running.
)

:: 3. Build the web UI on first run (ui\dist is not stored in git)
if not exist "%SCRIPT_DIR%ui\dist\index.html" (
    echo [3/5] Building the web UI ^(first run only^)...
    pushd "%SCRIPT_DIR%ui"
    call npm ci
    call npm run build
    popd
) else (
    echo [3/5] Web UI already built.
)

:: 4. Start VidForge Web Studio (FastAPI + Queue Worker) on Port 8700
echo [4/5] Starting VidForge Web UI and Background Engine ^(Port 8700^)...
pushd "%SCRIPT_DIR%backend"
start "VidForge Studio" cmd.exe /k "uv run python main.py"
popd

:: 5. Wait for Web UI to be ready, then open browser
echo [5/5] Waiting for services to initialize...
timeout /t 3 /nobreak >nul

echo Opening VidForge AI Studio in your browser...
start http://127.0.0.1:8700

echo.
echo =======================================================================
echo  VidForge Studio is LIVE at: http://127.0.0.1:8700
echo  - Ollama LLM: Port 11434
echo  - ComfyUI: Port 8188
echo  - VidForge Web UI: Port 8700
echo =======================================================================
echo.
pause
