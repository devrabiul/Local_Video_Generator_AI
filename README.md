# 🎬 VidForge AI Studio — Next-Gen Cinematic Film Suite

An automated end-to-end AI video production workstation with local LLM story writing, zero-shot voice cloning, cinematic character animation, talking head lip-syncing, and background music composition.

Powered by:
- ⚡ **NVIDIA RTX GPU Acceleration** (RTX 5070 Ti 16GB / RTX 40-series)
- 🤖 **Ollama LLM** (`qwen2.5:14b` / `story-writer` / `qwen3.5:9b`)
- 🎙️ **F5-TTS Zero-Shot Voice Cloning** (Local GPU) & **ElevenLabs API** (Studio Voices) & **Edge-TTS**
- 🎬 **ComfyUI + Wan 2.1 Image-to-Video (I2V 14B)** & **Z-Image-Turbo**
- 🗣️ **LivePortrait Talking Photo & Lip-Sync Engine**
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
│   │   └── models/F5-TTS/           # Local F5-TTS model checkpoints
│   ├── ui/                          # Modern React + TypeScript + Vite frontend
│   │   ├── src/                     # Source components & styling
│   │   └── dist/                    # Compiled production build
│   ├── music/                       # Cinematic royalty-free soundtrack themes
│   ├── workflows/                   # ComfyUI API JSON workflows (Wan 2.1 & Z-Image-Turbo)
│   ├── run_vidforge.bat             # One-click studio launcher
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
3. Create the custom VidForge story writer persona:
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
2. Initialize Python virtual environment (`uv run`).
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
