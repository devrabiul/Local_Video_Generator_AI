# 🎬 VidForge AI Studio — Next-Gen Cinematic Film Suite

An automated end-to-end AI video production workstation with local LLM story writing, zero-shot voice cloning, cinematic character animation, talking head lip-syncing, and background music composition.

Powered by:
- ⚡ **NVIDIA RTX GPU Acceleration** (RTX 5070 Ti 16GB / RTX 40-series)
- 🤖 **Ollama LLM** (`qwen2.5:14b` / `story-writer` / `qwen3.5:9b`)
- 🎙️ **Gemini 3.8 Flash TTS** (expressive narration) & **ElevenLabs v4** (Studio Voices) & **F5-TTS** (local cloning of your own voice)
- 🎬 **ComfyUI + Wan 2.1 Image-to-Video (I2V 14B)** & **Z-Image-Turbo**
- 🗣️ **LivePortrait Talking Photo & Lip-Sync Engine**
- 💎 **Cyber-Glassmorphic React + Vite Web Studio**

---

## 💻 Platform Support

| Platform | Status | Notes |
| :--- | :--- | :--- |
| **Windows 10/11 + NVIDIA RTX** | ✅ Full | ComfyUI portable, NVENC encoding, Wan 2.1 motion. Launch with `run_studio.bat`. |
| **Linux + NVIDIA RTX** | ✅ Full | Manual ComfyUI install, NVENC encoding, Wan 2.1 motion. Launch with `VidForge/run_vidforge.sh`. |
| **macOS (Apple Silicon)** | ⚠️ Partial | Everything except Wan 2.1 AI motion (FP8 weights are not supported on Apple GPUs). Ken Burns motion is used instead and video is encoded with VideoToolbox. 32 GB+ unified memory recommended. |
| **Any OS without NVIDIA** | ⚠️ Partial | Falls back to CPU encoding (`libx264`); image generation is slow. |

The video encoder is detected automatically on first use (`h264_nvenc` → `h264_videotoolbox` → `libx264`). The workspace can live in any folder; paths are resolved relative to the repository.

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
│   │   └── models/F5-TTS/           # Local F5-TTS model checkpoints
│   ├── ui/                          # Modern React + TypeScript + Vite frontend
│   │   ├── src/                     # Source components & styling
│   │   └── dist/                    # Compiled production build
│   ├── music/                       # Cinematic royalty-free soundtrack themes
│   ├── workflows/                   # ComfyUI API JSON workflows (Wan 2.1 & Z-Image-Turbo)
│   ├── run_vidforge.bat             # One-click studio launcher (Windows)
│   ├── run_vidforge.sh              # One-click studio launcher (macOS / Linux)
│   └── plan.md                      # Architecture blueprint & development roadmap
├── ComfyUI_windows_portable/        # Portable ComfyUI Engine with embedded Python 3.13
│   ├── ComfyUI/
│   │   ├── custom_nodes/            # Extension nodes (LivePortrait, VHS,KJNodes, RIFE)
│   │   └── models/                  # All AI checkpoints, VAEs, Text Encoders & Diffusion weights
├── ollama-models/                   # Ollama local LLM storage
├── Modelfile                        # Custom Ollama storyteller persona definition
├── run_studio.bat                   # Unified 1-click launcher for all services
├── start_ai.bat                     # Service helper launcher
└── README.md                        # Setup and configuration guide
```

---

## 🧠 Complete AI Models & Download Inventory

This table lists every AI model used across VidForge, its purpose, exact file name, destination directory, and direct download source for future setups.

| AI Model / Component | Exact File Name | Destination Folder | Source / Download Link |
| :--- | :--- | :--- | :--- |
| **Wan 2.1 I2V 14B (FP8)**<br>*(Cinematic Image-to-Video)* | `wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors` | `ComfyUI/models/diffusion_models/` | [HuggingFace (Wan-AI / Kijai)](https://huggingface.co/Kijai/WanVideo_comfy/tree/main) |
| **Z-Image Turbo (BF16)**<br>*(Fast Image Generation)* | `z_image_turbo_bf16.safetensors` | `ComfyUI/models/diffusion_models/` | [HuggingFace](https://huggingface.co/) |
| **Z-Image Turbo (INT8)** | `z_image_turbo_int8_convrot.safetensors` | `ComfyUI/models/diffusion_models/` | [HuggingFace](https://huggingface.co/) |
| **Z-Image Qwen3-4B Text Encoder** | `qwen_3_4b_fp8_mixed.safetensors` | `ComfyUI/models/text_encoders/` | [HuggingFace (Comfy-Org)](https://huggingface.co/Comfy-Org/z_image_turbo/tree/main/split_files/text_encoders) |
| **Wan 2.1 UMT5 Text Encoder** | `umt5_xxl_fp8_e4m3fn_scaled.safetensors` | `ComfyUI/models/text_encoders/` | [HuggingFace (Comfy-Org)](https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/tree/main/split_files/text_encoders) |
| **CLIP Vision Model** | `clip_vision_h.safetensors` | `ComfyUI/models/clip_vision/` | [HuggingFace (ComfyUI)](https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/tree/main/split_files/clip_vision) |
| **Wan 2.1 VAE** | `wan_2.1_vae.safetensors` | `ComfyUI/models/vae/` | [HuggingFace (Wan-AI)](https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P) |
| **Qwen / Flux VAE** | `qwen_image_vae.safetensors` / `ae.safetensors` | `ComfyUI/models/vae/` | [HuggingFace](https://huggingface.co/) |
| **ACE-Step Music/Audio** | `ace_step_v1_3.5b.safetensors` | `ComfyUI/models/checkpoints/` | [HuggingFace](https://huggingface.co/) |
| **F5-TTS Zero-Shot Voice** | `model_1250000.safetensors` | `VidForge/backend/models/F5-TTS/` | [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS) |
| **Ollama Storyteller LLM** | `qwen2.5:14b` & `qwen3.5:9b` | `D:\AI\ollama-models` | Via Ollama CLI (`ollama run qwen2.5:14b`) |

---

### 🗣️ LivePortrait (Talking Photo & Lip-Sync Models)

Destination Directory: **`D:\AI\ComfyUI_windows_portable\ComfyUI\models\liveportrait\`**  
Repository: [Kijai/LivePortrait_safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors)

| Model Name | Size | Direct Download URL |
| :--- | :--- | :--- |
| **Landmark Model** | ~114.9 MB | [landmark_model.pth](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/landmark_model.pth) |
| **Appearance Feature Extractor** | ~3.36 MB | [appearance_feature_extractor.safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/appearance_feature_extractor.safetensors) |
| **Motion Extractor** | ~112.5 MB | [motion_extractor.safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/motion_extractor.safetensors) |
| **SPADE Generator** | ~221.7 MB | [spade_generator.safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/spade_generator.safetensors) |
| **Warping Module** | ~182.1 MB | [warping_module.safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/warping_module.safetensors) |
| **Stitching & Retargeting Module** | ~0.91 MB | [stitching_retargeting_module.safetensors](https://huggingface.co/Kijai/LivePortrait_safetensors/resolve/main/stitching_retargeting_module.safetensors) |

---

## 🧩 ComfyUI Custom Nodes

All custom nodes are located in `D:\AI\ComfyUI_windows_portable\ComfyUI\custom_nodes\`:

| Node Name | Purpose | Git Repository URL |
| :--- | :--- | :--- |
| **ComfyUI-LivePortraitKJ** | Talking Head, Portrait Animation & Lip-Sync | `https://github.com/kijai/ComfyUI-LivePortraitKJ.git` |
| **ComfyUI-Frame-Interpolation** | RIFE AI Frame Interpolation (Smooth 60FPS) | `https://github.com/Fann-Studio/ComfyUI-Frame-Interpolation.git` |
| **ComfyUI-VideoHelperSuite** | VHS Video Combine & Export | `https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git` |
| **ComfyUI-KJNodes** | Color match, mask processing, utilities | `https://github.com/kijai/ComfyUI-KJNodes.git` |
| **ComfyUI-Manager** | ComfyUI Model & Node Package Manager | `https://github.com/ltdrdata/ComfyUI-Manager.git` |
| **ComfyUI-GGUF** | Quantized GGUF model support | `https://github.com/city96/ComfyUI-GGUF.git` |
| **ComfyUI-RMBG** | Background removal node | `https://github.com/ZHO-ZHO-ZHO/ComfyUI-RMBG.git` |
| **rgthree-comfy** | Workflow routing, muting, and clean cables | `https://github.com/rgthree/rgthree-comfy.git` |

---

## 🚀 Setting Up on a New Computer (Step-by-Step)

### 1. Clone this Repository
Clone the repository into your preferred drive (e.g. `D:\AI`):
```bash
git clone <your-repository-url> D:\AI
cd D:\AI
```

---

### 2. Install & Configure Ollama
1. Download and install [Ollama](https://ollama.com/download/windows).
2. Download storytelling models:
   ```bash
   ollama run qwen2.5:14b
   ollama run qwen3.5:9b
   ```
3. Create the custom VidForge story writer persona (built on `qwen2.5:14b`):
   ```bash
   cd D:\AI
   ollama create story-writer -f Modelfile
   ```

---

### 3. Setup ComfyUI Portable & Custom Nodes
1. Download [ComfyUI Portable for Windows](https://github.com/comfyanonymous/ComfyUI/releases) and extract to `D:\AI\ComfyUI_windows_portable\`.
2. Clone custom nodes into `D:\AI\ComfyUI_windows_portable\ComfyUI\custom_nodes\`:
   ```bash
   cd D:\AI\ComfyUI_windows_portable\ComfyUI\custom_nodes
   git clone https://github.com/kijai/ComfyUI-LivePortraitKJ.git
   git clone https://github.com/Fann-Studio/ComfyUI-Frame-Interpolation.git
   git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
   git clone https://github.com/kijai/ComfyUI-KJNodes.git
   git clone https://github.com/ltdrdata/ComfyUI-Manager.git
   git clone https://github.com/city96/ComfyUI-GGUF.git
   ```
3. Install dependencies into embedded Python:
   ```bash
   D:\AI\ComfyUI_windows_portable\python_embeded\python.exe -m pip install f5-tts soundfile mediapipe pykalman onnx2torch onnxruntime-gpu opencv-contrib-python
   ```

---

### 4. Download Model Checkpoints
Place all downloaded safetensors models according to the **Complete AI Models & Download Inventory** table above:
* Diffusion Models in `ComfyUI/models/diffusion_models/`
* Text Encoders in `ComfyUI/models/text_encoders/`
* CLIP Vision in `ComfyUI/models/clip_vision/`
* VAEs in `ComfyUI/models/vae/`
* LivePortrait in `ComfyUI/models/liveportrait/`
* F5-TTS checkpoint in `VidForge/backend/models/F5-TTS/model_1250000.safetensors`

---

### 5. Launch VidForge AI Studio
Simply run:
```text
D:\AI\run_studio.bat
```
or double-click:
```text
D:\AI\VidForge\run_vidforge.bat
```
The script will automatically:
1. Verify Ollama & ComfyUI services.
2. Build the web UI on first run (`npm ci && npm run build`, requires Node.js 20.19+).
3. Initialize Python virtual environment (`uv run`).
4. Launch the FastAPI backend on `http://127.0.0.1:8700`.
5. Open the VidForge AI Studio in your default browser.

---

## 🐧 Setting Up on Linux or macOS

Requirements: [Ollama](https://ollama.com/download), [uv](https://docs.astral.sh/uv/), Node.js 20.19+, FFmpeg (`brew install ffmpeg` / `sudo apt install ffmpeg`), Git.

1. Clone the repository into any folder (referred to as `<workspace>`).
2. Install Ollama models and create the persona: `ollama pull qwen2.5:14b && ollama create story-writer -f Modelfile`.
3. Install ComfyUI into `<workspace>/ComfyUI` (or set `VIDFORGE_COMFYUI_DIR`):
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI.git ComfyUI
   cd ComfyUI && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   .venv/bin/pip install f5-tts soundfile
   ```
   On Linux install the CUDA build of PyTorch first; on macOS the default PyTorch build uses the Apple GPU (MPS).
4. Place the models as described in the inventory above (Wan 2.1 models can be skipped on macOS).
5. Launch: `./VidForge/run_vidforge.sh`

### Configuration
Copy `VidForge/backend/config.example.json` to `VidForge/backend/config.json` and fill in only what differs from the defaults. Environment variables override the file:

| Setting | Environment variable | Default |
| :--- | :--- | :--- |
| `comfyui_dir` | `VIDFORGE_COMFYUI_DIR` | `<workspace>/ComfyUI_windows_portable/ComfyUI` (Windows), `<workspace>/ComfyUI` (macOS/Linux) |
| `f5_python` | `VIDFORGE_F5_PYTHON` | ComfyUI's embedded Python or its `.venv`/`venv` |
| `ffmpeg_path` / `ffprobe_path` | `VIDFORGE_FFMPEG` / `VIDFORGE_FFPROBE` | `ffmpeg` / `ffprobe` on `PATH` |
| `video_encoder` | `VIDFORGE_VIDEO_ENCODER` | `auto` |
| `gemini_tts_model` | `VIDFORGE_GEMINI_TTS_MODEL` | `gemini-3.8-flash-tts` |
| `elevenlabs_model` / `elevenlabs_stability` | `VIDFORGE_ELEVENLABS_MODEL` / `VIDFORGE_ELEVENLABS_STABILITY` | `eleven_v4` / `0.35` (lower = more expressive) |
| `f5_checkpoint` / `f5_vocab` | `VIDFORGE_F5_CHECKPOINT` / `VIDFORGE_F5_VOCAB` | built-in F5-TTS base model |
| `local_tts_model` | `VIDFORGE_LOCAL_TTS_MODEL` | `f5` — or `omnivoice` (best Bengali/Hindi, non-commercial weights) / `indicf5` (MIT, gated) |
| `local_tts_python` | `VIDFORGE_LOCAL_TTS_PYTHON` | same as `f5_python`; point it at the environment where the chosen model is installed |
| `wan_unet` | `VIDFORGE_WAN_UNET` | best installed of: 480p GGUF Q5_K_M → Q4_K_M → 480p FP8 → 720p FP8 |
| `wan_quality` | `VIDFORGE_WAN_QUALITY` | `balanced` (49 frames, 30 steps); `fast` (33, 20) or `quality` (81, 40 — Wan's official defaults) |
| `ollama_models_dir` | `OLLAMA_MODELS` | `~/.ollama/models` (used by the AI Models page) |
| `ollama_url` / `comfyui_url` | `VIDFORGE_OLLAMA_URL` / `VIDFORGE_COMFYUI_URL` | `http://127.0.0.1:11434` / `http://127.0.0.1:8188` |

Restart the backend after changing the configuration.

---

## 🎙️ Voice Engines

| Engine | Where it runs | Notes |
| :--- | :--- | :--- |
| **Gemini TTS** (default) | Google cloud | `gemini-3.8-flash-tts`, Bengali supported, per-scene emotional direction. Needs a [Google AI Studio](https://aistudio.google.com/apikey) key. |
| **ElevenLabs** | ElevenLabs cloud | `eleven_v4` with audio tags and request stitching across scenes. Needs an [ElevenLabs](https://elevenlabs.io/) key. |
| **F5-TTS** | Local GPU | Clones a reference recording. Add your own voice in **Voice Studio → My Voices**. |

To add API keys: open `http://127.0.0.1:8700/`, click the **Voice** capsule in the header, choose Gemini or ElevenLabs, paste the key and click **Save & Activate**.

### How the narration stays natural
- The script writer adds per-scene **delivery** directions (e.g. "hushed, slow, suspenseful"), a narrator persona, and cues such as `[whispers]`, `[sighs]`, `[short pause]`, `[long pause]`. Each engine renders them in its own syntax, and they can be edited in **Story Studio**.
- A short pause (`pause_after`, 0.2–2 s) is added after every scene so lines don't run together.
- ElevenLabs uses request stitching, so each scene continues the delivery of the previous one.

### My Voices (F5-TTS)
Record or upload **8–12 seconds** of a clear, expressive human voice and type its exact transcript. F5-TTS copies the emotion and pacing of the recording, so a lively reading gives lively narration. Recordings are stored in `VidForge/backend/ref_voices/custom/` and are excluded from Git.

The default F5 checkpoint is trained mainly on English and Chinese and cannot read Bengali script. For Bengali or Hindi, pick another **Voice model** in the Local Voice panel of the production form (saved as `local_tts_model`).

| Voice model | Bengali clarity* | Clones My Voices | Licence | Install into the `local_tts_python` environment |
| :--- | :--- | :--- | :--- | :--- |
| **OmniVoice** (`omnivoice`) | best — 22.5% CER | yes | weights CC-BY-NC | `pip install omnivoice soundfile` |
| **MMS Bengali** (`mms_ben`) | good — 26.0% CER, fastest | no (one voice) | CC-BY-NC | `pip install transformers torch soundfile` |
| **F5 Bengali OpenBible** (`f5_bengali`) | weak — ~58% CER | yes | CC-BY-SA | `pip install git+https://github.com/SWivid/F5-TTS.git` |
| **IndicF5** (`indicf5`) | not tested (gated) | yes | MIT | `pip install git+https://github.com/ai4bharat/IndicF5.git`, accept the terms on Hugging Face, `huggingface-cli login` |
| F5-TTS v1 Base (`f5`) | unusable for Bengali | yes | CC-BY-NC | (default) |

\*Character error rate when Whisper large-v3-turbo transcribes the generated Bengali; Whisper scores 12.2% on a real human recording, so lower is clearer. Models download on first use.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for details.
