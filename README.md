# 🎬 VidForge AI Studio — Next-Gen Cinematic Film Suite

An automated end-to-end AI video production workstation with local LLM story writing, zero-shot voice cloning, cinematic character animation, and background music composition.

Powered by:
- ⚡ **NVIDIA RTX GPU Acceleration** (RTX 5070 Ti 16GB / RTX 40-series)
- 🤖 **Ollama LLM** (`qwen2.5:14b` / `story-writer` / `qwen3.5:9b`)
- 🎙️ **F5-TTS Zero-Shot Voice Cloning** (Local GPU) & **ElevenLabs API** (Studio Voices) & **Edge-TTS**
- 🎬 **ComfyUI + Wan 2.1 Image-to-Video (I2V)** & **Z-Image-Turbo**
- 💎 **Cyber-Glassmorphic React + Vite Web Studio**

---

## 📂 Repository Structure

```text
D:\AI\
├── VidForge/                        # Main AI Video Production Application
│   ├── backend/                     # FastAPI backend engine & pipeline worker
│   │   ├── ai_engine.py             # Orchestration: Ollama + ComfyUI + F5-TTS + FFmpeg
│   │   ├── worker.py                # Asynchronous queue processor
│   │   ├── f5_infer_cli.py          # Standalone F5-TTS inference CLI
│   │   ├── ref_voices/              # Preset reference voice samples
│   │   └── models/F5-TTS/           # Local F5-TTS model checkpoints (downloaded separately)
│   ├── ui/                          # Modern React + TypeScript + Vite frontend
│   │   ├── src/                     # Source components & styling
│   │   └── dist/                    # Compiled production build
│   ├── music/                       # Cinematic royalty-free soundtrack themes
│   ├── workflows/                   # ComfyUI API JSON workflows (Wan 2.1 & Z-Image-Turbo)
│   ├── run_vidforge.bat             # One-click studio launcher
│   └── plan.md                      # Architecture blueprint & development roadmap
├── Modelfile                        # Custom Ollama storyteller persona definition
├── start_ai.bat                     # Service helper launcher
└── README.md                        # Setup and configuration guide
```

---

## 🚀 Setting Up on a New Computer

### 1. Clone this Repository
Clone the repository into your preferred drive (e.g. `D:\AI`):
```bash
git clone <your-repository-url> D:\AI
cd D:\AI
```

---

### 2. Install & Configure Ollama
1. Download and install [Ollama](https://ollama.com/download/windows).
2. Download a storytelling model (Qwen 2.5 14B recommended):
   ```bash
   ollama run qwen2.5:14b
   ```
3. *(Optional)* Create the custom VidForge story writer model:
   ```bash
   cd D:\AI
   ollama create story-writer -f Modelfile
   ```

---

### 3. Setup ComfyUI Windows Portable & Models
1. Download [ComfyUI Portable for Windows](https://github.com/comfyanonymous/ComfyUI/releases).
2. Extract it to:
   ```text
   D:\AI\ComfyUI_windows_portable\
   ```
3. Place your model checkpoints:
   - **Wan 2.1 I2V Model**: Place in `D:\AI\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\`
   - **CLIP Vision**: Place in `D:\AI\ComfyUI_windows_portable\ComfyUI\models\clip_vision\`
   - **Wan 2.1 VAE**: Place in `D:\AI\ComfyUI_windows_portable\ComfyUI\models\vae\`
4. Install `f5-tts` inside ComfyUI's embedded Python:
   ```bash
   D:\AI\ComfyUI_windows_portable\python_embeded\python.exe -m pip install f5-tts soundfile
   ```

---

### 4. Download F5-TTS Voice Cloning Weights
Create the directory `D:\AI\VidForge\backend\models\F5-TTS\` and place the pre-trained F5-TTS checkpoint:
- Checkpoint: `model_1250000.safetensors` or `model_1250000.pt`
- Download from HuggingFace: [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS)
```bash
mkdir D:\AI\VidForge\backend\models\F5-TTS
# Download model_1250000.safetensors into this folder
```

---

### 5. Launch VidForge AI Studio
Simply double-click:
```text
D:\AI\VidForge\run_vidforge.bat
```
The script will automatically:
1. Verify Ollama & ComfyUI services.
2. Initialize the Python virtual environment (`uv run`).
3. Launch the FastAPI backend on `http://127.0.0.1:8700`.
4. Open the VidForge AI Studio in your default browser.

---

## 🎙️ Optional: ElevenLabs Integration
To enable ultra-realistic cloud voice actors alongside local F5-TTS:
1. Open the studio web interface at `http://127.0.0.1:8700/`.
2. Click the **ElevenLabs Capsule** in the header.
3. Paste your [ElevenLabs](https://elevenlabs.io/) API Key and click **Save & Activate**.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for details.
