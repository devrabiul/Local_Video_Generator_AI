"""Catalogue of every AI model the VidForge pipeline loads, plus on-device verification.

Official sizes and SHA-256 hashes were read from the publishers on 2026-10-20:
- Hugging Face files: the repo tree API (huggingface.co/api/models/<repo>/tree/main/<dir>), cross-checked
  against the `x-linked-size` / `x-linked-etag` headers of each resolve URL. Two small non-LFS files
  (vocab.txt, config.yaml) have no published hash; theirs was computed from the official download.
- Ollama models: layer sizes in the registry manifest (registry.ollama.ai/v2/library/<name>/manifests/<tag>).

Hardware figures carry a `basis` so the UI can say where each number comes from:
  "vendor"     — stated by the model publisher (with source link)
  "calculated" — derived from the exact file sizes above
  "estimate"   — practical working figure, not published by the vendor
  "app"        — a VidForge restriction
"""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from ai_engine import BASE_DIR, COMFYUI_DIR, IS_MACOS, IS_WINDOWS, WAN_SUPPORTED, _setting
import tts_engine

CHECKED_ON = "2026-10-20"
HF = "https://huggingface.co"
WAN_REPO = f"{HF}/Comfy-Org/Wan_2.1_ComfyUI_repackaged"
ZIMAGE_REPO = f"{HF}/Comfy-Org/z_image_turbo"
GB = 1024 ** 3


def _hf_file(repo: str, path: str, size: int, sha256: str | None, comfy_folder: str | None = None) -> dict:
    return {
        "name": path.rsplit("/", 1)[-1],
        "url": f"{repo}/resolve/main/{path}",
        "page": f"{repo}/blob/main/{path}",
        "size": size,
        "sha256": sha256,
        "comfy_folder": comfy_folder,
    }


MODELS: list[dict] = [
    {
        "id": "qwen3.5-9b",
        "name": "Qwen3.5 9B",
        "stage": "Script writing",
        "role": "Default script & scene planner (Ollama)",
        "runtime": "ollama",
        "ollama_tag": "qwen3.5:9b",
        "precision": "Q4_K_M · 9.0B parameters",
        "page": "https://ollama.com/library/qwen3.5:9b",
        "download_cmd": "ollama pull qwen3.5:9b",
        "registry_size": 6550825550,
        "registry_layers": {"model": 5629109120, "projector": 921704832},
        "files": [],
        "requirements": {
            "accel_gb": 8,
            "lines": [
                {"label": "GPU / unified memory", "value": "≥ 8 GB", "basis": "estimate",
                 "note": "6.55 GB of weights (incl. 0.92 GB vision projector) plus the context cache for VidForge's 8,192-token context."},
                {"label": "Runs without a GPU", "value": "Yes, on CPU from system RAM (much slower)", "basis": "vendor",
                 "source": "https://github.com/ollama/ollama"},
                {"label": "Disk", "value": "6.55 GB", "basis": "calculated"},
            ],
        },
    },
    {
        "id": "qwen2.5-14b",
        "name": "Qwen2.5 14B",
        "stage": "Script writing",
        "role": "Base of the custom `story-writer` model (Modelfile)",
        "runtime": "ollama",
        "ollama_tag": "qwen2.5:14b",
        "precision": "Q4_K_M · 14.8B parameters",
        "page": "https://ollama.com/library/qwen2.5:14b",
        "download_cmd": "ollama pull qwen2.5:14b  &&  ollama create story-writer -f Modelfile",
        "registry_size": 8988124069,
        "registry_layers": {"model": 8988110688},
        "files": [],
        "requirements": {
            "accel_gb": 12,
            "lines": [
                {"label": "GPU / unified memory", "value": "≥ 12 GB", "basis": "calculated",
                 "note": "8.99 GB of weights + 1.61 GB FP16 KV cache at 8,192 tokens (48 layers × 8 KV heads × 128 dims) ≈ 10.6 GB."},
                {"label": "Runs without a GPU", "value": "Yes, on CPU from system RAM (much slower)", "basis": "vendor",
                 "source": "https://github.com/ollama/ollama"},
                {"label": "Disk", "value": "8.99 GB", "basis": "calculated"},
            ],
        },
    },
    {
        "id": "z-image-turbo",
        "name": "Z-Image Turbo",
        "stage": "Scene images",
        "role": "Text-to-image for every scene (ComfyUI)",
        "runtime": "comfyui",
        "precision": "BF16 diffusion model · FP8 text encoder",
        "page": ZIMAGE_REPO,
        "files": [
            _hf_file(ZIMAGE_REPO, "split_files/diffusion_models/z_image_turbo_bf16.safetensors", 12309866400,
                     "2407613050b809ffdff18a4ac99af83ea6b95443ecebdf80e064a79c825574a6", "diffusion_models"),
            _hf_file(ZIMAGE_REPO, "split_files/text_encoders/qwen_3_4b_fp8_mixed.safetensors", 5631994051,
                     "72450b19758172c5a7273cf7de729d1c17e7f434a104a00167624cba94f68f15", "text_encoders"),
            _hf_file(ZIMAGE_REPO, "split_files/vae/ae.safetensors", 335304388,
                     "afc8e28272cd15db3919bacdb6918ce9c1ed22e96cb12c4d5ed0fba823529e38", "vae"),
        ],
        "requirements": {
            "accel_gb": 16,
            "lines": [
                {"label": "GPU memory (VRAM)", "value": "16 GB", "basis": "vendor",
                 "note": "“Fits comfortably within 16G VRAM consumer devices.”",
                 "source": f"{HF}/Tongyi-MAI/Z-Image-Turbo"},
                {"label": "System RAM", "value": "≥ 24 GB", "basis": "estimate",
                 "note": "ComfyUI keeps the 18.3 GB of model files in RAM while swapping the text encoder and diffusion model on the GPU."},
                {"label": "Disk", "value": "18.28 GB", "basis": "calculated"},
            ],
        },
    },
    {
        "id": "wan21-i2v-14b",
        "name": "Wan 2.1 Image-to-Video 14B (720p)",
        "stage": "Video animation",
        "role": "Optional AI motion for each scene image (ComfyUI)",
        "runtime": "comfyui",
        "precision": "FP8 (e4m3fn) · 14B parameters",
        "page": WAN_REPO,
        "files": [
            _hf_file(WAN_REPO, "split_files/diffusion_models/wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors", 16397245448,
                     "b2051cd29d6b2f0c924fa7a3e78a4772f0134d7b059f21590dcce416f4f6cbe8", "diffusion_models"),
            _hf_file(WAN_REPO, "split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", 6735906897,
                     "c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68", "text_encoders"),
            _hf_file(WAN_REPO, "split_files/clip_vision/clip_vision_h.safetensors", 1264219396,
                     "64a7ef761bfccbadbaa3da77366aac4185a6c58fa5de5f589b42a65bcc21f161", "clip_vision"),
            _hf_file(WAN_REPO, "split_files/vae/wan_2.1_vae.safetensors", 253815318,
                     "2fc39d31359a4b0a64f55876d8ff7fa8d780956ae2cb13463b0223e15148976b", "vae"),
        ],
        "requirements": {
            "accel_gb": 16,
            "platform_block": None if WAN_SUPPORTED else "VidForge disables Wan 2.1 motion on macOS.",
            "lines": [
                {"label": "GPU", "value": "NVIDIA (CUDA)", "basis": "app",
                 "note": "VidForge only enables Wan 2.1 on Windows/Linux; macOS uses Ken Burns motion instead."},
                {"label": "GPU memory (VRAM)", "value": "≥ 16 GB, 24 GB to hold it fully", "basis": "calculated",
                 "note": "The FP8 transformer alone is 16.40 GB. Below that, ComfyUI offloads part of it to system RAM, which is slow. "
                         "Wan's official README gives no consumer-GPU figure for the 14B model; it suggests --offload_model and --t5_cpu on OOM.",
                 "source": "https://github.com/Wan-Video/Wan2.1"},
                {"label": "System RAM", "value": "≥ 32 GB", "basis": "estimate",
                 "note": "24.65 GB of model files have to be held in RAM while ComfyUI moves them to and from the GPU."},
                {"label": "Disk", "value": "24.65 GB", "basis": "calculated"},
            ],
        },
    },
    {
        "id": "f5-tts",
        "name": "F5-TTS v1 Base",
        "stage": "Voice (local)",
        "role": "Zero-shot voice cloning for “My Voices”",
        "runtime": "f5",
        "precision": "FP32 safetensors",
        "page": f"{HF}/SWivid/F5-TTS",
        "files": [
            _hf_file(f"{HF}/SWivid/F5-TTS", "F5TTS_v1_Base/model_1250000.safetensors", 1348435761,
                     "670900fd14e6c458b95da6e9ed317cdb20dbaf7a1c02ac06a05475a9d32b6a38"),
            _hf_file(f"{HF}/SWivid/F5-TTS", "F5TTS_v1_Base/vocab.txt", 13800,
                     "2a05f992e00af9b0bd3800a8d23e78d520dbd705284ed2eedb5f4bd29398fa3c"),
        ],
        "requirements": {
            "accel_gb": 4,
            "lines": [
                {"label": "GPU", "value": "NVIDIA, AMD, Intel or Apple Silicon", "basis": "vendor",
                 "source": "https://github.com/SWivid/F5-TTS"},
                {"label": "GPU / unified memory", "value": "≥ 4 GB", "basis": "estimate",
                 "note": "1.35 GB of FP32 weights plus the Vocos vocoder and inference buffers."},
                {"label": "Disk", "value": "1.35 GB", "basis": "calculated"},
            ],
        },
    },
    {
        "id": "vocos",
        "name": "Vocos mel 24 kHz",
        "stage": "Voice (local)",
        "role": "Vocoder F5-TTS uses to turn spectrograms into audio (downloaded automatically)",
        "runtime": "f5",
        "precision": "FP32 PyTorch",
        "page": f"{HF}/charactr/vocos-mel-24khz",
        "files": [
            _hf_file(f"{HF}/charactr/vocos-mel-24khz", "pytorch_model.bin", 54365991,
                     "97ec976ad1fd67a33ab2682d29c0ac7df85234fae875aefcc5fb215681a91b2a"),
            _hf_file(f"{HF}/charactr/vocos-mel-24khz", "config.yaml", 461,
                     "da9033922f969a47f0c160010226919e59f27761fd5066f3828d46de6650b0fc"),
        ],
        "requirements": {
            "accel_gb": 0,
            "lines": [
                {"label": "Memory", "value": "Included in F5-TTS's figure", "basis": "calculated",
                 "note": "54 MB of weights, loaded alongside F5-TTS."},
                {"label": "Disk", "value": "54 MB", "basis": "calculated"},
            ],
        },
    },
]

CLOUD_MODELS = [
    {
        "id": "gemini-tts",
        "name": "Gemini TTS",
        "model": tts_engine.GEMINI_MODEL,
        "role": "Default narration voice (Google cloud)",
        "page": "https://aistudio.google.com/apikey",
        "note": "Runs on Google's servers — nothing to download. Needs an internet connection and a Google AI Studio API key.",
    },
    {
        "id": "elevenlabs",
        "name": "ElevenLabs",
        "model": tts_engine.ELEVENLABS_MODEL,
        "role": "Ultra-realistic narration (ElevenLabs cloud)",
        "page": "https://elevenlabs.io/",
        "note": "Runs on ElevenLabs' servers — nothing to download. Needs an internet connection and an ElevenLabs API key.",
    },
]


# --------------------------------------------------------------------------- #
# Locating files on this device
# --------------------------------------------------------------------------- #
def _hf_cache_dir() -> Path:
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def _hf_cache_candidates(page_url: str, rel_path: str) -> list[Path]:
    """Every snapshot of the repo in the Hugging Face cache that could hold this file."""
    repo = page_url.replace(f"{HF}/", "", 1)
    snapshots = _hf_cache_dir() / f"models--{repo.replace('/', '--')}" / "snapshots"
    if not snapshots.is_dir():
        return []
    return [snap / rel_path for snap in sorted(snapshots.iterdir())]


def _candidates(model: dict, f: dict) -> list[Path]:
    rel = f["url"].split("/resolve/main/", 1)[1]
    if f["comfy_folder"]:
        return [COMFYUI_DIR / "models" / f["comfy_folder"] / f["name"]]
    paths: list[Path] = []
    if model["id"] == "f5-tts":
        configured = tts_engine.F5_CHECKPOINT if f["name"].endswith(".safetensors") else tts_engine.F5_VOCAB
        if configured:
            paths.append(Path(configured))
        if f["name"].endswith(".safetensors"):
            paths.append(BASE_DIR / "backend" / "models" / "F5-TTS" / f["name"])
    return paths + _hf_cache_candidates(model["page"], rel)


def _ollama_models_dir() -> Path:
    configured = _setting("ollama_models_dir", "OLLAMA_MODELS", "")
    return Path(configured) if configured else Path.home() / ".ollama" / "models"


def _describe(path: Path) -> dict:
    """Disk size of a file; a symlink (as in the HF cache) is followed to its blob."""
    real = path.resolve()
    return {"path": str(path), "bytes": real.stat().st_size}


def _scan_file(model: dict, f: dict) -> dict:
    found = next((p for p in _candidates(model, f) if p.is_file()), None)
    result = {
        "name": f["name"],
        "expected_bytes": f["size"],
        "searched": [str(p) for p in _candidates(model, f)][:3],
    }
    if not found:
        return {**result, "status": "missing"}
    info = _describe(found)
    return {**result, **info, "status": "match" if info["bytes"] == f["size"] else "mismatch"}


def _scan_ollama(model: dict) -> dict:
    name, tag = model["ollama_tag"].split(":")
    root = _ollama_models_dir()
    manifest = root / "manifests" / "registry.ollama.ai" / "library" / name / tag
    result = {"name": model["ollama_tag"], "expected_bytes": model["registry_size"], "searched": [str(manifest)]}
    if not manifest.is_file():
        return {**result, "status": "missing"}
    try:
        data = json.loads(manifest.read_text())
        blobs = [l for l in data.get("layers", [])] + [data["config"]]
        total = 0
        for layer in blobs:
            blob = root / "blobs" / layer["digest"].replace(":", "-")
            if not blob.is_file():
                return {**result, "status": "incomplete", "path": str(manifest)}
            total += blob.stat().st_size
    except (OSError, ValueError, KeyError):
        return {**result, "status": "unreadable", "path": str(manifest)}
    return {**result, "path": str(manifest), "bytes": total, "status": "match" if total == model["registry_size"] else "mismatch"}


def scan_device() -> list[dict]:
    out = []
    for model in MODELS:
        files = [_scan_ollama(model)] if model["runtime"] == "ollama" else [_scan_file(model, f) for f in model["files"]]
        out.append({"id": model["id"], "files": files})
    return out


# --------------------------------------------------------------------------- #
# SHA-256 verification (on demand — hashing a 16 GB file takes a while)
# --------------------------------------------------------------------------- #
_hash_cache: dict[tuple[str, int, float], str] = {}


def _sha256(path: Path) -> str:
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime)
    if key not in _hash_cache:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
                h.update(chunk)
        _hash_cache[key] = h.hexdigest()
    return _hash_cache[key]


def verify_hash(model_id: str, file_name: str) -> dict:
    model = next((m for m in MODELS if m["id"] == model_id), None)
    if not model:
        raise KeyError("Unknown model")
    if model["runtime"] == "ollama":
        name, tag = model["ollama_tag"].split(":")
        root = _ollama_models_dir()
        manifest = root / "manifests" / "registry.ollama.ai" / "library" / name / tag
        if not manifest.is_file():
            raise FileNotFoundError("Model is not downloaded")
        layer = next(l for l in json.loads(manifest.read_text())["layers"] if l["mediaType"].endswith("image.model"))
        blob = root / "blobs" / layer["digest"].replace(":", "-")
        expected = layer["digest"].split(":", 1)[1]
        actual = _sha256(blob.resolve())
        return {"expected": expected, "actual": actual, "match": actual == expected, "path": str(blob)}
    f = next((x for x in model["files"] if x["name"] == file_name), None)
    if not f or not f["sha256"]:
        raise KeyError("No published SHA-256 for this file")
    path = next((p for p in _candidates(model, f) if p.is_file()), None)
    if not path:
        raise FileNotFoundError("File is not downloaded")
    actual = _sha256(path.resolve())
    return {"expected": f["sha256"], "actual": actual, "match": actual == f["sha256"], "path": str(path)}


# --------------------------------------------------------------------------- #
# This device's hardware
# --------------------------------------------------------------------------- #
def _run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _total_ram() -> int:
    if IS_MACOS:
        return int(_run(["sysctl", "-n", "hw.memsize"]) or 0)
    if IS_WINDOWS:
        import ctypes

        class MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        status = MemStatus()
        status.dwLength = ctypes.sizeof(MemStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        return int(status.ullTotalPhys)
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except OSError:
        pass
    return 0


def device_info() -> dict:
    ram = _total_ram()
    gpus = []
    nvidia = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    for line in filter(None, nvidia.splitlines()):
        name, mem_mb = [x.strip() for x in line.rsplit(",", 1)]
        gpus.append({"name": name, "vram_bytes": int(float(mem_mb)) * 1024 * 1024, "kind": "nvidia"})

    chip = platform.processor() or platform.machine()
    unified = False
    if IS_MACOS:
        chip = _run(["sysctl", "-n", "machdep.cpu.brand_string"]) or chip
        unified = platform.machine() == "arm64"
        if unified:
            gpus.append({"name": f"{chip} GPU", "vram_bytes": ram, "kind": "apple"})

    disk_root = COMFYUI_DIR if COMFYUI_DIR.exists() else BASE_DIR
    disk = shutil.disk_usage(disk_root)
    # Memory the models can use on the accelerator: largest NVIDIA VRAM, or unified memory on Apple Silicon
    accel = max((g["vram_bytes"] for g in gpus), default=0)
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": chip,
        "ram_bytes": ram,
        "gpus": gpus,
        "unified_memory": unified,
        "accel_bytes": accel,
        "disk_free_bytes": disk.free,
        "disk_path": str(disk_root),
        "python": sys.version.split()[0],
    }


def catalog() -> dict:
    return {
        "checked_on": CHECKED_ON,
        "models": MODELS,
        "cloud": CLOUD_MODELS,
        "comfyui_dir": str(COMFYUI_DIR),
        "ollama_models_dir": str(_ollama_models_dir()),
        "hf_cache_dir": str(_hf_cache_dir()),
    }
