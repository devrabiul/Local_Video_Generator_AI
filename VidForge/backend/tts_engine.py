"""Voice-over engines: Gemini TTS, ElevenLabs and local F5-TTS voice cloning.

Scripts carry engine-neutral performance cues ([whispers], [short pause], ...) plus a
per-scene "delivery" direction; each engine renders them in its own syntax so the same
storyboard performs well everywhere.
"""
import asyncio
import base64
import json
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Awaitable, Callable

import httpx
from loguru import logger

from ai_engine import BASE_DIR, COMFYUI_DIR, CONFIG_FILE, FFMPEG, FFPROBE, _default_f5_python, _load_config, _setting

ENGINES = ("gemini", "elevenlabs", "f5tts")
DEFAULT_ENGINE = "gemini"

def _extract_retry_delay(res: httpx.Response, attempt: int, default_delay: float = 25.0) -> float:
    """Extracts wait time from 429/503 response headers or Google/ElevenLabs error payload."""
    # 1. Standard Retry-After header (seconds)
    retry_header = res.headers.get("retry-after")
    if retry_header:
        try:
            return max(float(retry_header), 1.0)
        except ValueError:
            pass

    # 2. Google RPC RetryInfo in JSON response
    try:
        data = res.json()
        error = data.get("error", {})
        for detail in error.get("details", []):
            if isinstance(detail, dict) and str(detail.get("@type", "")).endswith("RetryInfo"):
                delay_str = str(detail.get("retryDelay", ""))
                if delay_str.endswith("s"):
                    return max(float(delay_str[:-1]), 1.0)

        # 3. Message regex: "retry in 44s", "retry after 44s", etc.
        msg = error.get("message", "") or res.text
        match = re.search(r"retry\s+(?:in|after)\s+([0-9]+(?:\.[0-9]+)?)\s*s", msg, re.IGNORECASE)
        if match:
            return max(float(match.group(1)), 1.0)
    except Exception:
        pass

    # 4. Fallback backoff based on attempt count
    return default_delay * (1.5 ** (attempt - 1))


GEMINI_TTS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_MODEL = _setting("gemini_tts_model", "VIDFORGE_GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
ELEVENLABS_MODEL = _setting("elevenlabs_model", "VIDFORGE_ELEVENLABS_MODEL", "eleven_v4")
# Lower = more expressive and varied delivery, higher = steadier
ELEVENLABS_STABILITY = float(_setting("elevenlabs_stability", "VIDFORGE_ELEVENLABS_STABILITY", "0.35"))

F5_PYTHON = Path(_setting("f5_python", "VIDFORGE_F5_PYTHON", str(_default_f5_python(COMFYUI_DIR))))
F5_CHECKPOINT = _setting("f5_checkpoint", "VIDFORGE_F5_CHECKPOINT", "")
F5_VOCAB = _setting("f5_vocab", "VIDFORGE_F5_VOCAB", "")
F5_CLI_SCRIPT = BASE_DIR / "backend" / "f5_infer_cli.py"
REF_VOICES_DIR = BASE_DIR / "backend" / "ref_voices"
CUSTOM_VOICES_DIR = REF_VOICES_DIR / "custom"
CUSTOM_MANIFEST = CUSTOM_VOICES_DIR / "manifest.json"
SAMPLES_DIR = BASE_DIR / "output" / "voice_samples"

# F5 copies pacing and emotion from the reference clip, and clips references longer than ~12s
REF_MIN_SECONDS = 4.0
REF_MAX_SECONDS = 12.0

GEMINI_VOICES = {
    "Charon": {"name": "Charon", "description": "Informative, grounded documentary narrator"},
    "Algenib": {"name": "Algenib", "description": "Gravelly, weathered and dramatic"},
    "Gacrux": {"name": "Gacrux", "description": "Mature, wise and measured"},
    "Sulafat": {"name": "Sulafat", "description": "Warm, inviting storyteller"},
    "Enceladus": {"name": "Enceladus", "description": "Breathy, intimate and suspenseful"},
    "Achernar": {"name": "Achernar", "description": "Soft, gentle and tender"},
    "Iapetus": {"name": "Iapetus", "description": "Clear, articulate presenter"},
    "Kore": {"name": "Kore", "description": "Firm, confident and authoritative"},
    "Rasalgethi": {"name": "Rasalgethi", "description": "Informative, calm explainer"},
    "Vindemiatrix": {"name": "Vindemiatrix", "description": "Gentle, soothing and emotional"},
    "Sadaltager": {"name": "Sadaltager", "description": "Knowledgeable, thoughtful educator"},
    "Fenrir": {"name": "Fenrir", "description": "Excitable, energetic hype voice"},
    "Puck": {"name": "Puck", "description": "Upbeat, lively and playful"},
    "Despina": {"name": "Despina", "description": "Smooth, polished commercial voice"},
}

ELEVENLABS_VOICES = {
    "pNInz6obpgDQGcFmaJgB": {"name": "Adam", "description": "Deep, Authoritative Narration - US Male (Documentary & Epic)"},
    "ErXwobaYiN019PkySvjV": {"name": "Antoni", "description": "Dramatic Storyteller & Engaging - US Male"},
    "JBFqnCBsd6RMkjVDRZzb": {"name": "George", "description": "Warm, Eloquent British Documentary - UK Male"},
    "21m00Tcm4TlvDq8ikWAM": {"name": "Rachel", "description": "Calm, Intimate & Clear Narration - US Female"},
    "EXAVITQu4vr4xnSDxMaL": {"name": "Bella", "description": "Expressive, Vibrant & Emotional - US Female"},
    "onwK4e9ZLuTAKqWW03F9": {"name": "Daniel", "description": "Authoritative, Deep Broadcast - UK Male"},
    "TX3LPaxmHKxFdv7VOQHJ": {"name": "Liam", "description": "Young, Energetic & Direct - US Male"},
}

F5_PRESET_VOICES = {
    "bn_epic_male": {
        "name": "Pradeep Seed (বাংলা গম্ভীর পুরুষ কণ্ঠ)",
        "file": "bn_epic_male.wav",
        "text": "প্রাচীন বাংলার ইতিহাস এক গৌরবময় বীরত্ব ও ত্যাগের কাহিনী।",
        "lang": "bn"
    },
    "bn_soft_female": {
        "name": "Nabanita Seed (বাংলা সাবলীল নারী কণ্ঠ)",
        "file": "bn_soft_female.wav",
        "text": "নদীর কূল ঘেঁষে গড়ে ওঠা এই জনপদের প্রতিটি ধূলিকণায় লুকিয়ে আছে কত না বলা রূপকথা।",
        "lang": "bn"
    },
    "en_nature": {
        "name": "Nature & Earth (English Cinematic Male)",
        "file": "en_nature.wav",
        "text": "Some call me nature, others call me mother nature.",
        "lang": "en"
    }
}

# Preview lines include cues so a sample demonstrates the expressive range
SAMPLE_PHRASES = {
    "bn": "স্বাগতম VidForge-এ। [short pause] আজ আপনাদের শোনাব এক হারিয়ে যাওয়া রাজ্যের গল্প… [whispers] যে গল্প আগে কেউ কখনো বলেনি।",
    "hi": "VidForge में आपका स्वागत है। [short pause] आज मैं आपको एक खोए हुए राज्य की कहानी सुनाऊँगा… [whispers] जो पहले कभी किसी ने नहीं सुनाई।",
    "en": "Welcome to VidForge. [short pause] Tonight, I'll tell you the story of a forgotten kingdom… [whispers] one that no one has ever told before."
}
SAMPLE_STYLE = "warm, intimate storyteller; slow and expressive"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_tts_config() -> dict:
    cfg = _load_config() or {}
    cfg.setdefault("elevenlabs_api_key", "")
    cfg.setdefault("gemini_api_key", "")
    if cfg.get("default_engine") not in ENGINES:
        cfg["default_engine"] = DEFAULT_ENGINE
    return cfg

def save_tts_config(data: dict) -> dict:
    cfg = _load_config() or {}
    cfg.update(data)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return get_tts_config()

def _gemini_keys() -> list[str]:
    raw = get_tts_config().get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
    if not raw:
        return []
    return [k.strip() for k in re.split(r"[,;\n\r]+", str(raw)) if k.strip()]

def _gemini_key() -> str:
    keys = _gemini_keys()
    return keys[0] if keys else ""

def _elevenlabs_key() -> str:

    return get_tts_config().get("elevenlabs_api_key") or os.environ.get("ELEVENLABS_API_KEY", "")

def get_all_tts_engines() -> dict:
    return {
        "gemini": {
            "name": "Gemini TTS (Expressive Studio Narration)",
            "description": "Google Gemini speech with per-scene emotional direction",
            "model": GEMINI_MODEL,
            "configured": bool(_gemini_key()),
            "voices": GEMINI_VOICES
        },
        "elevenlabs": {
            "name": "ElevenLabs Studio (Ultra-Realistic Human)",
            "description": "Hyper-realistic emotion, breaths, pauses, and cadence",
            "model": ELEVENLABS_MODEL,
            "configured": bool(_elevenlabs_key()),
            "voices": ELEVENLABS_VOICES
        },
        "f5tts": {
            "name": "F5-TTS (Local Zero-Shot Voice Cloning)",
            "description": "Local GPU voice cloning from your own reference recordings",
            "ready": F5_PYTHON.exists(),
            "voices": list_f5_voices()
        }
    }


# ---------------------------------------------------------------------------
# Performance cue rendering
# ---------------------------------------------------------------------------

CUE_PATTERN = re.compile(r"\[([^\[\]]{1,40})\]")

GEMINI_TAGS = {
    "whispers": "<whispers>", "whispering": "<whispering>", "softly": "<whispers>",
    "sighs": "<sigh>", "sigh": "<sigh>",
    "laughs": "<laugh>", "laugh": "<laugh>", "laughing": "<laughter>", "laughter": "<laughter>",
    "chuckle": "<chuckle>", "chuckles": "<chuckles>",
    "gasps": "<gasp>", "gasp": "<gasp>",
    "breath": "<breath>", "heavy breath": "<heavy breath>", "phew": "<phew>",
    "cry": "<cry>", "sob": "<sob>", "groan": "<groan>", "shout": "<shout>",
    "cheer": "<cheer>", "excited": "<cheer>", "sad": "<sigh>",
    "short pause": "<short pause>", "long pause": "<long pause>",
}
ELEVENLABS_TAGS = {
    "whispers": "[whispering]", "whispering": "[whispering]", "softly": "[softly]",
    "excited": "[excited]", "sad": "[sad]",
    "sighs": "[sigh]", "sigh": "[sigh]",
    "laughs": "[laughing]", "laugh": "[laughing]", "chuckle": "[chuckles]", "chuckles": "[chuckles]",
    "gasps": "[gasp]", "gasp": "[gasp]",
    "shout": "[shouting]", "breath": "[breath]", "groan": "[groans]",
    "short pause": "…", "long pause": "… …",
}
PLAIN_PAUSES = {"short pause": ",", "long pause": "…"}

def _tidy(text: str) -> str:
    text = re.sub(r"\s+([,।.!?])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"…(\s*…)+", lambda m: "… …" if " " in m.group(0) else "…", text)
    return re.sub(r"\s{2,}", " ", text).strip()

def _render_cues(text: str, mapping: dict, keep_unknown: bool = False) -> str:
    def repl(match: re.Match) -> str:
        cue = match.group(1).strip().lower()
        if cue in mapping:
            return mapping[cue]
        return match.group(0) if keep_unknown else ""
    return _tidy(CUE_PATTERN.sub(repl, text))

def plain_text(text: str) -> str:
    """Narration with cues removed and pauses turned into punctuation (for F5 and context)."""
    return _render_cues(text, PLAIN_PAUSES)

def _elevenlabs_supports_tags(model: str) -> bool:
    return model.startswith(("eleven_v3", "eleven_v4"))


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _transcode(src: Path, dest: Path, extra_args: list[str] | None = None) -> None:
    cmd = [FFMPEG, "-y", "-i", str(src), *(extra_args or []), str(dest)]
    subprocess.run(cmd, check=True, capture_output=True)

def _duration(path: Path) -> float:
    cmd = [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    return float(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip())


# ---------------------------------------------------------------------------
# Gemini TTS
# ---------------------------------------------------------------------------

async def generate_gemini_voiceover(
    text: str,
    voice: str,
    output_path: Path,
    style: str = "",
    on_status: Callable[[str], Awaitable[None]] | None = None,
    max_retries: int = 5
) -> Path:
    keys = _gemini_keys()
    if not keys:
        raise ValueError("Gemini API key is required. Add it in the voice API key settings.")

    content = {"type": "text", "text": _render_cues(text, GEMINI_TAGS)}
    if style:
        content["annotations"] = [{"type": "speech_metadata", "style": style}]
    payload = {
        "model": GEMINI_MODEL,
        "input": [{"type": "user_input", "content": [content]}],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]}
    }

    last_error = None
    key_idx = 0
    attempt = 1

    while attempt <= max_retries and key_idx < len(keys):
        api_key = keys[key_idx]
        async with httpx.AsyncClient(timeout=180.0) as client:
            res = await client.post(GEMINI_TTS_URL, json=payload, headers={"x-goog-api-key": api_key})

        if res.status_code == 200:
            break

        err_msg = res.text
        try:
            err_msg = res.json().get("error", {}).get("message") or res.text
        except Exception:
            pass

        # Check for 429 Rate Limit or 503 Server Unavailable
        is_rate_limit = (
            res.status_code in (429, 503)
            or "rate limit" in err_msg.lower()
            or "resource_exhausted" in err_msg.lower()
            or "quota" in err_msg.lower()
        )
        if is_rate_limit:
            delay = _extract_retry_delay(res, attempt, default_delay=30.0)

            # If daily quota exceeded (> 120s wait or daily limit in message)
            if delay > 120.0 or "day" in err_msg.lower():
                if key_idx + 1 < len(keys):
                    key_idx += 1
                    logger.warning(f"Gemini API key #{key_idx} daily limit hit. Rotating to key #{key_idx + 1}...")
                    if on_status:
                        await on_status(f"Gemini key limit reached. Switching to backup key #{key_idx + 1}...")
                    continue
                else:
                    raise RuntimeError(
                        "Gemini TTS Free Tier daily limit reached (10 requests/day). "
                        "To continue: (1) Add another Gemini API key separated by comma in Voice Settings, "
                        "(2) Upgrade to Pay-As-You-Go at https://aistudio.google.com, or "
                        "(3) Switch to ElevenLabs or local F5-TTS."
                    )

            if attempt < max_retries:
                wait_seconds = max(delay + 2.0, 5.0)
                logger.warning(
                    f"Gemini TTS rate limited ({res.status_code}). Attempt {attempt}/{max_retries}. "
                    f"Waiting {wait_seconds:.1f}s before retry..."
                )
                remaining = int(round(wait_seconds))
                while remaining > 0:
                    if on_status:
                        await on_status(
                            f"Gemini TTS rate limit cooldown: waiting {remaining}s before retry ({attempt}/{max_retries})..."
                        )
                    step = min(remaining, 5)
                    await asyncio.sleep(step)
                    remaining -= step

                last_error = f"Gemini TTS error ({res.status_code}): {err_msg}"
                attempt += 1
                continue

        raise RuntimeError(f"Gemini TTS error ({res.status_code}): {err_msg}")
    else:
        raise RuntimeError(last_error or f"Gemini TTS failed after {max_retries} attempts.")

    audio_items = [
        item
        for step in res.json().get("steps", []) if step.get("type") == "model_output"
        for item in step.get("content", []) if item.get("type") == "audio"
    ]
    if not audio_items:
        raise RuntimeError("Gemini TTS returned no audio")

    # Unary responses are 24 kHz mono WAV; convert to the requested container
    wav_path = output_path.with_suffix(".gemini.wav")
    wav_path.write_bytes(base64.b64decode(audio_items[-1]["data"]))
    try:
        await asyncio.to_thread(_transcode, wav_path, output_path, ["-b:a", "192k"])
    finally:
        wav_path.unlink(missing_ok=True)
    return output_path


# ---------------------------------------------------------------------------
# ElevenLabs
# ---------------------------------------------------------------------------

async def generate_elevenlabs_voiceover(
    text: str,
    voice_id: str,
    output_path: Path,
    delivery: str = "",
    previous_text: str = "",
    next_text: str = "",
    stitch_ids: list[str] | None = None,
    language: str | None = None,
    on_status: Callable[[str], Awaitable[None]] | None = None,
    max_retries: int = 4
) -> Path:
    api_key = _elevenlabs_key()
    if not api_key:
        raise ValueError("ElevenLabs API Key is required. Please add your API key in ElevenLabs settings.")

    model = ELEVENLABS_MODEL
    if _elevenlabs_supports_tags(model):
        spoken = _render_cues(text, ELEVENLABS_TAGS)
        if delivery:
            spoken = f"[{delivery}] {spoken}"
    else:
        spoken = _render_cues(text, {"short pause": "…", "long pause": "… …"})

    stability = ELEVENLABS_STABILITY
    if model.startswith("eleven_v3"):
        # v3 only accepts the Creative / Natural / Robust presets
        stability = min((0.0, 0.5, 1.0), key=lambda preset: abs(preset - stability))
    voice_settings = {"stability": stability, "similarity_boost": 0.75, "use_speaker_boost": True}
    if not model.startswith("eleven_v4"):
        voice_settings["style"] = 0.35  # v4 has no style control

    payload = {"text": spoken, "model_id": model, "voice_settings": voice_settings}
    if language and model != "eleven_multilingual_v2":
        payload["language_code"] = language
    # Request stitching carries prosody across scenes (not available on eleven_v3)
    if stitch_ids and not model.startswith("eleven_v3"):
        payload["previous_request_ids"] = stitch_ids[-3:]
    elif previous_text:
        payload["previous_text"] = plain_text(previous_text)
    if next_text:
        payload["next_text"] = plain_text(next_text)

    headers = {"xi-api-key": api_key.strip(), "Content-Type": "application/json", "Accept": "audio/mpeg"}
    last_error = None
    res = None
    for attempt in range(1, max_retries + 1):
        async with httpx.AsyncClient(timeout=120.0) as client:
            res = await client.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}", json=payload, headers=headers)
        if res.status_code == 200:
            break
        err_msg = res.text
        try:
            err_json = res.json()
            err_msg = err_json.get("detail", {}).get("message") or err_json.get("message") or res.text
        except Exception:
            pass

        if res.status_code in (429, 503) and attempt < max_retries:
            delay = _extract_retry_delay(res, attempt, default_delay=15.0)
            wait_seconds = max(delay + 1.0, 5.0)
            logger.warning(f"ElevenLabs rate limited ({res.status_code}). Attempt {attempt}/{max_retries}. Waiting {wait_seconds:.1f}s...")
            remaining = int(round(wait_seconds))
            while remaining > 0:
                if on_status:
                    await on_status(f"ElevenLabs rate limit cooldown: waiting {remaining}s before retry ({attempt}/{max_retries})...")
                step = min(remaining, 5)
                await asyncio.sleep(step)
                remaining -= step
            last_error = f"ElevenLabs error ({res.status_code}): {err_msg}"
            continue

        raise RuntimeError(f"ElevenLabs error ({res.status_code}): {err_msg}")
    else:
        raise RuntimeError(last_error or f"ElevenLabs failed after {max_retries} attempts.")

    output_path.write_bytes(res.content)
    if stitch_ids is not None and res.headers.get("request-id"):
        stitch_ids.append(res.headers["request-id"])
    return output_path



# ---------------------------------------------------------------------------
# F5-TTS voice library and cloning
# ---------------------------------------------------------------------------

def _read_custom_manifest() -> dict:
    if CUSTOM_MANIFEST.exists():
        try:
            return json.loads(CUSTOM_MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _write_custom_manifest(data: dict) -> None:
    CUSTOM_VOICES_DIR.mkdir(parents=True, exist_ok=True)
    CUSTOM_MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def list_f5_voices() -> list[dict]:
    voices = [
        {"id": key, "name": meta["name"], "lang": meta["lang"], "custom": False}
        for key, meta in F5_PRESET_VOICES.items()
    ]
    for key, meta in _read_custom_manifest().items():
        voices.append({
            "id": key, "name": meta["name"], "lang": meta.get("lang", ""), "custom": True,
            "duration": meta.get("duration"), "transcript": meta.get("text", "")
        })
    return voices

def _resolve_f5_reference(ref_key: str) -> tuple[Path, str]:
    custom = _read_custom_manifest().get(ref_key)
    if custom:
        candidate = CUSTOM_VOICES_DIR / custom["file"]
        if candidate.exists():
            return candidate, custom["text"]
    if ref_key in F5_PRESET_VOICES:
        meta = F5_PRESET_VOICES[ref_key]
        candidate = REF_VOICES_DIR / meta["file"]
        if candidate.exists():
            return candidate, meta["text"]
    raise ValueError(f"F5-TTS reference voice '{ref_key}' was not found")

def save_custom_voice(name: str, transcript: str, language: str, audio_bytes: bytes, filename: str) -> dict:
    """Stores a user recording as an F5-TTS reference: trimmed, 24 kHz mono WAV."""
    name, transcript = name.strip(), transcript.strip()
    if not name or not transcript:
        raise ValueError("Voice name and the exact transcript of the recording are required")

    CUSTOM_VOICES_DIR.mkdir(parents=True, exist_ok=True)
    voice_id = f"my_{uuid.uuid4().hex[:8]}"
    raw_path = CUSTOM_VOICES_DIR / f"{voice_id}_upload{Path(filename).suffix or '.webm'}"
    wav_path = CUSTOM_VOICES_DIR / f"{voice_id}.wav"
    raw_path.write_bytes(audio_bytes)
    try:
        # Trim leading/trailing silence, keep natural pauses inside the recording
        trim = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"
        _transcode(raw_path, wav_path, ["-ac", "1", "-ar", "24000", "-af", trim])
    except subprocess.CalledProcessError:
        raise ValueError("Could not read that audio file. Upload a WAV, MP3, M4A or WebM recording.")
    finally:
        raw_path.unlink(missing_ok=True)

    duration = _duration(wav_path)
    if not REF_MIN_SECONDS <= duration <= REF_MAX_SECONDS + 0.5:
        wav_path.unlink(missing_ok=True)
        raise ValueError(f"The recording is {duration:.1f}s of speech; it must be between {REF_MIN_SECONDS:.0f} and {REF_MAX_SECONDS:.0f} seconds (8-12s works best).")

    manifest = _read_custom_manifest()
    manifest[voice_id] = {"name": name, "file": wav_path.name, "text": transcript, "lang": language, "duration": round(duration, 1)}
    _write_custom_manifest(manifest)
    logger.info(f"Saved custom F5 voice '{name}' ({voice_id}, {duration:.1f}s)")
    return {"id": voice_id, **manifest[voice_id]}

def delete_custom_voice(voice_id: str) -> bool:
    manifest = _read_custom_manifest()
    meta = manifest.pop(voice_id, None)
    if not meta:
        return False
    (CUSTOM_VOICES_DIR / meta["file"]).unlink(missing_ok=True)
    _write_custom_manifest(manifest)
    for sample in SAMPLES_DIR.glob(f"f5tts_{voice_id}_*"):
        sample.unlink(missing_ok=True)
    return True

async def generate_f5_voiceover(text: str, ref_key: str, output_path: Path) -> Path:
    ref_file, ref_txt = _resolve_f5_reference(ref_key)
    cmd = [
        str(F5_PYTHON), str(F5_CLI_SCRIPT),
        "--ref_audio", str(ref_file),
        "--ref_text", ref_txt,
        "--gen_text", plain_text(text),
        "--output", str(output_path),
        "--speed", "1.0"
    ]
    if F5_CHECKPOINT:
        cmd += ["--ckpt_file", F5_CHECKPOINT]
    if F5_VOCAB:
        cmd += ["--vocab_file", F5_VOCAB]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["VIDFORGE_FFMPEG"] = FFMPEG
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env)
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace")
        logger.error(f"F5-TTS failed: {err_msg}")
        raise RuntimeError(f"F5-TTS error: {err_msg}")
    return output_path


# ---------------------------------------------------------------------------
# Unified entry points
# ---------------------------------------------------------------------------

def split_voice(voice: str) -> tuple[str, str]:
    """Voice ids are stored as '<engine>:<voice>'."""
    engine, _, name = voice.partition(":")
    if engine in ("f5", "f5-tts"):
        engine = "f5tts"
    if engine == "edge":
        raise ValueError("Edge-TTS has been removed. Choose a Gemini, ElevenLabs or F5-TTS voice.")
    if engine not in ENGINES or not name:
        raise ValueError(f"Unknown voice '{voice}'")
    return engine, name

async def generate_voiceover(
    text: str,
    voice: str,
    output_path: Path,
    delivery: str = "",
    narrator_style: str = "",
    previous_text: str = "",
    next_text: str = "",
    stitch_ids: list[str] | None = None,
    language: str | None = None,
    on_status: Callable[[str], Awaitable[None]] | None = None
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine, name = split_voice(voice)
    logger.info(f"Generating voiceover: engine='{engine}', voice='{name}', delivery='{delivery}'")

    if engine == "gemini":
        parts = []
        if delivery:
            parts.append(delivery)
        if narrator_style and narrator_style not in delivery:
            parts.append(narrator_style)
        style = "; ".join(parts)[:120]
        return await generate_gemini_voiceover(text, name, output_path, style=style, on_status=on_status)
    if engine == "elevenlabs":
        return await generate_elevenlabs_voiceover(
            text, name, output_path, delivery=delivery, previous_text=previous_text,
            next_text=next_text, stitch_ids=stitch_ids, language=language, on_status=on_status
        )
    return await generate_f5_voiceover(text, name, output_path)


async def generate_voice_sample(voice: str, engine: str, language: str = "bn") -> str:
    """Generates (and caches) a short expressive preview for a voice."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    language = language if language in SAMPLE_PHRASES else "en"
    model = {"gemini": GEMINI_MODEL, "elevenlabs": ELEVENLABS_MODEL}.get(engine, "f5")
    clean_voice = re.sub(r"[^A-Za-z0-9_-]", "_", voice)
    sample_file = SAMPLES_DIR / f"{engine}_{clean_voice}_{language}_{model}.mp3"

    if not sample_file.exists() or sample_file.stat().st_size == 0:
        await generate_voiceover(
            text=SAMPLE_PHRASES[language],
            voice=f"{engine}:{voice}",
            output_path=sample_file,
            delivery=SAMPLE_STYLE,
            language=language
        )
    return f"/output/voice_samples/{sample_file.name}"

async def test_api_key(provider: str, key: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        if provider == "gemini":
            res = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}",
                headers={"x-goog-api-key": key}
            )
            if res.status_code == 200:
                return {"valid": True, "message": f"Valid Gemini key ({GEMINI_MODEL} available)"}
            if res.status_code == 404:
                return {"valid": True, "message": f"Key is valid, but {GEMINI_MODEL} is not available on this project"}
            return {"valid": False, "message": f"Verification failed (HTTP {res.status_code})"}

        res = await client.get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key})
        if res.status_code == 200:
            data = res.json()
            tier = data.get("tier", "unknown")
            char_count = data.get("character_count", 0)
            char_limit = data.get("character_limit", 0)
            return {
                "valid": True, "tier": tier, "character_count": char_count, "character_limit": char_limit,
                "message": f"Valid ({tier} tier, {char_count:,} / {char_limit:,} chars used)"
            }
        return {"valid": False, "message": f"Verification failed (HTTP {res.status_code})"}
