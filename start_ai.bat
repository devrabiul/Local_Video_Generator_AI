@echo off
title Local AI Services (Ollama + ComfyUI)
echo ========================================================
echo Starting Ollama and ComfyUI for VidForge pipeline...
echo ========================================================

:: 1. Ensure OLLAMA_MODELS points to D:\AI\ollama-models
set OLLAMA_MODELS=D:\AI\ollama-models

:: 2. Start Ollama in background window
start "Ollama Server" /min "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve

:: 3. Start ComfyUI Portable
cd /d "D:\AI\ComfyUI_windows_portable"
call run_nvidia_gpu.bat
