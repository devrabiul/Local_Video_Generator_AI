@echo off
title Local AI Services (Ollama + ComfyUI)
echo ========================================================
echo Starting Ollama and ComfyUI for VidForge pipeline...
echo ========================================================

:: Paths are resolved from this script's location
set "AI_ROOT=%~dp0"
if not defined OLLAMA_MODELS set "OLLAMA_MODELS=%AI_ROOT%ollama-models"

:: 1. Start Ollama in background window
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
    start "Ollama Server" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
) else (
    start "Ollama Server" /min ollama serve
)

:: 2. Start ComfyUI Portable
cd /d "%AI_ROOT%ComfyUI_windows_portable"
call run_nvidia_gpu.bat
