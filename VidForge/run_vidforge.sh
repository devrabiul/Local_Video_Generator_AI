#!/usr/bin/env bash
# VidForge AI Studio launcher for macOS and Linux (Windows uses run_vidforge.bat)
#
# Optional environment variables:
#   VIDFORGE_COMFYUI_DIR  ComfyUI folder (default: <workspace>/ComfyUI)
#   OLLAMA_MODELS         Ollama model store (default: <workspace>/ollama-models if it exists)
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMFYUI_DIR="${VIDFORGE_COMFYUI_DIR:-$AI_ROOT/ComfyUI}"
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"

if [ -z "${OLLAMA_MODELS:-}" ] && [ -d "$AI_ROOT/ollama-models" ]; then
    export OLLAMA_MODELS="$AI_ROOT/ollama-models"
fi

STARTED_PIDS=()
cleanup() {
    for pid in "${STARTED_PIDS[@]:-}"; do
        [ -n "$pid" ] && kill "$pid" 2>/dev/null
    done
}
trap cleanup EXIT INT TERM

is_up() {
    curl -s -o /dev/null --max-time 2 "$1"
}

echo "======================================================================="
echo "                VIDFORGE AI VIDEO STUDIO LAUNCHER"
echo "======================================================================="

# 1. Ollama
if is_up "http://127.0.0.1:11434/api/tags"; then
    echo "[1/5] Ollama Server is already running."
elif command -v ollama >/dev/null 2>&1; then
    echo "[1/5] Starting Ollama Server (Port 11434)... log: $LOG_DIR/ollama.log"
    ollama serve >"$LOG_DIR/ollama.log" 2>&1 &
    STARTED_PIDS+=($!)
else
    echo "[1/5] WARNING: 'ollama' not found. Install it from https://ollama.com/download"
fi

# 2. ComfyUI
if is_up "http://127.0.0.1:8188/system_stats"; then
    echo "[2/5] ComfyUI is already running."
elif [ -f "$COMFYUI_DIR/main.py" ]; then
    COMFY_PY="python3"
    for candidate in "$COMFYUI_DIR/.venv/bin/python" "$COMFYUI_DIR/venv/bin/python"; do
        if [ -x "$candidate" ]; then COMFY_PY="$candidate"; break; fi
    done
    echo "[2/5] Starting ComfyUI (Port 8188)... log: $LOG_DIR/comfyui.log"
    (cd "$COMFYUI_DIR" && "$COMFY_PY" main.py --listen 127.0.0.1 --port 8188) >"$LOG_DIR/comfyui.log" 2>&1 &
    STARTED_PIDS+=($!)
else
    echo "[2/5] WARNING: ComfyUI not found at $COMFYUI_DIR (set VIDFORGE_COMFYUI_DIR)."
fi

# 3. Web UI build (ui/dist is not stored in git)
if [ ! -f "$SCRIPT_DIR/ui/dist/index.html" ]; then
    if ! command -v npm >/dev/null 2>&1; then
        echo "ERROR: npm not found. Install Node.js 20.19+ or 22.12+ to build the UI."
        exit 1
    fi
    echo "[3/5] Building the web UI (first run only)..."
    (cd "$SCRIPT_DIR/ui" && npm ci && npm run build) || { echo "ERROR: UI build failed."; exit 1; }
else
    echo "[3/5] Web UI already built."
fi

# 4. Backend
if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: 'uv' not found. Install it from https://docs.astral.sh/uv/"
    exit 1
fi

# 5. Open the browser once the backend answers
(
    for _ in $(seq 1 60); do
        if is_up "http://127.0.0.1:8700/api/system/status"; then
            if command -v open >/dev/null 2>&1; then open "http://127.0.0.1:8700"
            elif command -v xdg-open >/dev/null 2>&1; then xdg-open "http://127.0.0.1:8700" >/dev/null 2>&1
            fi
            exit 0
        fi
        sleep 1
    done
) &

echo "[4/5] Starting VidForge Web UI and Background Engine (Port 8700)..."
echo "[5/5] The browser opens automatically at http://127.0.0.1:8700 - press Ctrl+C to stop."
cd "$SCRIPT_DIR/backend" && uv run python main.py
