I'll check the current state of local open-source models first, since this space moves fast.

I can't save files directly in this conversation, so below are three ready-to-save Markdown files. Copy each block into VS Code or Notepad and save it with the filename shown, using UTF-8 encoding. The hardware list has its own file, so it stays on a separate page.

Before writing, I checked the current state of the open models as of October 2026. Several facts shape the recommendations:

- **Wan 2.2** is the last Wan release with open weights. Wan 2.5, 2.6 and 2.7 are closed, API-only products.
- **LTX-2** is a strong open video model, but it ships under the LTX-2 Community License, which permits research and commercial use by companies under 10 million dollars in revenue at no cost.
- **Z-Image-Turbo** is the best fit for your 16 GB card: a distilled 6B model that generates in about eight steps, released under Apache 2.0, that runs under roughly 16GB of VRAM.
- **ACE-Step 1.5** can generate background music. It is MIT-licensed and runs locally with under 4GB of VRAM.
- **Remotion**, the video composition engine, is free for individuals and companies up to three people, with commercial use allowed.
- **Qwen3.5** can act as both the "director" model and the image inspector, because all Qwen3.5 models are natively multimodal with image and video support.
- **Qwen-Image-Edit-2511** handles image refinement. It is the latest release in the Qwen Image Edit series.

---

## File 1 of 3: `HARDWARE.md`

````markdown
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# Workstation Hardware Specification

**Purpose:** Local AI video production workstation (VidForge pipeline)
**Last updated:** 18 October 2026

## 1. Core Components

| # | Component | Model | Qty | Key specification |
|---|-----------|-------|-----|-------------------|
| 1 | Processor | AMD Ryzen 9 9950X (OEM/Tray) | 1 | 16 cores / 32 threads, 4.3–5.7 GHz, Zen 5, AM5, 170 W TDP |
| 2 | CPU Cooler | Arctic Liquid Freezer III Pro 360 ARGB (Black) | 1 | 360 mm AIO liquid cooler |
| 3 | Motherboard | MSI MAG X870 TOMAHAWK (Wi-Fi 7) | 1 | AM5, DDR5, PCIe 5.0 x16 GPU slot, multiple M.2 slots |
| 4 | Memory | Kingston Fury Beast RGB DDR5-6000 16 GB | 2 | 32 GB total, dual channel |
| 5 | Graphics Card | ASUS TUF Gaming GeForce RTX 5070 Ti 16GB GDDR7 OC Edition | 1 | 16 GB VRAM, Blackwell architecture, NVENC/NVDEC, FP8/FP4 tensor cores, ~300 W |
| 6 | Primary Storage | Corsair MP600 PRO XT 1 TB | 1 | M.2 NVMe PCIe Gen4 x4 |
| 7 | Secondary Storage | Transcend 230S 512 GB | 1 | 2.5" SATA III SSD |
| 8 | Power Supply | Corsair RM850e | 1 | 850 W, 80 Plus Gold, ATX 3.1, fully modular |
| 9 | Case | Xigmatek Alphard Pro Mesh (Black) | 1 | Mid tower, E-ATX support, mesh front panel |
| 10 | Case Fans | Arctic P12 Pro Reverse ARGB 120 mm | 3 | Reverse-blade 120 mm fans |

## 2. Displays and Peripherals

| # | Device | Model | Qty |
|---|--------|-------|-----|
| 1 | Monitor | ASUS TUF Gaming VG249QL3A 23.8" FHD (Dual HDMI + DisplayPort) | 2 |
| 2 | Keyboard | Fantech K612 Soldier RGB Gaming Keyboard | 1 |
| 3 | Mouse | MCHOSE K7 Ultra Tri-mode Gaming Mouse | 1 |
| 4 | Mouse | AJAZZ AJ139 V2 MC Wireless Gaming Mouse with Charging Dock | 1 |
| 5 | USB Hub | Yuanxin X-80907 USB Male to Multi-USB Female Hub | 1 |

## 3. AI Workload Capacity Summary

| Resource | Capacity | What it means for local AI video |
|----------|----------|----------------------------------|
| GPU VRAM | 16 GB | Fits one large image or video model at a time (FP8, GGUF or NVFP4 formats). Models must be loaded one after another, not side by side. |
| System RAM | 32 GB | This is the main bottleneck. Large models offload part of their weights to RAM, and 32 GB is tight for video models. |
| CPU | 16C/32T | Excellent for transcription (Whisper on CPU), FFmpeg and Remotion rendering. These can run alongside GPU work. |
| Storage | 1 TB NVMe + 512 GB SATA | Models and software need about 65 GB total. The NVMe drive holds models and programs; the SATA drive holds jobs, outputs and the archive. Over 900 GB remains free on the NVMe for future models and upgrades. |
| Power | 850 W | The CPU and GPU together peak around 500 W, so the PSU has comfortable headroom for 24/7 use. |
| Video encoding | NVENC (Blackwell) | Hardware H.264/HEVC/AV1 export with almost no load on the CPU or the GPU's main cores. |

## 4. Recommended Upgrades (in priority order)

1. **RAM to 64 GB.** Use a 2 × 32 GB DDR5-6000 kit and replace the current sticks; on AM5, four DIMMs usually forces lower memory speeds. This upgrade has the largest impact on stability and speed for video models.
2. **A second NVMe SSD of 2 TB (Gen4)** dedicated to AI models.
3. **A UPS (1000–1500 VA, line-interactive)** to protect 24/7 rendering from power cuts and fluctuations.
````

---

## File 2 of 3: `USER_GUIDE.md`

`````markdown
# VidForge — Local AI Video Pipeline
## Complete Setup, Testing and User Guide

**Version:** 1.0 · **Date:** 18 October 2026
**Target system:** Windows 11, Ryzen 9 9950X, RTX 5070 Ti 16 GB, 32 GB RAM (see HARDWARE.md)

---

## Table of Contents

0. About This Guide
1. Adding the Hardware Page to Your DOCX Document
2. What Your Hardware Can Realistically Do
3. The 10 Recommended Local AI Models
4. Complete List of Third-Party Tools and Plugins
5. System Architecture
6. Step-by-Step Setup
7. Testing the Workflow
8. Daily User Guide
9. Resource Management and Tuning
10. Maintenance and Troubleshooting
11. Licensing Checklist

---

## 0. About This Guide

VidForge is a custom harness. You give it a **script** and a **voice-over**, and it produces a finished **MP4**. Everything else is optional: screenshots, logo, sound effects, music, motion directions, brand colors and so on.

The pipeline:

1. Transcribes your voice-over to get the timing of every word.
2. Uses a local LLM to split the script into timed scenes and write image prompts that match the selected video type.
3. Generates the images locally.
4. Lets you preview each image and refine it with a new prompt.
5. Animates the scenes with camera moves or AI motion.
6. Adds captions, music and sound effects.
7. Exports an MP4 at the aspect ratio you choose, with or without sound.
8. Moves straight on to the next job in the queue, 24/7.

**Conventions used in this guide**

- `C:\AI\` is the program and model location on the NVMe drive.
- `D:\VidForge\` is the jobs, outputs and archive location on the SATA SSD. If your SATA drive has a different letter, replace `D:` everywhere.
- Commands are written for **PowerShell**. Unless a step says otherwise, run it in a normal (non-admin) PowerShell window.

> **Scope note:** This guide gives you the full infrastructure plus a working core skeleton of the backend and renderer code. The full UI is specified in `PRD.md`. You can build it yourself, or hand `PRD.md` and this guide to a coding agent such as Claude Code to generate the remaining screens.

---

## 1. Adding the Hardware Page to Your DOCX Document

There are three ways to get `HARDWARE.md` into your Word document.

### Method A — Copy and paste (simplest, no extra software)

1. Open `HARDWARE.md` in VS Code and press `Ctrl+Shift+V` to open the rendered preview.
2. Select all of the preview (`Ctrl+A`) and copy it (`Ctrl+C`).
3. In Word, place your cursor where the page should go, then press `Ctrl+Enter` to insert a page break.
4. Paste with `Ctrl+V`. If the formatting looks wrong, use **Paste Special → HTML Format** instead.
5. Format the tables: click a table, open **Table Design**, and pick a style.

### Method B — Pandoc conversion (best formatting, recommended)

1. Install Pandoc:
   ```powershell
   winget install --id JohnMacFarlane.Pandoc -e
   ```
2. Convert the file. The block at the top of `HARDWARE.md` is a Word page break, so the content starts on a new page automatically.
   ```powershell
   cd "C:\path\to\your\md\files"
   pandoc HARDWARE.md -o HARDWARE.docx
   ```
3. Open your main DOCX and place the cursor at the insertion point.
4. Go to **Insert → Object (dropdown arrow) → Text from File…**, choose `HARDWARE.docx`, and click **Insert**.

**Optional: match your document's styles.** If you want the converted page to use your document's fonts and colors, use your DOCX as a reference:
```powershell
pandoc HARDWARE.md -o HARDWARE.docx --reference-doc "C:\path\to\YourDocument.docx"
```

### Method C — Convert the whole guide

The same command works for any file. For example:
```powershell
pandoc USER_GUIDE.md -o USER_GUIDE.docx --toc
```
The `--toc` flag adds a table of contents.

---

## 2. What Your Hardware Can Realistically Do

### 2.1 The golden rule: one GPU model family at a time

With 16 GB of VRAM, VidForge **never keeps two large models on the GPU at once**. A "GPU token" (a lock inside the orchestrator) works like this:

1. Load the LLM, plan all scenes, then unload it.
2. Load the image model, generate **all** images for the job, then free it.
3. Load the vision model, check all images, then unload it.
4. Load the video model, animate the selected scenes, then free it.

Batching work by model family is what keeps the system fast and stable.

### 2.2 Two lanes for parallel work

GPU work and CPU work can run at the same time:

| Lane | Runs on | Handles |
|------|---------|---------|
| **GPU lane** | GPU + light CPU | Transcription, planning, image generation, image QA, AI motion, music |
| **Render lane** | CPU + NVENC encoder | Remotion composition and FFmpeg export |

While video N renders on the CPU, the assets for video N+1 are generated on the GPU. This is exactly the "prepare the next video automatically" behaviour you asked for.

### 2.3 Rough throughput estimates

These are planning numbers only. Measure your own in Section 7.

| Video | Length | Images | AI motion clips | Estimated time |
|-------|--------|--------|-----------------|----------------|
| Faceless reel | 45–60 s | 12–15 | 0 (Ken Burns only) | 6–12 min |
| Faceless reel | 45–60 s | 12–15 | 3 (Wan 5B) | 20–40 min |
| SaaS promo | 60–90 s | 10–15 + screenshots | 2 | 20–45 min |
| Storytelling | 3–5 min | 40–60 | 4–6 | 1–2.5 h |

**Practical daily output:** at 24/7 with resource caps, expect roughly **30–80 short videos per day** if you use Ken Burns motion only, or **10–30 per day** with AI motion clips.

---

## 3. The 10 Recommended Local AI Models

Every model below is free and runs fully locally. Licenses are summarised in Section 11.

### 3.1 Summary table

| # | Model | Role in the pipeline | Runs via | Approx. disk | Approx. peak VRAM | License |
|---|-------|---------------------|----------|-----------|----------------|---------|
| 1 | **Qwen3.5-9B** (Q4_K_M) | "Director": scene planning, prompt writing, and vision QA of generated images | Ollama | ~5.5 GB | 8–9 GB | Apache 2.0 |
| 2 | **Z-Image-Turbo** (6B, FP8 UNet + **FP8** T5) | Primary image generator: fast, photoreal and stylised, good text rendering | ComfyUI | ~12.5 GB (FP8 UNet + FP8 T5 encoder + CLIP + VAE) | 10–12 GB | Apache 2.0 |
| 3 | **Qwen-Image-2512** (GGUF Q4_K_M) | Hero images with heavy typography (SaaS headlines, posters) | ComfyUI + GGUF | ~8 GB + ~7.5 GB shared encoder/VAE | 14–15 GB (with offload) | Apache 2.0 |
| 4 | **Qwen-Image-Edit-2511** (GGUF Q4_K_M) | Refining defective images, compositing screenshots into mockups, character consistency | ComfyUI + GGUF | ~8 GB (shares encoder/VAE with #3) | 14–15 GB (with offload) | Apache 2.0 |
| 5 | **Wan 2.2 TI2V-5B** (GGUF **Q4_K_M**) | AI image-to-video motion clips (720p at 24 fps) | ComfyUI | ~7 GB incl. encoder and VAE | 10–12 GB | Apache 2.0 |
| 6 | ~~LTX-2.x distilled~~ | **Deferred** — install after 64 GB RAM upgrade (saves ~20 GB) | — | 0 GB | — | LTX-2 Community |
| 7 | **faster-whisper large-v3-turbo** | Voice-over transcription with word-level timestamps for sync and captions | Python (CPU, int8) | ~1.6 GB | 0 (runs on CPU) | MIT |
| 8 | **ACE-Step 1.5** | Royalty-free background music generation | ComfyUI workflow only (no standalone app) | ~2.5 GB | under 4 GB | MIT |
| 9 | **BiRefNet** | Background removal for logos, product shots and portraits | ComfyUI (RMBG node pack) | ~0.5 GB | 2–4 GB | MIT |
| 10 | **Real-ESRGAN x4plus** (or 4x-UltraSharp) | Upscaling images to 1080p or 4K before composition | ComfyUI built-in upscale nodes | under 100 MB | 1–3 GB | BSD-3 |

**Total model disk footprint: approximately 53 GB.** With software and runtimes (~11 GB) the full installation is about 65 GB, well within 80–100 GB.

**VRAM figures are approximate.** Verify them on your machine with `nvidia-smi` during testing.

**LTX-2.x:** deferred to save ~20 GB. After upgrading to 64 GB RAM, install it to gain faster, higher-resolution AI motion. The ~21 GB headroom in the storage budget accommodates this upgrade.

### 3.2 Why each model was chosen

1. **Qwen3.5-9B.** One model plans scenes (using JSON structured output) *and* looks at images to score defects, because it is natively multimodal. That means one fewer model to swap in and out of VRAM.
2. **Z-Image-Turbo.** It needs only 8 steps, so each image takes seconds. Use it for about 80% of images: reels, storytelling, branding backgrounds and motion graphics plates.
3. **Qwen-Image-2512.** It is slower than Z-Image but the strongest open model for readable text inside images, such as headline cards and UI-like visuals.
4. **Qwen-Image-Edit-2511.** This powers the "Refine" button. You describe the fix ("remove the extra hand", "make the background navy blue") and it edits the image while keeping the rest. It also places your real screenshots into laptop or phone mockups, and it keeps characters consistent by using a reference image.
5. **Wan 2.2 TI2V-5B.** It turns a still image into a short motion clip. It is fully Apache-licensed and fits comfortably in 16 GB. It supports only 1280×704 and 704×1280, so use it for 16:9 and 9:16 videos.
6. **LTX-2.x.** Deferred to save disk space. It is faster and supports more resolutions. Install it after upgrading to 64 GB of RAM — there is enough headroom in the storage budget (~21 GB free).
7. **faster-whisper.** The word timestamps drive the scene timing, word-by-word captions and SFX placement. It runs on the CPU, which leaves the GPU free.
8. **ACE-Step 1.5.** It generates a music bed per video ("upbeat corporate electronic, 110 bpm") so you never worry about copyright claims.
9. **BiRefNet.** It produces clean cutouts for logo reveals, product hero shots and personal-branding portraits.
10. **Real-ESRGAN.** Image models output about 1 megapixel, and upscaling keeps 1080p and 4K exports sharp, especially during Ken Burns zooms.

### 3.3 Model routing by video type

| Video type | Default aspect | Image model | Motion style | Captions | Music |
|------------|---------------|-------------|--------------|----------|-------|
| Motion Graphics | 16:9 | Z-Image (flat or 3D abstract style) | Kinetic text + parallax (Remotion) | Kinetic typography | ACE-Step, energetic |
| SaaS Promo | 16:9 | Qwen-Image for headline visuals; Qwen-Edit for mockups | Screenshot pan/zoom in device frames, plus 1–2 AI motion clips | Kinetic | ACE-Step, corporate |
| Branding | 16:9 or 1:1 | Z-Image + BiRefNet logo cutout | Logo reveal, smooth parallax | Minimal | ACE-Step, cinematic |
| Faceless Reel | 9:16 | Z-Image | Ken Burns + up to 3 Wan clips | Bold word-by-word | ACE-Step, trending style |
| Storytelling | 16:9 or 9:16 | Z-Image + Qwen-Edit for character consistency | Slow Ken Burns; AI motion on key moments | Subtle | ACE-Step, cinematic |
| Personal Branding | 9:16 or 4:5 | Your photos + Qwen-Edit scenes + BiRefNet | Ken Burns, lower-thirds | Bold | ACE-Step, warm |
| Portfolio | 16:9 | Your project images first; AI only for backgrounds | Grid reveals, pans | Minimal | ACE-Step, ambient |

---

## 4. Complete List of Third-Party Tools and Plugins

### 4.1 System software

| Tool | Purpose | Install |
|------|---------|---------|
| NVIDIA Studio Driver (latest) | GPU driver; Studio drivers are tuned for stability | nvidia.com or the NVIDIA App |
| Git for Windows | Cloning repositories | `winget install Git.Git` |
| uv | Python and package manager | `winget install astral-sh.uv` |
| Python 3.12 | Backend runtime (uv installs it) | via uv |
| Node.js 22 LTS | Remotion renderer and UI | `winget install OpenJS.NodeJS.LTS` |
| FFmpeg (full build) | Audio mixing, reframing and NVENC export | `winget install Gyan.FFmpeg` |
| Visual Studio 2022 Build Tools (C++ workload) | Compiling some Python wheels | `winget install Microsoft.VisualStudio.2022.BuildTools` |
| VS Code | Editing configs and code | `winget install Microsoft.VisualStudioCode` |
| 7-Zip | Extracting the ComfyUI portable build | `winget install 7zip.7zip` |
| NSSM | Running everything as auto-restarting Windows services | `winget install NSSM.NSSM` |
| Pandoc | Markdown to DOCX conversion | `winget install JohnMacFarlane.Pandoc` |
| MSI Afterburner | GPU power limit and fan curve (GUI) | msi.com |
| HWiNFO64 | Temperature and power monitoring | hwinfo.com |

If a winget ID fails, download the tool from its official website instead.

### 4.2 AI runtimes

| Tool | Purpose |
|------|---------|
| **Ollama for Windows** (latest) | Serves Qwen3.5-9B through a local API (`winget install Ollama.Ollama`) |
| **ComfyUI Windows Portable (NVIDIA build)** | Runs all image, video, music and upscaling models through its API. Recent portable builds ship PyTorch with CUDA 12.8 or newer, which RTX 50-series cards require. |
| **ComfyUI-Manager** | Installs custom nodes. It is bundled with recent builds; install it from GitHub if missing. |

### 4.3 ComfyUI custom nodes

Install these through ComfyUI-Manager.

| Node pack | Why you need it |
|-----------|-----------------|
| **ComfyUI-GGUF** (city96) | Loads the GGUF-quantised Qwen-Image, Qwen-Edit and Wan models |
| **ComfyUI-VideoHelperSuite** (Kosinkadink) | Saving and loading video frames and MP4 files |
| **ComfyUI-KJNodes** (kijai) | Utility nodes: resizing, masks, batching |
| **ComfyUI-RMBG** (1038lab) | BiRefNet background removal |
| **ComfyUI-Frame-Interpolation** (Fannovel16) | RIFE interpolation to smooth 24 fps clips to 30 or 60 fps |
| **rgthree-comfy** | Workflow organisation and the ability to bypass nodes |
| **ComfyUI-nunchaku** (optional) | 4-bit/FP4 Qwen-Image variants for extra speed on Blackwell cards |

> **Note:** ComfyUI-LTXVideo is not needed at this stage. Install it later when you add LTX-2.x after the RAM upgrade.

### 4.4 Python packages (VidForge backend)

These packages are needed for the core pipeline:
```
fastapi, uvicorn[standard], httpx, pyyaml, psutil, nvidia-ml-py,
faster-whisper, watchdog, pillow, python-multipart, loguru, tenacity
```

### 4.5 Node packages

| Area | Packages |
|------|----------|
| Renderer | `remotion`, `@remotion/cli`, `@remotion/transitions`, `@remotion/google-fonts`, `react`, `zod` |
| UI | `vite`, `react`, `typescript`, `tailwindcss`, `@tanstack/react-query`, `react-hook-form`, `zod`, `wavesurfer.js`, `react-dropzone`, shadcn/ui components |

### 4.6 Optional extras

| Tool | Use |
|------|-----|
| Kokoro-82M TTS (Apache 2.0) | Generating test voice-overs; optional fallback voice-over for autopilot |
| Audacity | Cleaning voice-overs (noise reduction) |
| DaVinci Resolve (free edition) | Manual touch-ups when needed |
| OBS Studio | Recording SaaS screen footage to use as assets |

**Free sound sources:** Freesound with the CC0 filter, and the Sonniss GDC bundles. Always check each source's license.

---

## 5. System Architecture

### 5.1 Component diagram

```
 ┌────────────────────── Browser UI (React) ──────────────────────┐
 │  New Job (dynamic form) · Scene Board (preview/refine) ·        │
 │  Export · Queue Dashboard · Settings · Brand Kits               │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ HTTP :8700
 ┌──────────────────────────────▼──────────────────────────────────┐
 │  VidForge API (FastAPI)  ── SQLite (jobs, scenes, events)        │
 └──────────────────────────────┬──────────────────────────────────┘
                                │ shared DB + D:\VidForge\jobs
 ┌──────────────────────────────▼──────────────────────────────────┐
 │  VidForge Worker (orchestrator)                                  │
 │   ├─ GPU lane:    ingest → transcribe → plan → images → QA →     │
 │   │               [review gate] → motion → music                 │
 │   ├─ Render lane: Remotion render → FFmpeg mix/export (NVENC)    │
 │   ├─ Inbox watcher (D:\VidForge\inbox)                           │
 │   └─ Resource Guard (GPU/CPU/RAM/temp caps)                      │
 └───────┬───────────────────────┬──────────────────────┬──────────┘
         │ :11434                │ :8188                │ CLI
   ┌─────▼─────┐          ┌──────▼──────┐        ┌──────▼──────┐
   │  Ollama   │          │   ComfyUI   │        │  Remotion   │
   │ Qwen3.5-9B│          │ Z-Image,    │        │  + FFmpeg   │
   └───────────┘          │ Qwen-Image, │        └─────────────┘
                          │ Qwen-Edit,  │
                          │ Wan, LTX,   │
                          │ ACE-Step,   │
                          │ BiRefNet,   │
                          │ ESRGAN      │
                          └─────────────┘
```

### 5.2 Pipeline stages

| # | Stage | What happens | Output |
|---|-------|--------------|--------|
| 1 | Ingest | Validates inputs and converts the voice-over to 48 kHz WAV | `input/vo.wav` |
| 2 | Transcribe | faster-whisper produces word timestamps | `transcript.json` |
| 3 | Plan | Qwen3.5 returns a scene list in JSON, using the video type's template and your motion directions | `plan.json` |
| 4 | Images | ComfyUI generates one image per scene at the correct aspect ratio | `scenes/sNN.png` |
| 5 | QA | Qwen3.5 scores each image and lists any defects | `qa.json` |
| 6 | Review gate | You preview, refine and approve. In autopilot, images that pass QA are approved automatically. | approved scenes |
| 7 | Motion | Ken Burns or parallax is set up for Remotion; Wan or LTX generates clips for the scenes flagged for AI motion | `scenes/sNN.mp4` |
| 8 | Music | ACE-Step generates music, or your uploaded file is used | `audio/music.wav` |
| 9 | Render | Remotion composes the scenes, captions, text and transitions into a silent video | `render/video.mp4` |
| 10 | Export | FFmpeg mixes voice-over, music (ducked under the voice) and SFX, reframes the aspect ratio, and encodes with NVENC | `output/<name>.mp4` |

### 5.3 Folder layout

```
C:\AI\
├── ComfyUI_windows_portable\        (ComfyUI + models)
├── ollama-models\                   (OLLAMA_MODELS)
└── vidforge\
    ├── backend\                     (FastAPI + worker, Python)
    │   ├── config.yaml
    │   ├── app\
    │   └── templates\               (one YAML per video type)
    ├── workflows\                   (ComfyUI API-format JSON files)
    ├── renderer\                    (Remotion project)
    └── ui\                          (React app)

D:\VidForge\
├── inbox\                           (drop-folder for automatic jobs)
├── jobs\<job_id>\                   (working files per job)
│   ├── input\  scenes\  audio\  render\  public\
│   └── job.json, plan.json, transcript.json, qa.json
├── output\                          (final MP4s + thumbnails + metadata)
├── archive\
└── logs\
```

---

## 6. Step-by-Step Setup

Do the steps in order. Each one ends with a check so you know it worked.

### Step 1 — Prepare Windows (about 20 minutes)

**1.1 Install the latest NVIDIA Studio Driver.** Use a clean install and reboot afterwards.

**1.2 Stop the driver from silently spilling VRAM into system RAM.** When VRAM runs out, the default driver behaviour moves data into system RAM, which makes jobs extremely slow. Disabling it makes ComfyUI manage memory itself.

1. Open **NVIDIA Control Panel → Manage 3D Settings → Program Settings**.
2. Add `C:\AI\ComfyUI_windows_portable\python_embeded\python.exe`. If that path doesn't exist yet, come back to this step after Step 4.
3. Set **CUDA – Sysmem Fallback Policy** to **Prefer No Sysmem Fallback**.

**1.3 Set the page file.**
1. Open **Settings → System → About → Advanced system settings → Performance → Settings → Advanced → Virtual memory → Change**.
2. On drive C:, choose a custom size: initial 32768 MB, maximum 65536 MB.

**1.4 Set up power for 24/7 operation.**
- **Power plan:** use Balanced. Set **Sleep: Never** and **Turn off display: 15 min**.
- **BIOS:** set **Restore on AC Power Loss** to **Power On**.
- **Optional, for lower heat during 24/7 runs:** enable AMD **Eco Mode (105 W)** in the BIOS (look under AMD Overclocking / Precision Boost Overdrive). You lose a modest amount of CPU speed in exchange for much less heat.

**1.5 Enable Hardware-accelerated GPU scheduling.** It's under **Settings → Display → Graphics → Default graphics settings**. Reboot afterwards.

**1.6 Cap GPU power at about 85%.** This keeps GPU headroom and temperatures in check. Open an **Admin PowerShell** and run:
```powershell
nvidia-smi -q -d POWER        # shows the default and the min/max allowed power limits
nvidia-smi -pl 255            # about 85% of a 300 W default; must be within the allowed range
```
The setting resets on reboot, so make it permanent with a startup task (in the same Admin PowerShell):
```powershell
$a = New-ScheduledTaskAction -Execute "nvidia-smi.exe" -Argument "-pl 255"
$t = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName "GPU-PowerLimit" -Action $a -Trigger $t -RunLevel Highest -User "SYSTEM"
```
If the command is rejected, set the power limit to 85% in MSI Afterburner instead and enable "Apply at startup."

**1.7 Control Windows Update.** Set active hours, and pause updates during long production runs. Do updates in a weekly maintenance window.

✅ **Check:** `nvidia-smi` shows your driver and the new power limit.

### Step 2 — Install base tools (about 15 minutes)

Run in PowerShell:
```powershell
winget install Git.Git astral-sh.uv OpenJS.NodeJS.LTS Gyan.FFmpeg 7zip.7zip Microsoft.VisualStudioCode NSSM.NSSM JohnMacFarlane.Pandoc
winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
```
Close and reopen PowerShell so the new PATH takes effect, then verify:
```powershell
git --version; uv --version; node -v; ffmpeg -hide_banner -encoders | findstr nvenc
```
✅ **Check:** the last command lists `h264_nvenc`, `hevc_nvenc` and `av1_nvenc`.

### Step 3 — Install Ollama and the director model (about 10 minutes)

1. Install Ollama:
   ```powershell
   winget install Ollama.Ollama
   ```
2. Set the environment variables for your user account. Run each line:
   ```powershell
   setx OLLAMA_MODELS "C:\AI\ollama-models"
   setx OLLAMA_MAX_LOADED_MODELS "1"
   setx OLLAMA_NUM_PARALLEL "1"
   setx OLLAMA_FLASH_ATTENTION "1"
   setx OLLAMA_CONTEXT_LENGTH "16384"
   ```
3. Quit Ollama from the system tray, reopen PowerShell, and pull the model:
   ```powershell
   ollama serve        # leave this window open
   # in a second PowerShell window:
   ollama pull qwen3.5:9b
   ollama run qwen3.5:9b "Reply with the single word OK"
   ```
✅ **Check:** the model replies, and `ollama ps` shows it loaded on the GPU.

### Step 4 — Install ComfyUI and the custom nodes (about 20 minutes)

1. Download the **ComfyUI Windows Portable (NVIDIA)** build from the official ComfyUI GitHub releases page. Extract it to `C:\AI\ComfyUI_windows_portable\`.
2. Edit `run_nvidia_gpu.bat` so its launch line reads:
   ```bat
   .\python_embeded\python.exe -s ComfyUI\main.py --windows-standalone-build --listen 127.0.0.1 --port 8188 --reserve-vram 1.5 --disable-auto-launch
   ```
   `--reserve-vram 1.5` keeps about 1.5 GB of VRAM permanently free so the GPU never hits 100% memory use.
3. Double-click `run_nvidia_gpu.bat`, then open `http://127.0.0.1:8188` in your browser.
4. Open **Manager → Custom Nodes Manager** and install every node pack in Section 4.3. Restart ComfyUI afterwards.
5. Go back to Step 1.2 and add ComfyUI's `python.exe` to the NVIDIA Sysmem Fallback setting.

✅ **Check:** `http://127.0.0.1:8188/system_stats` in your browser shows your RTX 5070 Ti and its VRAM.

### Step 5 — Download the models (1–3 hours, depending on your connection)

**The easiest reliable method is the template browser.** In ComfyUI, open **Templates** (left sidebar), find the template for each model below, and open it. ComfyUI lists any missing model files with download links and their target folders. This avoids file-name mistakes as versions change.

| Model | ComfyUI template to open | Files go into | Storage-optimised note |
|-------|--------------------------|---------------|------------------------|
| Z-Image-Turbo | Image → Z-Image-Turbo Text to Image | `models/diffusion_models`, `models/text_encoders`, `models/vae` | **Use the FP8 text encoder** (not FP16) to save ~4 GB. RTX 5070 Ti has native FP8 tensor cores, so quality is identical. |
| Qwen-Image-2512 (GGUF) | Image → Qwen-Image. Then swap the loader for **Unet Loader (GGUF)** and use a Q4_K_M file from a reputable GGUF repo (unsloth or QuantStack). | `models/unet`, `models/text_encoders`, `models/vae` | |
| Qwen-Image-Edit-2511 (GGUF) | Image → Qwen Image Edit. Swap in **Unet Loader (GGUF)** with a Q4_K_M file. | `models/unet` (shares the encoder and VAE) | |
| Wan 2.2 TI2V-5B | Video → Wan 2.2 5B (Image to Video). Swap in the **Q4_K_M** GGUF file. | `models/diffusion_models` or `models/unet`, `models/text_encoders`, `models/vae` | **Use Q4_K_M (not Q8_0)** to save ~6 GB. Motion quality is visually comparable for 5-second 720p clips. |
| ~~LTX-2.x distilled~~ | **Do not download** — deferred until 64 GB RAM upgrade | — | Saves ~20 GB |
| ACE-Step 1.5 | Audio → ACE-Step, if your build includes it. | `models/checkpoints` | **Use ComfyUI workflow only** — do not install the standalone portable app. Saves ~2.5 GB. |
| BiRefNet | Downloads automatically the first time you use the RMBG node | `models/RMBG` | |
| Real-ESRGAN x4plus / 4x-UltraSharp | Manager → Model Manager → search "upscale" | `models/upscale_models` | |

faster-whisper downloads its model automatically on first use (Step 7).

**Avoid these for commercial work:** FLUX.1-dev, FLUX.2-dev and RMBG-2.0 use non-commercial licenses.

**Total model disk usage after download: approximately 53 GB.** Verify with `du -sh C:\AI\ComfyUI_windows_portable\ComfyUI\models` and `du -sh C:\AI\ollama-models`.

✅ **Check:** each template runs once inside ComfyUI and produces an output.

### Step 6 — Build and export the API workflows (about 1 hour)

VidForge controls ComfyUI by loading workflow JSON files and changing specific inputs. It finds those inputs **by node title**, which is much more robust than node ID numbers.

**6.1 Create each workflow.** For each workflow in the table below:
1. Open the matching template in ComfyUI.
2. Rename the key nodes (right-click → **Title**) using the exact titles in the table.
3. Run it once to confirm it works.
4. Use **Workflow → Export (API)** and save it to `C:\AI\vidforge\workflows\` with the filename shown.

| File name | Purpose | Nodes that must be titled |
|-----------|---------|---------------------------|
| `t2i_zimage.json` | Z-Image text-to-image | `VF_PROMPT` (positive text), `VF_LATENT` (empty latent: width/height), `VF_SAMPLER` (KSampler: seed), `VF_SAVE` (Save Image) |
| `t2i_qwenimage.json` | Qwen-Image text-to-image | same titles as above, plus `VF_NEG` (negative prompt) |
| `edit_qwen.json` | Refine an image with an instruction | `VF_LOAD_IMAGE`, `VF_PROMPT`, `VF_SAMPLER`, `VF_SAVE`; optionally `VF_LOAD_IMAGE_2` (second reference) |
| `i2v_wan5b.json` | Image to motion clip | `VF_LOAD_IMAGE`, `VF_PROMPT`, `VF_LATENT` (width/height/length), `VF_SAMPLER`, `VF_SAVE_VIDEO` (VHS Video Combine) |
| ~~`i2v_ltx.json`~~ | ~~Faster image-to-video~~ | Deferred — create this workflow after installing LTX-2.x |
| `music_acestep.json` | Background music | `VF_PROMPT` (tags), `VF_DURATION`, `VF_SAMPLER`, `VF_SAVE_AUDIO` |
| `rmbg.json` | Background removal | `VF_LOAD_IMAGE`, `VF_SAVE` |
| `upscale.json` | 4× upscale, then resize | `VF_LOAD_IMAGE`, `VF_RESIZE` (target width/height), `VF_SAVE` |

**6.2 Image sizes by aspect ratio.** All dimensions are multiples of 16.

| Aspect | Generation size (Z-Image / Qwen) | Final render size |
|--------|----------------------------------|-------------------|
| 16:9 | 1344 × 768 | 1920 × 1080 |
| 9:16 | 768 × 1344 | 1080 × 1920 |
| 1:1 | 1024 × 1024 | 1080 × 1080 |
| 4:5 | 896 × 1120 | 1080 × 1350 |
| 4:3 | 1152 × 864 | 1440 × 1080 |

**Wan 5B only accepts 1280×704 (16:9) or 704×1280 (9:16), with frame counts of the form 4k+1** (121 frames is about 5 seconds at 24 fps). For 1:1 or 4:5 videos, VidForge uses Ken Burns motion. After the RAM upgrade, install LTX-2.x for broader resolution support.

### Step 7 — Build the VidForge backend (about 1–2 hours)

**7.1 Create the project and install dependencies:**
```powershell
mkdir C:\AI\vidforge\backend; cd C:\AI\vidforge\backend
uv init --python 3.12 --no-workspace
uv add fastapi "uvicorn[standard]" httpx pyyaml psutil nvidia-ml-py faster-whisper watchdog pillow python-multipart loguru tenacity
mkdir app, templates
New-Item app\__init__.py
```

**7.2 Create `config.yaml`:**
```yaml
paths:
  inbox:     D:/VidForge/inbox
  jobs:      D:/VidForge/jobs
  output:    D:/VidForge/output
  archive:   D:/VidForge/archive
  logs:      D:/VidForge/logs
  workflows: C:/AI/vidforge/workflows
  renderer:  C:/AI/vidforge/renderer
  templates: C:/AI/vidforge/backend/templates
services:
  ollama:  http://127.0.0.1:11434
  comfyui: http://127.0.0.1:8188
models:
  director: qwen3.5:9b
  whisper:  large-v3-turbo
limits:
  gpu_max_temp_c: 80          # pause new GPU steps above this temperature
  cpu_max_pct: 80             # pause new heavy steps above this CPU usage
  ram_max_pct: 85
  render_concurrency: 8       # Remotion uses 8 of 32 threads
  ffmpeg_threads: 12
  render_affinity: "4-31"     # logical CPUs 0-3 always stay free for Windows and the UI
  whisper_threads: 8
  cooldown_between_jobs_s: 30
pipeline:
  mode: review                # review | autopilot
  qa_min_score: 7             # images scoring 1-10; below this are auto-regenerated
  max_auto_retries: 2
  max_ai_motion_clips: 3      # per video; AI motion is the most expensive step
  default_fps: 30
```

**7.3 Create `app/config.py`:**
```python
import yaml, pathlib
from loguru import logger as log

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
for k in ("inbox", "jobs", "output", "archive", "logs"):
    pathlib.Path(CFG["paths"][k]).mkdir(parents=True, exist_ok=True)
log.add(pathlib.Path(CFG["paths"]["logs"]) / "worker.log", rotation="20 MB", retention=10)

def parse_affinity(s: str):
    a, b = s.split("-")
    return list(range(int(a), int(b) + 1))
```

**7.4 Create `app/resource_guard.py`.** This module keeps the system below 100% utilisation:
```python
import time, psutil, pynvml
from .config import log

pynvml.nvmlInit()
_GPU = pynvml.nvmlDeviceGetHandleByIndex(0)

def snapshot() -> dict:
    mem = pynvml.nvmlDeviceGetMemoryInfo(_GPU)
    return {
        "gpu_util": pynvml.nvmlDeviceGetUtilizationRates(_GPU).gpu,
        "vram_used_gb": round(mem.used / 1024**3, 2),
        "vram_total_gb": round(mem.total / 1024**3, 2),
        "gpu_temp_c": pynvml.nvmlDeviceGetTemperature(_GPU, pynvml.NVML_TEMPERATURE_GPU),
        "gpu_power_w": round(pynvml.nvmlDeviceGetPowerUsage(_GPU) / 1000, 1),
        "cpu_pct": psutil.cpu_percent(interval=1),
        "ram_pct": psutil.virtual_memory().percent,
    }

def wait_for_headroom(limits: dict):
    """Block until temperature, CPU and RAM are under their caps."""
    while True:
        s = snapshot()
        if (s["gpu_temp_c"] < limits["gpu_max_temp_c"]
                and s["cpu_pct"] < limits["cpu_max_pct"]
                and s["ram_pct"] < limits["ram_max_pct"]):
            return s
        log.warning(f"Resource guard: pausing 15 s {s}")
        time.sleep(15)

def tame_process(pid: int, affinity: list[int] | None = None):
    """Lower priority and pin a child process to selected cores."""
    p = psutil.Process(pid)
    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    if affinity:
        p.cpu_affinity(affinity)
```

**7.5 Create `app/ollama_client.py`.** This handles the director and the vision QA:
```python
import base64, json, httpx
from .config import CFG

URL = CFG["services"]["ollama"]
MODEL = CFG["models"]["director"]

def chat(messages, schema=None, keep_alive="10m", temperature=0.4) -> str:
    payload = {"model": MODEL, "messages": messages, "stream": False, "think": False,
               "keep_alive": keep_alive,
               "options": {"temperature": temperature, "num_ctx": 16384}}
    if schema:
        payload["format"] = schema            # structured JSON output
    r = httpx.post(f"{URL}/api/chat", json=payload, timeout=900)
    r.raise_for_status()
    return r.json()["message"]["content"]

def unload():
    httpx.post(f"{URL}/api/generate", json={"model": MODEL, "keep_alive": 0}, timeout=60)

SCENE_SCHEMA = {
  "type": "object",
  "properties": {"scenes": {"type": "array", "items": {
      "type": "object",
      "properties": {
        "id": {"type": "integer"},
        "start": {"type": "number"}, "end": {"type": "number"},
        "narration": {"type": "string"},
        "visual_prompt": {"type": "string"},
        "motion": {"type": "string", "enum": ["ken_burns_in", "ken_burns_out", "pan",
                    "parallax", "ai_motion", "screenshot_pan", "kinetic_text", "static"]},
        "motion_prompt": {"type": "string"},
        "on_screen_text": {"type": "string"},
        "asset_ref": {"type": "string"},
        "sfx": {"type": "array", "items": {"type": "object",
                "properties": {"file": {"type": "string"}, "at": {"type": "number"}},
                "required": ["file", "at"]}}
      },
      "required": ["id", "start", "end", "narration", "visual_prompt", "motion"]}}},
  "required": ["scenes"]
}

QA_SCHEMA = {"type": "object", "properties": {
    "score": {"type": "integer"}, "matches_prompt": {"type": "boolean"},
    "defects": {"type": "array", "items": {"type": "string"}}},
    "required": ["score", "matches_prompt", "defects"]}

def plan_scenes(template, transcript, script, directions, assets) -> list[dict]:
    sentences = "\n".join(f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}"
                          for s in transcript["segments"])
    system = (
      "You are a video director. Split the narration into scenes that exactly cover "
      f"0 to {transcript['duration']:.2f} seconds with no gaps. Scene length: "
      f"{template['defaults']['scene_seconds']} seconds. Write rich, concrete visual prompts "
      f"in this style: {template['defaults']['image_style']}. "
      f"Allowed motion types for this video type: {template['defaults']['allowed_motion']}. "
      "Use asset_ref when a user asset fits the scene. Follow the user's motion directions exactly. "
      "Never put long sentences inside images.")
    user = (f"VIDEO TYPE: {template['label']}\nSCRIPT:\n{script}\n\nTIMED NARRATION:\n{sentences}\n\n"
            f"USER ASSETS: {json.dumps(assets)}\nMOTION DIRECTIONS:\n{directions or 'none'}")
    out = chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
               schema=SCENE_SCHEMA)
    return json.loads(out)["scenes"]

def qa_image(path, prompt) -> dict:
    img = base64.b64encode(open(path, "rb").read()).decode()
    msg = {"role": "user", "images": [img], "content":
           "Rate this image 1-10 for quality and match to the prompt. List visible defects "
           "(extra limbs, warped hands, garbled text, artifacts, wrong subject).\n"
           f"PROMPT: {prompt}"}
    return json.loads(chat([msg], schema=QA_SCHEMA, temperature=0.1))
```

**7.6 Create `app/comfy_client.py`:**
```python
import json, time, uuid, pathlib, httpx
from .config import CFG

class Comfy:
    def __init__(self):
        self.base = CFG["services"]["comfyui"]
        self.wf_dir = pathlib.Path(CFG["paths"]["workflows"])
        self.cid = str(uuid.uuid4())

    def load(self, name):
        return json.loads((self.wf_dir / f"{name}.json").read_text(encoding="utf-8"))

    @staticmethod
    def set(wf, title, key, value):
        for node in wf.values():
            if node.get("_meta", {}).get("title") == title:
                node["inputs"][key] = value
                return
        raise KeyError(f"Node titled {title} not found in workflow")

    def upload(self, path):
        p = pathlib.Path(path)
        with open(p, "rb") as f:
            r = httpx.post(f"{self.base}/upload/image",
                           files={"image": (p.name, f)}, data={"overwrite": "true"}, timeout=120)
        r.raise_for_status()
        return r.json()["name"]

    def run(self, wf, timeout=3600):
        r = httpx.post(f"{self.base}/prompt", json={"prompt": wf, "client_id": self.cid}, timeout=60)
        r.raise_for_status()
        pid = r.json()["prompt_id"]
        t0 = time.time()
        while time.time() - t0 < timeout:
            h = httpx.get(f"{self.base}/history/{pid}", timeout=30).json()
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI error: {st}")
                if st.get("completed"):
                    return h[pid]["outputs"]
            time.sleep(2)
        raise TimeoutError("ComfyUI job timed out")

    def download(self, outputs, dest: pathlib.Path, rename: str | None = None):
        dest.mkdir(parents=True, exist_ok=True)
        files = []
        for out in outputs.values():
            for kind in ("images", "gifs", "videos", "audio"):
                for it in out.get(kind, []):
                    data = httpx.get(f"{self.base}/view", params={
                        "filename": it["filename"], "subfolder": it.get("subfolder", ""),
                        "type": it.get("type", "output")}, timeout=300).content
                    name = (rename + pathlib.Path(it["filename"]).suffix) if rename else it["filename"]
                    (dest / name).write_bytes(data)
                    files.append(dest / name)
        return files

    def free(self):
        httpx.post(f"{self.base}/free", json={"unload_models": True, "free_memory": True}, timeout=60)
```

**7.7 Create `app/media.py`.** This covers transcription and FFmpeg:
```python
import subprocess, pathlib
from faster_whisper import WhisperModel
from .config import CFG

_whisper = None
ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080),
           "4:5": (1080, 1350), "4:3": (1440, 1080)}
GEN_SIZES = {"16:9": (1344, 768), "9:16": (768, 1344), "1:1": (1024, 1024),
             "4:5": (896, 1120), "4:3": (1152, 864)}

def normalize_audio(src, dst):
    subprocess.run(["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "48000",
                    "-c:a", "pcm_s16le", str(dst)], check=True, capture_output=True)

def transcribe(audio, script, language=None) -> dict:
    global _whisper
    if _whisper is None:   # CPU int8: fast on 16 cores and keeps the GPU free
        _whisper = WhisperModel(CFG["models"]["whisper"], device="cpu",
                                compute_type="int8", cpu_threads=CFG["limits"]["whisper_threads"])
    segs, info = _whisper.transcribe(str(audio), word_timestamps=True, vad_filter=True,
                                     initial_prompt=script[:800], language=language)
    segments, words = [], []
    for s in segs:
        segments.append({"start": s.start, "end": s.end, "text": s.text.strip()})
        words += [{"w": w.word.strip(), "start": w.start, "end": w.end} for w in (s.words or [])]
    return {"duration": info.duration, "segments": segments, "words": words}

def reframe_filter(aspect, method="blur"):
    W, H = ASPECTS[aspect]
    if method == "crop":
        return f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v]"
    return (f"[0:v]split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},boxblur=20:5[bg];[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]")

def audio_graph(has_music, sfx, music_vol=0.22):
    g = ["[1:a]aresample=48000,asplit=2[vo1][vo2]"]
    mix = ["[vo2]"]
    if has_music:
        g.append(f"[2:a]aresample=48000,volume={music_vol}[m]")
        g.append("[m][vo1]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=400[duck]")
        mix.append("[duck]")
    else:
        g.append("[vo1]anullsink")
    base = 3 if has_music else 2
    for i, s in enumerate(sfx):
        ms = int(s["at"] * 1000)
        g.append(f"[{base+i}:a]aresample=48000,adelay=delays={ms}:all=1,volume={s.get('vol', 0.8)}[s{i}]")
        mix.append(f"[s{i}]")
    g.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,"
             f"loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    return ";".join(g)

def export(video, vo, music, sfx, out, aspect, render_aspect, with_sound=True,
           reframe="blur", cq=19, codec="h264_nvenc"):
    cmd = ["ffmpeg", "-y", "-i", str(video)]
    if with_sound:
        cmd += ["-i", str(vo)]
        if music:
            cmd += ["-i", str(music)]
        for s in sfx:
            cmd += ["-i", str(s["path"])]
    graph, vmap = [], "0:v"
    if aspect != render_aspect:
        graph.append(reframe_filter(aspect, reframe))
        vmap = "[v]"
    if with_sound:
        graph.append(audio_graph(bool(music), sfx))
    if graph:
        cmd += ["-filter_complex", ";".join(graph)]
    cmd += ["-map", vmap]
    cmd += (["-map", "[a]", "-c:a", "aac", "-b:a", "192k"] if with_sound else ["-an"])
    cmd += ["-c:v", codec, "-preset", "p5", "-cq", str(cq), "-pix_fmt", "yuv420p",
            "-threads", str(CFG["limits"]["ffmpeg_threads"]), "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out
```

**7.8 Create `app/db.py`.** This is a SQLite job store that both the API and the worker use:
```python
import sqlite3, json, time, threading
from .config import CFG

DB_PATH = f"{CFG['paths']['jobs']}/vidforge.db"
_lock = threading.Lock()

class DB:
    def __init__(self):
        self.c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA journal_mode=WAL")
        self.c.execute("""CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY, status TEXT, priority INTEGER DEFAULT 0, created REAL,
            locked_by TEXT, paused INTEGER DEFAULT 0, retries INTEGER DEFAULT 0,
            data TEXT, error TEXT)""")
        self.c.execute("""CREATE TABLE IF NOT EXISTS refines(
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, scene_id INTEGER,
            mode TEXT, prompt TEXT, status TEXT DEFAULT 'PENDING', created REAL)""")
        self.c.commit()

    def add(self, job_id, data, priority=0):
        with _lock, self.c:
            self.c.execute("INSERT INTO jobs(id,status,priority,created,data) VALUES(?,?,?,?,?)",
                           (job_id, "QUEUED", priority, time.time(), json.dumps(data)))

    def get(self, job_id):
        r = self.c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return {**dict(r), "data": json.loads(r["data"])} if r else None

    def claim(self, statuses, lane):
        with _lock, self.c:
            q = ",".join("?" * len(statuses))
            r = self.c.execute(f"SELECT id FROM jobs WHERE status IN ({q}) AND locked_by IS NULL "
                               "AND paused=0 ORDER BY priority DESC, created ASC LIMIT 1",
                               statuses).fetchone()
            if not r:
                return None
            self.c.execute("UPDATE jobs SET locked_by=? WHERE id=?", (lane, r["id"]))
        return self.get(r["id"])

    def advance(self, job_id, status, data=None):
        with _lock, self.c:
            if data is not None:
                self.c.execute("UPDATE jobs SET data=? WHERE id=?", (json.dumps(data), job_id))
            self.c.execute("UPDATE jobs SET status=?, locked_by=NULL, retries=0 WHERE id=?",
                           (status, job_id))

    def fail(self, job_id, err, max_retries=2):
        with _lock, self.c:
            r = self.c.execute("SELECT retries FROM jobs WHERE id=?", (job_id,)).fetchone()
            if r["retries"] < max_retries:
                self.c.execute("UPDATE jobs SET retries=retries+1, locked_by=NULL, error=? WHERE id=?",
                               (err, job_id))
            else:
                self.c.execute("UPDATE jobs SET status='FAILED', locked_by=NULL, error=? WHERE id=?",
                               (err, job_id))

    def pending_refines(self):
        return [dict(r) for r in self.c.execute(
            "SELECT * FROM refines WHERE status='PENDING' ORDER BY created").fetchall()]

    def finish_refine(self, rid, status="DONE"):
        with _lock, self.c:
            self.c.execute("UPDATE refines SET status=? WHERE id=?", (status, rid))
```

**7.9 Create `app/stages.py`.** These are the core pipeline steps:
```python
import json, random, shutil, pathlib, subprocess, yaml
from .config import CFG, log, parse_affinity
from . import ollama_client as llm, media
from .comfy_client import Comfy
from .resource_guard import tame_process

JOBS = pathlib.Path(CFG["paths"]["jobs"])
comfy = Comfy()

def jdir(job):
    return JOBS / job["id"]

def template(job):
    p = pathlib.Path(CFG["paths"]["templates"]) / f"{job['data']['video_type']}.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def ingest(job, db):
    d = jdir(job)
    for sub in ("input", "scenes", "audio", "render", "public"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    media.normalize_audio(job["data"]["voiceover_path"], d / "input" / "vo.wav")
    return "INGESTED", job["data"]

def transcribe(job, db):
    t = media.transcribe(jdir(job) / "input" / "vo.wav", job["data"]["script"],
                         job["data"].get("language"))
    (jdir(job) / "transcript.json").write_text(json.dumps(t, indent=2), encoding="utf-8")
    return "TRANSCRIBED", job["data"]

def plan(job, db):
    t = json.loads((jdir(job) / "transcript.json").read_text(encoding="utf-8"))
    tpl = template(job)
    scenes = llm.plan_scenes(tpl, t, job["data"]["script"],
                             job["data"].get("motion_directions"), job["data"].get("assets", {}))
    llm.unload()                                         # release VRAM before image generation
    for i, s in enumerate(scenes):                       # enforce contiguous coverage of the audio
        s["start"] = 0.0 if i == 0 else scenes[i - 1]["end"]
        s["seed"] = random.randint(1, 2**31)
        s["status"] = "PENDING"
    scenes[-1]["end"] = t["duration"]
    (jdir(job) / "plan.json").write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    return "PLANNED", job["data"]

def gen_one(job, scene, tpl, extra=""):
    w, h = media.GEN_SIZES[job["data"]["aspect"]]
    wf = comfy.load(tpl["defaults"]["image_workflow"])
    prompt = f"{scene['visual_prompt']}, {tpl['defaults']['image_style']}"
    if job["data"].get("character_bible"):
        prompt = f"{job['data']['character_bible']}. {prompt}"
    if extra:
        prompt = f"{prompt}. {extra}"
    Comfy.set(wf, "VF_PROMPT", "text", prompt)
    Comfy.set(wf, "VF_LATENT", "width", w)
    Comfy.set(wf, "VF_LATENT", "height", h)
    Comfy.set(wf, "VF_SAMPLER", "seed", scene["seed"])
    out = comfy.run(wf)
    comfy.download(out, jdir(job) / "scenes", rename=f"s{scene['id']:02d}")

def generate_images(job, db):
    tpl = template(job)
    scenes = json.loads((jdir(job) / "plan.json").read_text(encoding="utf-8"))
    for s in scenes:
        if s.get("asset_ref") and s["motion"] == "screenshot_pan":
            continue                                     # the user's screenshot is used directly
        gen_one(job, s, tpl)
    comfy.free()
    return "IMAGES_DONE", job["data"]

def qa_images(job, db):
    tpl = template(job)
    p = jdir(job) / "plan.json"
    scenes = json.loads(p.read_text(encoding="utf-8"))
    for s in scenes:
        img = jdir(job) / "scenes" / f"s{s['id']:02d}.png"
        if img.exists():
            s["qa"] = llm.qa_image(img, s["visual_prompt"])
    llm.unload()
    if CFG["pipeline"]["mode"] == "autopilot":
        retry = [s for s in scenes if s.get("qa") and s["qa"]["score"] < CFG["pipeline"]["qa_min_score"]]
        for s in retry[:6]:                              # bounded regeneration: one retry per failed image
            s["seed"] = random.randint(1, 2**31)
            gen_one(job, s, tpl, extra="high quality, anatomically correct, clean composition")
        comfy.free()
        for s in scenes:
            s["status"] = "APPROVED"
        p.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
        return "APPROVED", job["data"]
    p.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    return "AWAITING_REVIEW", job["data"]               # the UI changes this to APPROVED

def refine(db, r):
    """Handles a UI 'Refine' click: regenerate with a new prompt, or edit the existing image."""
    job = db.get(r["job_id"])
    tpl = template(job)
    p = jdir(job) / "plan.json"
    scenes = json.loads(p.read_text(encoding="utf-8"))
    s = next(x for x in scenes if x["id"] == r["scene_id"])
    img = jdir(job) / "scenes" / f"s{s['id']:02d}.png"
    if r["mode"] == "regenerate":
        s["visual_prompt"] = r["prompt"]
        s["seed"] = random.randint(1, 2**31)
        gen_one(job, s, tpl)
    else:                                                # edit with Qwen-Image-Edit
        wf = comfy.load("edit_qwen")
        Comfy.set(wf, "VF_LOAD_IMAGE", "image", comfy.upload(img))
        Comfy.set(wf, "VF_PROMPT", "prompt", r["prompt"])  # the input name varies by node; check your export
        Comfy.set(wf, "VF_SAMPLER", "seed", random.randint(1, 2**31))
        comfy.download(comfy.run(wf), jdir(job) / "scenes", rename=f"s{s['id']:02d}")
    s["status"] = "PENDING"
    s["version"] = s.get("version", 1) + 1
    p.write_text(json.dumps(scenes, indent=2), encoding="utf-8")

def motion(job, db):
    scenes = json.loads((jdir(job) / "plan.json").read_text(encoding="utf-8"))
    budget = CFG["pipeline"]["max_ai_motion_clips"]
    aspect = job["data"]["aspect"]
    for s in scenes:
        if s["motion"] != "ai_motion" or budget <= 0 or aspect not in ("16:9", "9:16"):
            continue
        w, h = (1280, 704) if aspect == "16:9" else (704, 1280)
        wf = comfy.load("i2v_wan5b")
        Comfy.set(wf, "VF_LOAD_IMAGE", "image",
                  comfy.upload(jdir(job) / "scenes" / f"s{s['id']:02d}.png"))
        Comfy.set(wf, "VF_PROMPT", "text", s.get("motion_prompt") or "subtle cinematic camera motion")
        Comfy.set(wf, "VF_LATENT", "width", w)
        Comfy.set(wf, "VF_LATENT", "height", h)
        Comfy.set(wf, "VF_LATENT", "length", 121)
        comfy.download(comfy.run(wf), jdir(job) / "scenes", rename=f"s{s['id']:02d}")
        budget -= 1
    comfy.free()
    return "MOTION_DONE", job["data"]

def music(job, db):
    d = jdir(job)
    choice = job["data"].get("music", "auto_generate")
    if choice == "upload":
        shutil.copy(job["data"]["music_path"], d / "audio" / "music.wav")
    elif choice == "auto_generate":
        t = json.loads((d / "transcript.json").read_text(encoding="utf-8"))
        wf = comfy.load("music_acestep")
        Comfy.set(wf, "VF_PROMPT", "tags", template(job)["defaults"]["music_mood"])
        Comfy.set(wf, "VF_DURATION", "seconds", int(t["duration"]) + 2)  # input name may differ; check your export
        comfy.download(comfy.run(wf), d / "audio", rename="music")
        comfy.free()
    return "AUDIO_READY", job["data"]

def render(job, db):
    d = jdir(job)
    fps = CFG["pipeline"]["default_fps"]
    W, H = media.ASPECTS[job["data"]["aspect"]]
    t = json.loads((d / "transcript.json").read_text(encoding="utf-8"))
    scenes = json.loads((d / "plan.json").read_text(encoding="utf-8"))
    pub = d / "public"
    shutil.copytree(d / "scenes", pub / "scenes", dirs_exist_ok=True)
    items = []
    for s in scenes:
        vid = d / "scenes" / f"s{s['id']:02d}.mp4"
        src = f"scenes/s{s['id']:02d}.mp4" if vid.exists() else f"scenes/s{s['id']:02d}.png"
        if s.get("asset_ref"):
            shutil.copy(s["asset_ref"], pub / "scenes" / pathlib.Path(s["asset_ref"]).name)
            src = f"scenes/{pathlib.Path(s['asset_ref']).name}"
        items.append({"src": src, "kind": "video" if src.endswith(".mp4") else "image",
                      "from": round(s["start"] * fps),
                      "durationInFrames": max(1, round((s["end"] - s["start"]) * fps)),
                      "motion": s["motion"], "text": s.get("on_screen_text", "")})
    props = {"width": W, "height": H, "fps": fps,
             "durationInFrames": round(t["duration"] * fps),
             "scenes": items,
             "words": [{"w": w["w"], "startFrame": round(w["start"] * fps),
                        "endFrame": round(w["end"] * fps)} for w in t["words"]],
             "captionStyle": job["data"].get("captions", template(job)["defaults"]["captions"]),
             "brand": job["data"].get("brand", {"primary": "#FFD400", "font": "Inter"})}
    (d / "props.json").write_text(json.dumps(props), encoding="utf-8")
    proc = subprocess.Popen(
        ["npx.cmd", "remotion", "render", "src/index.ts", "Main", str(d / "render" / "video.mp4"),
         f"--props={d / 'props.json'}", f"--public-dir={pub}", "--muted",
         f"--concurrency={CFG['limits']['render_concurrency']}"],
        cwd=CFG["paths"]["renderer"])
    tame_process(proc.pid, parse_affinity(CFG["limits"]["render_affinity"]))
    if proc.wait() != 0:
        raise RuntimeError("Remotion render failed")
    return "RENDERED", job["data"]

def export(job, db):
    d = jdir(job)
    opts = job["data"].get("export", {})
    aspect = opts.get("aspect", job["data"]["aspect"])
    music_file = next((d / "audio").glob("music.*"), None)
    sfx = job["data"].get("sfx_cues", [])
    out = pathlib.Path(CFG["paths"]["output"]) / f"{job['id']}_{aspect.replace(':', 'x')}.mp4"
    media.export(d / "render" / "video.mp4", d / "input" / "vo.wav", music_file, sfx, out,
                 aspect, job["data"]["aspect"], opts.get("with_sound", True),
                 opts.get("reframe", "blur"), opts.get("cq", 19))
    log.info(f"Exported {out}")
    return "DONE", job["data"]
```

**7.10 Create `app/worker.py`.** This is the 24/7 orchestrator with its two lanes and the inbox watcher:
```python
import threading, time, traceback, pathlib, shutil, uuid, yaml
from .config import CFG, log
from .db import DB
from . import stages
from .resource_guard import wait_for_headroom

GPU_LANE = {"QUEUED": stages.ingest, "INGESTED": stages.transcribe, "TRANSCRIBED": stages.plan,
            "PLANNED": stages.generate_images, "IMAGES_DONE": stages.qa_images,
            "APPROVED": stages.motion, "MOTION_DONE": stages.music}
RENDER_LANE = {"AUDIO_READY": stages.render, "RENDERED": stages.export}

def lane(name, table, db):
    while True:
        if name == "gpu":
            for r in db.pending_refines():               # interactive refines jump the queue
                try:
                    stages.refine(db, r)
                    db.finish_refine(r["id"])
                except Exception:
                    log.exception("refine failed")
                    db.finish_refine(r["id"], "FAILED")
        job = db.claim(list(table), name)
        if not job:
            time.sleep(5)
            continue
        wait_for_headroom(CFG["limits"])
        st = job["status"]
        log.info(f"[{name}] {job['id']} {st}")
        try:
            new_status, data = table[st](job, db)
            db.advance(job["id"], new_status, data)
            if new_status == "DONE":
                time.sleep(CFG["limits"]["cooldown_between_jobs_s"])
        except Exception:
            log.error(traceback.format_exc())
            db.fail(job["id"], traceback.format_exc(), CFG["pipeline"]["max_auto_retries"])

def inbox_watcher(db):
    inbox = pathlib.Path(CFG["paths"]["inbox"])
    while True:
        for folder in inbox.iterdir():
            if not (folder / "READY").exists():
                continue                                 # wait until the upload is complete
            jid = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
            dest = pathlib.Path(CFG["paths"]["jobs"]) / jid
            shutil.move(str(folder), dest)
            meta = yaml.safe_load((dest / "job.yaml").read_text()) if (dest / "job.yaml").exists() else {}
            vo = next(dest.glob("voiceover.*"))
            data = {"video_type": meta.get("video_type", "faceless_reel"),
                    "aspect": meta.get("aspect", "9:16"),
                    "script": (dest / "script.txt").read_text(encoding="utf-8"),
                    "voiceover_path": str(vo), **meta}
            db.add(jid, data, meta.get("priority", 0))
            log.info(f"Inbox job queued: {jid}")
        time.sleep(10)

if __name__ == "__main__":
    db = DB()
    threading.Thread(target=lane, args=("gpu", GPU_LANE, db), daemon=True).start()
    threading.Thread(target=lane, args=("render", RENDER_LANE, db), daemon=True).start()
    threading.Thread(target=inbox_watcher, args=(db,), daemon=True).start()
    log.info("VidForge worker running")
    while True:
        time.sleep(60)
```

**7.11 Create `app/api.py`.** This minimal API is enough for the UI and for testing:
```python
import json, pathlib, shutil, time, uuid, yaml
from fastapi import FastAPI, UploadFile, Form, File
from fastapi.staticfiles import StaticFiles
from .config import CFG
from .db import DB
from .resource_guard import snapshot

app = FastAPI(title="VidForge")
db = DB()
JOBS = pathlib.Path(CFG["paths"]["jobs"])
TPL = pathlib.Path(CFG["paths"]["templates"])

@app.get("/api/templates")
def templates():
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in TPL.glob("*.yaml")]

@app.post("/api/jobs")
async def create_job(video_type: str = Form(...), script: str = Form(...),
                     voiceover: UploadFile = File(...), options: str = Form("{}"),
                     assets: list[UploadFile] = File(default=[])):
    jid = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
    d = JOBS / jid / "input"
    d.mkdir(parents=True)
    vo = d / f"voiceover{pathlib.Path(voiceover.filename).suffix}"
    vo.write_bytes(await voiceover.read())
    saved = {}
    for a in assets:
        p = d / a.filename
        p.write_bytes(await a.read())
        saved[a.filename] = str(p)
    opts = json.loads(options)
    tpl = yaml.safe_load((TPL / f"{video_type}.yaml").read_text(encoding="utf-8"))
    data = {"video_type": video_type, "script": script, "voiceover_path": str(vo),
            "aspect": opts.pop("aspect", tpl["defaults"]["aspect"]), "assets": saved, **opts}
    db.add(jid, data, opts.get("priority", 0))
    return {"id": jid}

@app.get("/api/jobs")
def list_jobs():
    return [dict(r) for r in db.c.execute(
        "SELECT id,status,priority,created,error FROM jobs ORDER BY created DESC LIMIT 200")]

@app.get("/api/jobs/{jid}/scenes")
def scenes(jid: str):
    p = JOBS / jid / "plan.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []

@app.post("/api/jobs/{jid}/scenes/{sid}/refine")
def refine(jid: str, sid: int, mode: str = Form("edit"), prompt: str = Form(...)):
    with db.c:
        db.c.execute("INSERT INTO refines(job_id,scene_id,mode,prompt,created) VALUES(?,?,?,?,?)",
                     (jid, sid, mode, prompt, time.time()))
    return {"queued": True}

@app.post("/api/jobs/{jid}/approve")
def approve(jid: str):
    db.advance(jid, "APPROVED")
    return {"ok": True}

@app.post("/api/jobs/{jid}/export")
def set_export(jid: str, aspect: str = Form(...), with_sound: bool = Form(True),
               reframe: str = Form("blur")):
    job = db.get(jid)
    job["data"]["export"] = {"aspect": aspect, "with_sound": with_sound, "reframe": reframe}
    db.advance(jid, "RENDERED" if job["status"] == "DONE" else job["status"], job["data"])
    return {"ok": True}

@app.get("/api/system")
def system():
    return snapshot()

app.mount("/jobs", StaticFiles(directory=str(JOBS)), name="jobs")   # serves image previews
ui = pathlib.Path(__file__).resolve().parents[2] / "ui" / "dist"
if ui.exists():
    app.mount("/", StaticFiles(directory=str(ui), html=True), name="ui")
```

**7.12 Create the video-type templates.** Save one YAML file per video type in `backend/templates/`. Here is `saas_promo.yaml`:
```yaml
id: saas_promo
label: SaaS Promotional Video
defaults:
  aspect: "16:9"
  scene_seconds: "3-5"
  image_workflow: t2i_qwenimage
  image_style: "clean modern SaaS marketing visual, soft gradients, glassmorphism UI cards, studio lighting, crisp, high detail"
  allowed_motion: [screenshot_pan, kinetic_text, parallax, ai_motion, ken_burns_in]
  music_mood: "upbeat corporate electronic, 110 bpm, optimistic"
  captions: kinetic
fields:
  - {key: script, label: Script, type: textarea, required: true}
  - {key: voiceover, label: Voice-over, type: audio, required: true}
  - {key: product_name, label: Product name, type: text}
  - {key: screenshots, label: Product screenshots, type: images, multiple: true}
  - {key: device_mockup, label: Device frame, type: select, options: [browser, laptop, phone, none], default: browser, showIf: "screenshots"}
  - {key: logo, label: Logo, type: image}
  - {key: brand_colors, label: Brand colors, type: colors}
  - {key: cta_text, label: CTA text, type: text, default: "Start your free trial"}
  - {key: cta_url, label: CTA URL, type: text}
  - {key: sfx, label: Sound effects, type: audio, multiple: true}
  - {key: motion_directions, label: Motion directions, type: textarea}
  - {key: music, label: Music, type: select, options: [auto_generate, upload, none], default: auto_generate}
  - {key: music_file, label: Music file, type: audio, showIf: "music == 'upload'"}
  - {key: aspect, label: Aspect ratio, type: select, options: ["16:9", "9:16", "1:1", "4:5", "4:3"]}
```
Create the remaining templates the same way, with different defaults and fields:

| File | Key defaults | Extra fields |
|------|--------------|--------------|
| `motion_graphics.yaml` | `t2i_zimage`, flat/3D abstract style, `kinetic_text` + `parallax`, scene length 2–3 s | brand colors, font, shape style |
| `branding.yaml` | `t2i_zimage`, premium cinematic style, logo reveal | logo (required), tagline, palette, font |
| `faceless_reel.yaml` | 9:16, `t2i_zimage`, scene length 2–4 s, `ken_burns_*` + `ai_motion`, bold captions | hook text, caption color, niche style |
| `storytelling.yaml` | `t2i_zimage`, cinematic illustration style, scene length 4–7 s | `character_bible`, art style, mood |
| `personal_branding.yaml` | 9:16, `edit_qwen` with your photos | your photos, name, title, social handle |
| `portfolio.yaml` | 16:9, your images first, `screenshot_pan` | project images, project titles, client logos |

✅ **Check:** run `uv run python -c "import app.stages; print('ok')"`. It should print `ok`.

### Step 8 — Build the Remotion renderer (about 30 minutes)

1. Create the project:
   ```powershell
   cd C:\AI\vidforge
   npx create-video@latest renderer      # choose the "Blank" template with TypeScript
   cd renderer
   npm i @remotion/transitions @remotion/google-fonts zod
   ```
2. Replace `src/Root.tsx` with:
   ```tsx
   import {Composition} from 'remotion';
   import {Main, MainProps} from './Main';

   const defaults: MainProps = {width: 1920, height: 1080, fps: 30, durationInFrames: 300,
     scenes: [], words: [], captionStyle: 'kinetic', brand: {primary: '#FFD400', font: 'Inter'}};

   export const RemotionRoot: React.FC = () => (
     <Composition id="Main" component={Main} defaultProps={defaults}
       durationInFrames={300} fps={30} width={1920} height={1080}
       calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames,
         width: props.width, height: props.height, fps: props.fps})}/>
   );
   ```
3. Create `src/Main.tsx`:
   ```tsx
   import {AbsoluteFill, Img, OffthreadVideo, Sequence, interpolate, staticFile,
           useCurrentFrame, useVideoConfig} from 'remotion';

   type Scene = {src: string; kind: 'image' | 'video'; from: number;
                 durationInFrames: number; motion: string; text?: string};
   type Word = {w: string; startFrame: number; endFrame: number};
   export type MainProps = {width: number; height: number; fps: number; durationInFrames: number;
     scenes: Scene[]; words: Word[]; captionStyle: 'none' | 'subtle' | 'kinetic';
     brand: {primary: string; font: string}};

   const Still: React.FC<{s: Scene}> = ({s}) => {
     const f = useCurrentFrame();
     const t = interpolate(f, [0, s.durationInFrames], [0, 1], {extrapolateRight: 'clamp'});
     const out = s.motion === 'ken_burns_out';
     const scale = s.motion === 'static' ? 1 : out ? 1.12 - 0.12 * t : 1 + 0.12 * t;
     const x = s.motion === 'pan' || s.motion === 'screenshot_pan' ? -4 * t : -1.5 * t;
     return (
       <AbsoluteFill style={{overflow: 'hidden'}}>
         <Img src={staticFile(s.src)} style={{width: '100%', height: '100%', objectFit: 'cover',
           transform: `scale(${scale}) translateX(${x}%)`}}/>
       </AbsoluteFill>
     );
   };

   const Captions: React.FC<{words: Word[]; style: string; color: string}> = ({words, style, color}) => {
     const f = useCurrentFrame();
     const {width} = useVideoConfig();
     if (style === 'none') return null;
     const i = words.findIndex((w) => f >= w.startFrame && f < w.endFrame);
     if (i < 0) return null;
     const start = i - (i % 3);
     const group = words.slice(start, start + 3);
     return (
       <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: '14%'}}>
         <div style={{fontSize: width * (style === 'kinetic' ? 0.06 : 0.035), fontWeight: 800,
           textAlign: 'center', color: 'white', textShadow: '0 4px 18px rgba(0,0,0,.65)',
           padding: '0 6%'}}>
           {group.map((w, k) => (
             <span key={k} style={{margin: '0 .18em',
               color: start + k === i ? color : 'white'}}>{w.w}</span>
           ))}
         </div>
       </AbsoluteFill>
     );
   };

   export const Main: React.FC<MainProps> = (p) => (
     <AbsoluteFill style={{backgroundColor: 'black'}}>
       {p.scenes.map((s, i) => (
         <Sequence key={i} from={s.from} durationInFrames={s.durationInFrames}>
           {s.kind === 'video'
             ? <OffthreadVideo src={staticFile(s.src)} muted
                 style={{width: '100%', height: '100%', objectFit: 'cover'}}/>
             : <Still s={s}/>}
         </Sequence>
       ))}
       <Captions words={p.words} style={p.captionStyle} color={p.brand.primary}/>
     </AbsoluteFill>
   );
   ```
4. **Next improvements to add later:** crossfade and slide transitions with `@remotion/transitions` (`TransitionSeries`), device-mockup frames for `screenshot_pan`, kinetic title cards for `on_screen_text`, logo reveal and CTA end-card components per template, and brand fonts through `@remotion/google-fonts`.

✅ **Check:** run `npx remotion studio`. The Main composition opens in your browser without errors.

### Step 9 — Build the UI (about 2–6 hours, or let a coding agent do it from PRD.md)

1. Scaffold the app:
   ```powershell
   cd C:\AI\vidforge
   npm create vite@latest ui -- --template react-ts
   cd ui; npm i; npm i @tanstack/react-query react-hook-form zod wavesurfer.js react-dropzone
   ```
   Then add Tailwind CSS and shadcn/ui by following their current Vite setup guides.
2. Build the screens defined in **PRD.md, Section 14**: Dashboard, New Job, Scene Board, Export, Queue, Settings and Brand Kits.
3. **The key to the dynamic layout is the DynamicForm component.** It fetches `/api/templates`. When you pick a video type, it renders that template's `fields` list, hiding any field whose `showIf` condition is false. Changing the video type swaps the entire form and its defaults.
4. Build for production with `npm run build`. FastAPI automatically serves `ui/dist` at `http://127.0.0.1:8700`.

### Step 10 — Run everything as 24/7 services (about 20 minutes)

1. Run these commands in an **Admin PowerShell**. Replace `YOURUSER` and `YOURPASS` with your Windows login. Running the services under your own account (instead of LocalSystem) avoids GPU and path problems.
   ```powershell
   $L = "D:\VidForge\logs"

   # Ollama (quit the tray app and remove it from Startup first, so the port is free)
   nssm install VF-Ollama "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve
   nssm set VF-Ollama AppEnvironmentExtra OLLAMA_MODELS=C:\AI\ollama-models OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_FLASH_ATTENTION=1 OLLAMA_CONTEXT_LENGTH=16384

   # ComfyUI
   nssm install VF-ComfyUI "C:\AI\ComfyUI_windows_portable\python_embeded\python.exe" "-s ComfyUI\main.py --windows-standalone-build --listen 127.0.0.1 --port 8188 --reserve-vram 1.5 --disable-auto-launch"
   nssm set VF-ComfyUI AppDirectory "C:\AI\ComfyUI_windows_portable"

   # API + UI
   nssm install VF-API "$env:USERPROFILE\.local\bin\uv.exe" "run uvicorn app.api:app --host 127.0.0.1 --port 8700"
   nssm set VF-API AppDirectory "C:\AI\vidforge\backend"

   # Worker
   nssm install VF-Worker "$env:USERPROFILE\.local\bin\uv.exe" "run python -m app.worker"
   nssm set VF-Worker AppDirectory "C:\AI\vidforge\backend"
   nssm set VF-Worker DependOnService VF-Ollama VF-ComfyUI

   foreach ($s in "VF-Ollama","VF-ComfyUI","VF-API","VF-Worker") {
     nssm set $s ObjectName ".\YOURUSER" "YOURPASS"
     nssm set $s AppStdout "$L\$s.log"; nssm set $s AppStderr "$L\$s.err.log"
     nssm set $s AppRotateFiles 1; nssm set $s AppRotateBytes 20000000
     nssm set $s AppRestartDelay 10000
     nssm set $s Start SERVICE_AUTO_START
     nssm start $s
   }
   ```
2. **Check the program paths before running.** Confirm where `uv.exe` and `ollama.exe` live with `where.exe uv` and `where.exe ollama`, and adjust the paths above if they differ.
3. **If GPU access fails under a service** (rare): use Task Scheduler instead, with an "At log on" trigger, Windows auto-login, and "Restart on failure" set.

✅ **Check:** open `services.msc` and confirm all four VF services are Running. Then open `http://127.0.0.1:8700` and the dashboard should load.

---

## 7. Testing the Workflow

### Test 1 — Service smoke test (5 minutes)
```powershell
curl http://127.0.0.1:11434/api/tags          # Ollama lists qwen3.5:9b
curl http://127.0.0.1:8188/system_stats       # ComfyUI shows the RTX 5070 Ti
curl http://127.0.0.1:8700/api/system         # VidForge shows the resource snapshot
curl http://127.0.0.1:8700/api/templates      # all 7 templates load
```

### Test 2 — Prepare a sample job
1. Create `D:\VidForge\test\script.txt` with an 80–120 word script. That's about 30–45 seconds of speech.
2. Record the voice-over on your phone and save it as `voiceover.mp3`. Alternatively, generate a test voice-over with Kokoro TTS.

### Test 3 — Run each stage on its own
Run this from `C:\AI\vidforge\backend` after stopping the VF-Worker service:
```powershell
uv run python -c "from app import media; import json; t=media.transcribe('D:/VidForge/test/voiceover.mp3', open('D:/VidForge/test/script.txt').read()); print(t['duration'], len(t['words']))"
```
Expected result: the duration in seconds, and a word count close to your script's.

Then test ComfyUI on its own by running `t2i_zimage.json` in the ComfyUI UI with the titled nodes. Expect an image in 2–10 seconds.

### Test 4 — End-to-end test through the UI (review mode)
1. Go to **New Job**, choose **Faceless Reel**, paste the script, upload the voice-over, and click **Create**.
2. On the **Queue** page, watch the status move: QUEUED → INGESTED → TRANSCRIBED → PLANNED → IMAGES_DONE → AWAITING_REVIEW.
3. Open the **Scene Board**. Pick one image and click **Refine** with mode **Edit**, using an instruction like "make the sky sunset orange." The image should update within about a minute.
4. Click **Approve all**. The job should go on to MOTION_DONE → AUDIO_READY → RENDERED → DONE.
5. On the **Export** page, set the aspect to 1:1 and "without sound," and re-export. Check `D:\VidForge\output`: you should see two MP4 files, one silent and one with sound.

### Test 5 — Inbox and autopilot test
1. Set `pipeline.mode: autopilot` in `config.yaml`, then restart VF-Worker.
2. Copy the test folder to `D:\VidForge\inbox\test-01\`.
3. Add a `job.yaml` file:
   ```yaml
   video_type: faceless_reel
   aspect: "9:16"
   captions: kinetic
   music: auto_generate
   ```
4. Create an empty file named `READY` in the folder.
5. **Expected result:** the folder disappears from the inbox, the job appears in the queue, and an MP4 arrives in `output` without any clicks from you.

### Test 6 — Resource cap test
While a job runs, open a second PowerShell window and run:
```powershell
nvidia-smi dmon -s pum      # shows power, temperature, utilisation and memory every second
```
**Pass criteria:**
- GPU power stays at or below your limit (about 255 W).
- VRAM stays at or below about 14.5 GB.
- GPU temperature stays under 80 °C.
- In Task Manager, CPU usage averages below 80% during rendering, and logical CPUs 0–3 stay lightly loaded.
- RAM stays below 85%.

### Test 7 — Overnight soak test
Queue 10 or more inbox jobs before bed. In the morning, check:

| Check | Pass criteria |
|-------|---------------|
| Success rate | 9 or more of 10 jobs DONE |
| Pipelining | `worker.log` shows job N+1's images generating while job N renders |
| Memory | RAM usage did not keep climbing across jobs (check the logged snapshots) |
| Disk | Free space is above 100 GB |

### Test 8 — Failure recovery test
Stop VF-ComfyUI in `services.msc` while a job is generating images, then start it again. **Expected result:** the stage fails, the job retries automatically, and it finishes.

---

## 8. Daily User Guide

### 8.1 Creating a video from the UI
1. Open `http://127.0.0.1:8700` and go to **New Job**.
2. **Choose a video type.** The form changes to show only the fields that matter for that type, with sensible defaults already filled in.
3. **Fill in the required inputs:** paste the **script** and upload the **voice-over** (MP3, WAV or M4A).
4. **Add optional inputs** as needed: screenshots, logo, brand colors, SFX, music, motion directions, aspect ratio, caption style and priority.
5. Click **Create Job**. The job joins the queue.

### 8.2 Reviewing and refining images (Scene Board)
Each scene card shows the image, its narration line, the time range, the QA score, any detected defects, and the prompt.

| Button | What it does |
|--------|--------------|
| **Approve** | Locks the scene so it won't change |
| **Refine → Edit** | Keeps the image and applies your instruction, such as "remove the text on the mug" or "change the shirt to blue." Best for small defects. |
| **Refine → Regenerate** | Generates a completely new image from your new prompt with a new seed. Best when the composition itself is wrong. |
| **Replace** | Uploads your own image for this scene |
| **Motion** | Overrides the motion type for this scene, such as `ai_motion` or `ken_burns_out` |
| **Approve all** | Sends the job on to motion, music and rendering |

**Draft preview:** click **Preview draft** for a fast half-resolution render before you approve the final version.

### 8.3 Motion directions syntax
You can write motion directions as free text, and the director model will interpret it. For exact control, use these tags:
```
[00:00-00:03] kinetic_text "Stop wasting hours on reports"
[00:05-00:09] screenshot_pan dashboard.png zoom_to top-right
[scene 4] ai_motion "camera slowly pushes in, light particles drifting"
[00:12] sfx whoosh.wav
[00:20] sfx click.wav vol=0.5
[all] transition slide_left
[end] cta "Start your free trial — app.example.com"
```
Filenames refer to the assets you uploaded with the job.

### 8.4 Export options
| Option | Choices | Notes |
|--------|---------|-------|
| Aspect ratio | 16:9, 9:16, 1:1, 4:5, 4:3 | See the reframe note below if this differs from the generation aspect |
| Reframe method | Regenerate / Smart crop / Blur pad | **Regenerate** gives the best quality but re-runs image generation. **Blur pad** keeps the whole frame on a blurred background. |
| Sound | With sound / Without sound | "Without sound" exports silent video (for adding music on social platforms) |
| Resolution | 1080p / 4K | 4K upscales the images before rendering |
| Frame rate | 24 / 30 / 60 | 60 fps uses RIFE frame interpolation on AI clips |
| Captions | Burned-in / SRT file / None | |
| Codec | H.264 (most compatible) / HEVC / AV1 | All three use NVENC |

**Important note on aspect ratios:** images are generated at the aspect ratio chosen when the job was created. Pick the right one up front for best quality, and use Export reframing for extra versions.

### 8.5 Running 24/7
**Feeding the queue.** You have two options:
- Submit jobs through the UI.
- Drop folders into `D:\VidForge\inbox\` with this layout:
  ```
  my-video-01\
    script.txt        (required)
    voiceover.mp3     (required)
    job.yaml          (optional settings)
    assets\           (optional: screenshots, sfx, logo, music)
    READY             (empty file — create it last)
  ```

**Choosing a mode:**
- **Review mode:** jobs pause at AWAITING_REVIEW. The worker moves on to other jobs while it waits, so nothing blocks.
- **Autopilot mode:** QA approves images automatically and regenerates low-scoring ones, so jobs run straight through to MP4.

**Controlling the queue:**
- Use **Priority** to push urgent jobs to the front.
- Use **Pause** or **Resume** per job, or for the whole queue, from the Dashboard.

---

## 9. Resource Management and Tuning

| Lever | Where to set it | Default | Effect |
|-------|-----------------|---------|--------|
| GPU power limit | `nvidia-smi -pl` or Afterburner | 255 W (85%) | Lower heat and power; speed drops only about 5–10% |
| VRAM reserve | ComfyUI `--reserve-vram` | 1.5 GB | VRAM never reaches 100% |
| One model at a time | `OLLAMA_MAX_LOADED_MODELS=1` + `/free` calls | on | Prevents out-of-memory crashes |
| Render CPU threads | `render_concurrency` | 8 | Raise to 12 for faster renders; lower it if the PC feels sluggish |
| CPU affinity | `render_affinity` | 4–31 | CPUs 0–3 stay free for Windows and the UI |
| Process priority | `tame_process()` | Below normal | Your desktop stays responsive |
| Guard thresholds | `limits.*` | 80% CPU, 85% RAM, 80 °C GPU | New steps wait when the system is busy or hot |
| AI motion budget | `max_ai_motion_clips` | 3 | The biggest single lever on time per video |
| Cooldown | `cooldown_between_jobs_s` | 30 s | Gives temperatures time to settle |

---

## 10. Maintenance and Troubleshooting

### Weekly maintenance
- Update ComfyUI and the custom nodes through Manager, then re-run Test 4.
- Update Ollama.
- Archive old jobs (move `jobs\*` folders older than 7 days to `archive`, or delete their intermediate files).
- Back up `config.yaml`, `templates\`, `workflows\` and `vidforge.db`.

### Common problems
| Symptom | Fix |
|---------|-----|
| ComfyUI runs out of memory (OOM) | Use a smaller GGUF (Q4 instead of Q5), confirm Ollama unloaded, raise `--reserve-vram`, or use the `--lowvram` flag |
| Jobs become extremely slow after a while | The Sysmem Fallback setting is not applied (Step 1.2), or RAM is full. Check Task Manager. |
| `KeyError: Node titled VF_...` | The workflow JSON is missing a node title. Re-export it with the titles from Step 6. |
| `Comfy.set` errors on edit or music workflows | Input names differ between node versions. Open the exported JSON and use the input name that node actually has. |
| Garbled text inside images | Use the `t2i_qwenimage` workflow for that scene, or keep text short and add it as a Remotion overlay instead |
| Wan rejects the resolution | Use only 1280×704 or 704×1280, with frame counts of the form 4k+1 |
| Captions are out of sync | The script and the voice-over don't match closely. Re-record the VO, or edit `transcript.json`. |
| Remotion render fails | Run `npx remotion studio` with the job's `props.json` to see the error |
| A service keeps restarting | Read `D:\VidForge\logs\VF-*.err.log` |

---

## 11. Licensing Checklist

| Component | License | Commercial use |
|-----------|---------|----------------|
| Qwen3.5-9B | Apache 2.0 | ✅ |
| Z-Image-Turbo | Apache 2.0 | ✅ |
| Qwen-Image-2512 / Qwen-Image-Edit-2511 | Apache 2.0 | ✅ |
| Wan 2.2 TI2V-5B | Apache 2.0 | ✅ |
| LTX-2.x (deferred) | LTX-2 Community License | ✅ if annual revenue is under $10M (install after RAM upgrade) |
| faster-whisper / Whisper weights | MIT | ✅ |
| ACE-Step 1.5 | MIT | ✅ |
| BiRefNet | MIT | ✅ |
| Real-ESRGAN | BSD-3 | ✅ |
| Remotion | Remotion License | ✅ free for individuals and teams of up to 3 people |
| FFmpeg (full build) | GPL/LGPL | ✅ for internal use |
| Community fine-tunes and LoRAs | varies | Check each one before use |
| FLUX.1-dev, FLUX.2-dev, RMBG-2.0 | Non-commercial | ❌ avoid for client work |

These are summaries, not legal advice. Re-check each model's license page before commercial or client use, because terms can change.
`````

---

## File 3 of 3: `PRD.md`

````markdown
# Product Requirements Document
# VidForge — Local AI Video Generation Harness

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Date | 18 October 2026 |
| Status | Draft for build |
| Owner | Product owner / sole operator |
| Platform | Windows 11 workstation (Ryzen 9 9950X, RTX 5070 Ti 16 GB, 32 GB RAM) |
| Related docs | USER_GUIDE.md, HARDWARE.md |

---

## 1. Summary

VidForge is a fully local, open-source AI video production harness. The operator provides a **script** and a **voice-over**, the only two mandatory inputs. The system produces a finished **MP4** for one of seven video types:

- Motion Graphics
- SaaS Promo
- Branding
- Faceless Reel
- Storytelling
- Personal Branding
- Portfolio

The system plans scenes, generates images that match the video type, supports human preview and prompt-based refinement, animates scenes, adds captions, music and SFX, and exports at a selected aspect ratio with or without sound. It runs **24/7 as a queue**, pipelining work so the next video's assets are generated while the current video renders. It also keeps hardware utilisation below defined caps.

## 2. Problem and Opportunity

**Problems today:**
- Producing short-form and promotional videos by hand is slow: storyboarding, image sourcing, animation, captions and audio mixing.
- Paid AI video services charge per generation, limit throughput, and keep data off-premises.
- Open-source models are now capable enough, but running them means juggling separate tools (LLMs, diffusion UIs, editors) with no unified, repeatable workflow.

**The opportunity:** a single controllable pipeline on existing hardware, with zero marginal cost per video, consistent quality through templates, and continuous unattended output.

## 3. Goals and Non-Goals

### 3.1 Goals
- **G1.** Turn a script and voice-over into an MP4 with no other required input.
- **G2.** Make every pipeline aspect controllable through the UI, with optional parameters.
- **G3.** Dynamically adapt the UI layout and image generation to the selected video type.
- **G4.** Provide image preview and per-image refinement by prompt (edit or regenerate).
- **G5.** Use operator assets (screenshots, SFX, logo, music, motion directions) faithfully.
- **G6.** At export, let the operator choose the aspect ratio and with or without sound.
- **G7.** Run 24/7 with automatic queueing and pipelining.
- **G8.** Use only free, local, open-weight models.
- **G9.** Never drive the system to 100% utilisation; enforce resource caps.

### 3.2 Non-Goals (v1)
- Cloud or paid model APIs.
- Multi-user accounts and permissions, or remote public hosting.
- Lip-synced talking-avatar generation (possible in v2).
- Fully automatic script writing and voice generation as the primary path (optional P2 feature).
- A non-linear editor that replaces professional NLE software.

## 4. Users and Personas

| Persona | Description | Key needs |
|---------|-------------|-----------|
| **Operator / Creator** (primary) | A solo creator or freelancer producing promos, reels and brand content | Speed, quality control, minimal clicks, batch output |
| **Reviewer** | The same person in a QA role | Fast visual review, precise fixes |
| **Unattended mode** | The system running overnight | Reliability, auto-recovery, safe resource use |

## 5. Video Types (v1 scope)

| ID | Type | Default aspect | Image engine | Motion | Captions | Distinguishing inputs |
|----|------|---------------|--------------|--------|----------|----------------------|
| VT1 | Motion Graphics | 16:9 | Z-Image | Kinetic text, parallax | Kinetic | Brand colors, font, shape style |
| VT2 | SaaS Promo | 16:9 | Qwen-Image + Qwen-Edit | Screenshot pan in device frames, limited AI motion | Kinetic | Screenshots, device frame, CTA, logo |
| VT3 | Branding | 16:9 / 1:1 | Z-Image + BiRefNet | Logo reveal, parallax | Minimal | Logo (required), tagline, palette |
| VT4 | Faceless Reel | 9:16 | Z-Image | Ken Burns + up to N AI clips | Bold word-by-word | Hook text, caption color |
| VT5 | Storytelling | 16:9 / 9:16 | Z-Image + Qwen-Edit | Slow Ken Burns, AI motion on key beats | Subtle | Character bible, art style, mood |
| VT6 | Personal Branding | 9:16 / 4:5 | Operator photos + Qwen-Edit | Ken Burns, lower-thirds | Bold | Photos, name, title, handle |
| VT7 | Portfolio | 16:9 | Operator images first | Grid reveals, pans | Minimal | Project images, titles, client logos |

## 6. User Stories

| ID | As the operator, I want to… | So that… | Priority |
|----|------------------------------|----------|----------|
| US-01 | Create a job with only a script and voice-over | I can start fast | P0 |
| US-02 | Pick a video type and see a form tailored to it | I only see relevant options | P0 |
| US-03 | Add optional assets (screenshots, SFX, logo, music) | The video uses my real materials | P0 |
| US-04 | Write motion directions | I control camera moves, timing and SFX | P0 |
| US-05 | Preview every generated image before rendering | I catch defects early | P0 |
| US-06 | Fix an image with a new prompt (edit or regenerate) | I don't redo the whole video | P0 |
| US-07 | Replace any scene image with my own upload | I keep full creative control | P1 |
| US-08 | Choose the aspect ratio and with/without sound at export | I get platform-ready files | P0 |
| US-09 | Export multiple aspect versions of one job | One job serves several platforms | P1 |
| US-10 | Drop job folders into an inbox | Batch production runs unattended | P0 |
| US-11 | Run autopilot with automatic QA | Videos finish overnight without me | P0 |
| US-12 | See live resource usage and queue state | I trust the system is safe | P0 |
| US-13 | Set job priority, and pause or resume jobs or the queue | Urgent work goes first | P1 |
| US-14 | Save brand kits (logo, colors, fonts) | Branding stays consistent | P1 |
| US-15 | Preview a low-resolution draft render | I validate timing quickly | P1 |
| US-16 | Create and edit video-type templates in the UI | I can add new formats without code | P2 |
| US-17 | Generate scripts and voice-overs from topics automatically | The queue never runs dry | P2 |

## 7. Functional Requirements

### 7.1 Job Intake
- **FR-1.1 (P0).** The system shall require exactly two inputs per job: script text and a voice-over audio file (MP3, WAV, M4A or FLAC, up to 30 minutes).
- **FR-1.2 (P0).** The system shall accept optional inputs as defined by the selected template's field list.
- **FR-1.3 (P0).** The system shall validate inputs on submission: the audio must decode, the script must not be empty, and asset types must be correct. Errors are shown inline.
- **FR-1.4 (P0).** The system shall accept jobs from an inbox folder containing `script.txt`, `voiceover.*`, an optional `job.yaml`, an optional `assets/` folder, and a `READY` marker file. Folders without a `READY` marker shall be ignored.
- **FR-1.5 (P1).** The system shall accept batch import from a CSV file that references script and voice-over paths.
- **FR-1.6 (P0).** Each job shall receive a unique ID and its own working folder.

### 7.2 Templates and Dynamic UI
- **FR-2.1 (P0).** Each video type shall be defined by a template file (YAML) with: `id`, `label`, `defaults` (aspect, scene length, image workflow, image style, allowed motion types, music mood, caption style), and `fields` (key, label, type, required, default, options, showIf).
- **FR-2.2 (P0).** The New Job form shall render entirely from the selected template. Changing the type shall replace the fields and defaults without a page reload.
- **FR-2.3 (P0).** Fields shall support these types: text, textarea, select, number, toggle, color, colors, image, images, audio, and audio (multiple).
- **FR-2.4 (P0).** `showIf` conditions shall show or hide fields reactively.
- **FR-2.5 (P2).** A template editor in the UI shall support creating, cloning and editing templates, with validation.

### 7.3 Transcription and Alignment
- **FR-3.1 (P0).** The system shall convert the voice-over to 48 kHz mono WAV.
- **FR-3.2 (P0).** The system shall transcribe with faster-whisper (large-v3-turbo, CPU int8), producing segment-level and word-level timestamps.
- **FR-3.3 (P0).** The script shall be used as an initial prompt to improve transcription accuracy.
- **FR-3.4 (P1).** The UI shall show the transcript with timestamps and allow manual correction.
- **FR-3.5 (P1).** The language shall be selectable; the default is automatic detection.

### 7.4 Scene Planning
- **FR-4.1 (P0).** The director LLM (Qwen3.5-9B via Ollama) shall output a JSON scene list that validates against a schema. Each scene has: id, start, end, narration, visual_prompt, motion, motion_prompt, on_screen_text, asset_ref, and sfx cues.
- **FR-4.2 (P0).** Scenes shall cover the full audio duration with no gaps or overlaps. The system shall fix any gaps after planning.
- **FR-4.3 (P0).** Scene lengths and allowed motion types shall follow the template.
- **FR-4.4 (P0).** Tagged motion directions (`[mm:ss-mm:ss]`, `[scene N]`, `[all]`, `[end]`) shall be parsed deterministically and take precedence over the LLM's choices. Free text shall be passed to the LLM.
- **FR-4.5 (P0).** Uploaded assets shall be assigned to scenes when relevant, for example screenshots to `screenshot_pan` scenes.
- **FR-4.6 (P1).** The operator shall be able to edit the plan (prompts, timings, motion types) before image generation, through an optional "plan review" gate.

### 7.5 Image Generation
- **FR-5.1 (P0).** Images shall be generated through the ComfyUI API, using the workflow named in the template.
- **FR-5.2 (P0).** Generation size shall follow the job's aspect ratio (1344×768, 768×1344, 1024×1024, 896×1120, 1152×864).
- **FR-5.3 (P0).** Prompts shall combine the scene's visual prompt, the template's image style, the brand context, and (for storytelling) the character bible.
- **FR-5.4 (P0).** All images for a job shall be generated in one batch before the model is unloaded.
- **FR-5.5 (P1).** Images shall be upscaled to the render resolution (Real-ESRGAN) before composition.
- **FR-5.6 (P1).** Background removal (BiRefNet) shall be applied to logos and portraits when the template requires it.
- **FR-5.7 (P1).** Seeds shall be stored per scene so results are reproducible.

### 7.6 Quality Assurance, Preview and Refinement
- **FR-6.1 (P0).** Every generated image shall be scored from 1 to 10 by the vision model, with a list of detected defects.
- **FR-6.2 (P0).** In **review mode**, the job shall pause at AWAITING_REVIEW. Other jobs shall continue processing.
- **FR-6.3 (P0).** The Scene Board shall show, for each scene: image, narration, time range, QA score, defects, prompt and version history.
- **FR-6.4 (P0).** **Refine → Edit** shall run Qwen-Image-Edit on the current image with the operator's instruction.
- **FR-6.5 (P0).** **Refine → Regenerate** shall run text-to-image with the new prompt and a new seed.
- **FR-6.6 (P0).** Refine requests shall jump ahead of queued background work in the GPU lane, with a target time to result under 90 seconds.
- **FR-6.7 (P0).** Previous image versions shall be kept, and the operator can revert to any of them.
- **FR-6.8 (P1).** The operator shall be able to replace a scene image by upload.
- **FR-6.9 (P0).** In **autopilot mode**, images scoring below the threshold (default 7) shall be regenerated up to N times (default 2), after which the best version is approved automatically.

### 7.7 Motion
- **FR-7.1 (P0).** Supported motion types: ken_burns_in, ken_burns_out, pan, parallax, screenshot_pan, kinetic_text, static, and ai_motion.
- **FR-7.2 (P0).** `ai_motion` shall use Wan 2.2 TI2V-5B (1280×704 or 704×1280, 121 frames), with an optional LTX-2.x engine.
- **FR-7.3 (P0).** AI motion clips per video shall be capped by `max_ai_motion_clips`. Scenes beyond the cap fall back to Ken Burns.
- **FR-7.4 (P1).** AI clips shorter than their scene shall be extended by slow playback or a hold on the final frame. Longer clips shall be trimmed.
- **FR-7.5 (P1).** RIFE frame interpolation shall be available for 60 fps exports.

### 7.8 Audio
- **FR-8.1 (P0).** Music options shall be: auto-generate (ACE-Step 1.5 with the template's mood), upload, or none.
- **FR-8.2 (P0).** Music shall be ducked under the voice-over using sidechain compression.
- **FR-8.3 (P0).** SFX shall be placed at times from motion directions or the plan's SFX cues, with per-cue volume.
- **FR-8.4 (P0).** The final mix shall be loudness-normalised to −14 LUFS integrated, with a −1.5 dBTP true-peak ceiling.
- **FR-8.5 (P1).** Separate audio stems (VO, music, SFX) shall be exportable.

### 7.9 Composition and Captions
- **FR-9.1 (P0).** Composition shall be rendered with Remotion from a generated props file (scenes, words, brand, caption style).
- **FR-9.2 (P0).** Caption styles shall be: none, subtle, and kinetic (word-by-word highlight in the brand color).
- **FR-9.3 (P1).** Transitions (crossfade, slide, zoom) shall be configurable per job or per scene.
- **FR-9.4 (P1).** Template components shall include: device mockup frames, kinetic title cards, logo reveal, lower-thirds, and a CTA end card.
- **FR-9.5 (P1).** A draft preview shall be available at half resolution.

### 7.10 Export
- **FR-10.1 (P0).** The output format shall be MP4 (H.264 by default; HEVC and AV1 optional), encoded with NVENC, `yuv420p`, and `+faststart`.
- **FR-10.2 (P0).** Before export, the operator shall be able to choose an aspect ratio from 16:9, 9:16, 1:1, 4:5 and 4:3.
- **FR-10.3 (P0).** When the export aspect differs from the generation aspect, the reframe method shall be selectable: regenerate, smart crop, or blur pad.
- **FR-10.4 (P0).** The operator shall be able to choose to export with sound or without sound (an audio-free stream).
- **FR-10.5 (P1).** Resolution options shall include 1080p and 4K. Caption options shall include burned-in, an SRT sidecar file, or none.
- **FR-10.6 (P1).** Each export shall also produce a thumbnail (PNG) and a metadata JSON file containing the job settings, models used and seeds.
- **FR-10.7 (P1).** Re-exports shall not re-run generation unless "regenerate" reframing is selected.

### 7.11 Automation (24/7)
- **FR-11.1 (P0).** The worker shall run two lanes: a GPU lane (stages 1–8) and a render lane (render and export), each processing one job at a time.
- **FR-11.2 (P0).** The GPU lane shall start the next job's stages while the render lane processes the previous job.
- **FR-11.3 (P0).** Jobs shall be selected by priority (highest first), then by creation time (oldest first).
- **FR-11.4 (P0).** Failed stages shall retry automatically up to N times before the job is marked FAILED with an error log.
- **FR-11.5 (P0).** All services shall auto-start at boot and auto-restart on crash.
- **FR-11.6 (P0).** Job state shall persist in SQLite, so a restarted worker resumes from the last completed stage.
- **FR-11.7 (P1).** A configurable cooldown shall apply between jobs.
- **FR-11.8 (P1).** A disk guard shall pause intake when free space falls below a threshold (default 50 GB), and an auto-archive feature shall move intermediate files after N days.
- **FR-11.9 (P2).** An autopilot content source shall generate scripts with the LLM and voice-overs with a local TTS model from a topics list.

### 7.12 Resource Management
- **FR-12.1 (P0).** Only one GPU model family shall be resident at a time. The system shall unload Ollama models and free ComfyUI memory between model families.
- **FR-12.2 (P0).** ComfyUI shall run with a VRAM reserve (default 1.5 GB).
- **FR-12.3 (P0).** The Resource Guard shall block the start of new heavy steps while GPU temperature is at or above 80 °C, CPU at or above 80%, or RAM at or above 85%. All thresholds shall be configurable.
- **FR-12.4 (P0).** Render processes shall run at below-normal priority, pinned to configured CPU cores (default: logical cores 4–31).
- **FR-12.5 (P0).** The setup shall apply a GPU power limit (default 85% of the stock limit).
- **FR-12.6 (P1).** Quiet hours shall allow reduced limits on a schedule.

### 7.13 Monitoring and Logging
- **FR-13.1 (P0).** The Dashboard shall show live GPU utilisation, VRAM, temperature, power, CPU, RAM and disk, refreshed at least every 5 seconds.
- **FR-13.2 (P0).** The Queue view shall show each job's status, current stage, elapsed time and ETA.
- **FR-13.3 (P0).** Per-job event logs and service logs shall be rotated at 20 MB.
- **FR-13.4 (P2).** Desktop notifications shall be sent on job done or failed (optionally Telegram or email, via a local script).

### 7.14 Settings
- **FR-14.1 (P0).** The UI shall edit: model names, workflow mapping per template, limits, pipeline mode, QA threshold, retries, AI motion budget and paths.
- **FR-14.2 (P1).** Brand kits shall support create, read, update and delete. Each kit holds a logo, palette, fonts and caption color, and can be attached to a job.

## 8. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-1 | Performance | A 60-second faceless reel with no AI motion completes in 15 minutes or less. Each AI motion clip adds no more than 10 minutes (Wan 5B, 720p). |
| NFR-2 | Performance | Refine edit or regenerate returns in 90 seconds or less when the GPU lane is idle or between steps. |
| NFR-3 | Resource | Peak VRAM stays at or below the total minus the reserve. Sustained CPU stays at or below 80%. RAM stays at or below 85%. GPU power stays at or below the configured limit. |
| NFR-4 | Reliability | At least 95% job success rate over a 24-hour soak test with 20 or more jobs. No unbounded memory growth. |
| NFR-5 | Recoverability | After a crash or reboot, the worker resumes within 2 minutes of boot with no lost completed stages. |
| NFR-6 | Privacy | All processing is local. No outbound network calls during generation, except optional model or library updates started by the operator. |
| NFR-7 | Security | API and UI bind to 127.0.0.1 by default. LAN access is opt-in and documented as protected by a firewall rule. |
| NFR-8 | Licensing | Only models and tools whose licenses permit the operator's commercial use. Each model's license is recorded in the model registry. |
| NFR-9 | Maintainability | Models are swappable through config and workflow files without code changes. Workflows are located by node titles, not node IDs. |
| NFR-10 | Usability | A first video can be created in 5 or fewer form interactions (type, script, voice-over, create, approve). |
| NFR-11 | Portability | All paths are configurable. The system runs entirely from user-space installs plus NSSM services. |

## 9. System Architecture

**Components:**
- **UI:** React + Vite + TypeScript, served by the API.
- **API:** FastAPI on port 8700.
- **Worker:** Python orchestrator with a GPU lane, a render lane, an inbox watcher and the Resource Guard.
- **Ollama** on port 11434: Qwen3.5-9B.
- **ComfyUI** on port 8188: all diffusion, audio, matting and upscaling models.
- **Renderer:** a Remotion project, called through the CLI.
- **FFmpeg:** mixing, reframing and NVENC encoding.
- **Storage:** SQLite (WAL mode) plus a filesystem tree per job.

**Data flow:** UI or inbox → API/DB → worker lanes → (Ollama, ComfyUI, Remotion, FFmpeg) → output folder.

## 10. Model Registry

| Key | Model | Engine | Role | License |
|-----|-------|--------|------|---------|
| director | Qwen3.5-9B | Ollama | Planning, prompting, vision QA | Apache 2.0 |
| t2i_fast | Z-Image-Turbo | ComfyUI | Default images | Apache 2.0 |
| t2i_text | Qwen-Image-2512 (GGUF) | ComfyUI | Typography-heavy images | Apache 2.0 |
| edit | Qwen-Image-Edit-2511 (GGUF) | ComfyUI | Refinement, compositing, consistency | Apache 2.0 |
| i2v | Wan 2.2 TI2V-5B (Q4_K_M) | ComfyUI | AI motion | Apache 2.0 |
| i2v_fast | LTX-2.x distilled | ComfyUI | AI motion (deferred — install after 64 GB RAM upgrade) | LTX-2 Community |
| asr | faster-whisper large-v3-turbo | Python (CPU) | Transcription | MIT |
| music | ACE-Step 1.5 | ComfyUI | Music | MIT |
| matting | BiRefNet | ComfyUI | Background removal | MIT |
| upscale | Real-ESRGAN x4plus | ComfyUI | Upscaling | BSD-3 |

## 11. Data Model

**Job**

| Field | Description |
|-------|-------------|
| id | Unique job ID |
| status | Current state (see Section 12) |
| priority | Higher runs first |
| created | Creation timestamp |
| locked_by | Lane currently holding the job, if any |
| paused | Whether the job is paused |
| retries | Retry count for the current stage |
| error | Last error message |
| data (JSON) | video_type, script, voiceover_path, aspect, assets{}, options{}, brand, export{}, character_bible, motion_directions, music settings |

**Scene** (stored in `plan.json`, one per scene)

| Field | Description |
|-------|-------------|
| id, start, end | Scene number and time range |
| narration | The voice-over line for this scene |
| visual_prompt | Image prompt |
| motion, motion_prompt | Motion type and AI motion prompt |
| on_screen_text | Text overlay |
| asset_ref | Path to an operator asset, if used |
| sfx[] | Sound effect cues |
| seed | Generation seed |
| version | Image version number |
| status | PENDING / APPROVED / LOCKED |
| qa | score, matches_prompt, defects[] |
| history[] | version, path, prompt, mode |

**Other records**

| Record | Fields |
|--------|--------|
| Refine | id, job_id, scene_id, mode (edit/regenerate), prompt, status, created |
| Template | YAML file (see Section 15) |
| BrandKit | id, name, logo_path, colors[], fonts{heading, body}, caption_color |
| Event | job_id, timestamp, stage, level, message, resource snapshot |

## 12. Job State Machine

```
QUEUED → INGESTED → TRANSCRIBED → PLANNED → [PLAN_REVIEW]* → IMAGES_DONE
  → AWAITING_REVIEW (review mode) ──approve──┐
  → (autopilot: auto-QA/regenerate) ─────────┤
                                             ▼
                          APPROVED → MOTION_DONE → AUDIO_READY
                          → RENDERED → DONE
Any stage ──error──► retry (≤N) ──► FAILED
Any state ──pause──► PAUSED ──resume──► previous state
DONE ──re-export──► RENDERED (export only)
```
*PLAN_REVIEW is optional (P1).

**Lane assignment:**
- GPU lane: QUEUED through MOTION_DONE→AUDIO_READY.
- Render lane: AUDIO_READY→RENDERED→DONE.

## 13. API Specification

| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/templates | List templates (fields and defaults) |
| POST | /api/jobs | Create a job (multipart: video_type, script, voiceover, options JSON, assets[]) |
| GET | /api/jobs | List jobs with status |
| GET | /api/jobs/{id} | Job detail and events |
| GET | /api/jobs/{id}/scenes | Scene plan with QA and versions |
| PATCH | /api/jobs/{id}/scenes/{sid} | Edit prompt, motion, timing or text; approve or lock |
| POST | /api/jobs/{id}/scenes/{sid}/refine | Queue a refine (mode, prompt) |
| POST | /api/jobs/{id}/scenes/{sid}/replace | Upload a replacement image |
| POST | /api/jobs/{id}/scenes/{sid}/revert | Revert to a previous version |
| POST | /api/jobs/{id}/approve | Approve all scenes and continue |
| POST | /api/jobs/{id}/preview | Queue a draft render |
| POST | /api/jobs/{id}/export | Set export options and queue an export |
| POST | /api/jobs/{id}/pause and /resume | Job control |
| POST | /api/queue/pause and /resume | Global control |
| GET | /api/system | Resource snapshot |
| GET/PUT | /api/settings | Configuration |
| CRUD | /api/brandkits | Brand kits |
| GET | /jobs/{id}/... | Static files (image and video previews) |

## 14. UI Specification

| Screen | Key elements |
|--------|--------------|
| **Dashboard** | Resource gauges (GPU %, VRAM, °C, W, CPU, RAM, disk); current GPU-lane and render-lane jobs; today's output count; global pause button; recent failures |
| **New Job** | Video-type selector (cards with icons); dynamic form from the template; drag-and-drop asset zones; waveform preview of the voice-over; aspect picker with visual frames; "Create" and "Create + review plan" buttons |
| **Queue** | Table with ID, type, status chip, stage progress bar, ETA and priority. Actions: pause, resume, priority up/down, retry, delete, open. |
| **Scene Board** | Grid of scene cards sorted by time. Each card shows the image (click for a fullscreen lightbox with zoom), narration, time range, QA badge, defects and prompt editor. Buttons: Edit / Regenerate / Replace / Approve / Lock / Revert, plus a motion dropdown. Header has Approve all, Preview draft, and a filter for "show low-QA only". |
| **Job Detail** | Stage timeline, logs, transcript editor, plan JSON viewer, audio player |
| **Export** | Aspect selector, reframe method, sound toggle (with/without), resolution, fps, captions mode, codec and quality; "Export" button; list of previous exports with download links and an inline video player |
| **Settings** | Models and workflows mapping, limits, pipeline mode, paths, inbox status |
| **Brand Kits** | Create and edit kits: logo upload, palette picker, fonts |

**UI rules:**
- Fields render only from the template, and switching type swaps the layout instantly.
- Required fields are marked; optional fields collapse under "Advanced."
- Mobile-friendly layout so jobs can be reviewed on a phone over the LAN (opt-in).

## 15. Template Specification

```yaml
id: string                 # file name = id.yaml
label: string
defaults:
  aspect: "16:9" | "9:16" | "1:1" | "4:5" | "4:3"
  scene_seconds: "min-max"
  image_workflow: workflow file name (without .json)
  image_style: string      # appended to every visual prompt
  negative: string         # optional
  allowed_motion: [motion types]
  music_mood: string
  captions: none | subtle | kinetic
  components: [device_mockup, logo_reveal, lower_third, cta_card, kinetic_title]  # optional
fields:
  - key: string
    label: string
    type: text|textarea|select|number|toggle|color|colors|image|images|audio
    required: bool
    multiple: bool
    default: any
    options: [..]
    showIf: expression     # e.g. "screenshots" or "music == 'upload'"
    help: string
```

## 16. Success Metrics

| Metric | Target (v1) |
|--------|-------------|
| Time to first video for a new user | under 30 minutes after setup |
| Fully automatic job success rate | at least 95% |
| Images accepted without refinement (review mode) | at least 70% |
| Average refines per video | at most 3 |
| Daily output, Ken Burns only (short reels) | at least 30 per day |
| Resource cap violations (sustained over 60 s) | 0 per day |
| Unplanned manual interventions per 24 h | at most 1 |

## 17. Release Plan

| Phase | Scope | Exit criteria |
|-------|-------|---------------|
| **M0 — Infrastructure** (week 1) | Drivers, Ollama, ComfyUI, models, workflows exported with titles | All templates run in ComfyUI; smoke tests pass |
| **M1 — Core pipeline** (weeks 2–3) | Ingest, transcribe, plan, images, Remotion render, export; CLI/API only | 60 s reel produced end-to-end from the API |
| **M2 — Review UI** (weeks 3–4) | New Job dynamic form, Scene Board with refine, Export page, Queue | All P0 user stories demoed |
| **M3 — Automation** (week 5) | Two lanes, inbox, autopilot QA, NSSM services, Resource Guard | 24 h soak test passes NFR-4 |
| **M4 — Polish** (week 6) | All seven templates with components, brand kits, draft preview, transitions, 4K, SRT | All P1 items done |
| **M5 — v2 candidates** | Template editor, autopilot content source, LTX default after RAM upgrade, avatar video | — |

## 18. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| 32 GB RAM is insufficient for large-model offloading | Slowdowns, OOM errors | GGUF Q4 quantisation, one model at a time, page file; upgrade to 64 GB |
| Model or node updates break workflows | Pipeline stops | Pin versions; title-based node lookup; re-run smoke tests after every update |
| LLM outputs an invalid or poorly timed plan | Bad videos | JSON schema enforcement, post-validation and gap fixing, optional plan review |
| Image defects pass autopilot QA | Lower quality | Conservative threshold, bounded retries, periodic human spot checks |
| Garbled text inside images | Unprofessional look | Route text scenes to Qwen-Image; render text as Remotion overlays |
| Thermal stress from 24/7 operation | Hardware wear | Power limit, temperature guard, cooldowns, optional CPU Eco Mode |
| Power outage | Lost work | UPS; persistent state with resume from the last stage |
| License changes | Legal exposure | Model registry with licenses; review before upgrades |
| Disk fills up | Jobs fail | Disk guard and auto-archive |

## 19. Open Questions

1. Which languages besides English will voice-overs use? This affects transcription accuracy and caption fonts.
2. Should storytelling character consistency be done with a trained LoRA per series (higher quality) or only reference-image editing?
3. Is phone access over the LAN needed for remote review in v1?
4. What should happen to jobs left at AWAITING_REVIEW: auto-approve after X hours, or wait indefinitely?
5. Are platform presets needed, such as YouTube Shorts or Instagram safe zones for captions?

## 20. Acceptance Criteria (v1 Definition of Done)

- [ ] A job created with only a script and voice-over produces a playable MP4 with synced captions.
- [ ] Switching between the seven video types changes the form fields and defaults instantly.
- [ ] Images match the template style, and every image can be previewed, edited or regenerated, with version history.
- [ ] Operator screenshots, SFX and motion directions visibly appear at the specified times.
- [ ] Export works at all five aspect ratios, with and without sound.
- [ ] Inbox jobs process unattended in autopilot, and the next job's generation overlaps the current job's render.
- [ ] Over a 24 h soak test: at least 95% success, no sustained resource cap violations, and automatic recovery from a killed service.
- [ ] All services auto-start after reboot, and the pipeline resumes without manual steps.
- [ ] Every model in use has a recorded license that permits the operator's use.

## 21. Glossary

| Term | Meaning |
|------|---------|
| Ken Burns | Slow pan and zoom over a still image |
| I2V | Image-to-video generation |
| GGUF | Quantised model file format that reduces memory use |
| NVENC | NVIDIA's hardware video encoder |
| Ducking | Lowering music volume automatically while the voice plays |
| LUFS | Loudness unit used by streaming platforms |
| Lane | A worker thread dedicated to one resource class (GPU or render) |
| Template | YAML definition of a video type's defaults and UI fields |
````

---

The single most valuable upgrade for this pipeline is going from 32 GB to 64 GB of RAM. With 64 GB, the larger models can offload part of their weights without slowing down, and LTX-2 becomes practical as a faster motion engine.

For building the full UI, the fastest route is to give `PRD.md` and `USER_GUIDE.md` to a coding agent such as Claude Code and ask it to implement milestones M1 to M3. The backend skeleton in the guide gives it a solid starting point.