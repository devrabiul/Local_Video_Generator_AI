import asyncio
import json
import sys
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from loguru import logger
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Literal
from pydantic import BaseModel, Field
from database import (
    init_db, add_job, get_all_jobs, get_job, delete_job, delete_all_jobs, requeue_job, update_job_fields, RUNNING_STATUSES
)
from worker import worker_loop
import ai_engine
import model_catalog
import music_library
import projects
import tts_engine
import character_3d_engine
from tripo3d_provider import Tripo3DProvider, get_tripo3d_api_key

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = projects.OUTPUT_DIR
JOBS_DIR = projects.JOBS_DIR
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    worker_task = asyncio.create_task(worker_loop())
    yield
    worker_task.cancel()

app = FastAPI(title="VidForge AI Studio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CreateJobRequest(BaseModel):
    story_prompt: str
    language: str = "bn"
    voice: str = "Charon"
    tts_engine: str = "gemini"
    narrator_style: str = ""
    aspect_ratio: str = "9:16"
    title: str = ""
    scenes: list[dict] | None = None
    video_type: str = "story"
    target_duration: int = 60
    motion_mode: str = "kenburns"
    music_theme: str = "cinematic_epic"
    # Optional background music: "" = none; otherwise a track id from /api/music
    music_track: str = ""
    music_volume: int = Field(100, ge=0, le=200)
    voice_volume: int = Field(100, ge=50, le=150)
    music_ducking: bool = True
    enable_subtitles: bool = True
    resolution: Literal[480, 720, 1080, 1440] = 1080  # height of the short side
    fps: Literal[24, 25, 30, 60] = 30
    script_mode: Literal["ai_generate", "direct"] = "ai_generate"
    enable_character_ref: bool = False
    character_references: list[dict] = []

class TTSConfigRequest(BaseModel):
    elevenlabs_api_key: str | None = None
    gemini_api_key: str | None = None
    default_engine: str | None = None
    local_tts_model: str | None = None

class TestKeyRequest(BaseModel):
    api_key: str
    provider: str = "elevenlabs"

class GenerateStoryRequest(BaseModel):
    topic: str
    model: str = "story-writer:latest"
    language: str = "bn"
    genre: str = "historical"
    tone: str = "epic"
    scene_count: int | None = None
    video_type: str = "story"
    target_duration: int = 60

class RegenerateRequest(BaseModel):
    # script: new script, voice and visuals · media: keep script, new voice and visuals · visuals: keep script and voice
    mode: Literal["script", "media", "visuals"] = "media"

class RefineRequest(BaseModel):
    instruction: str = Field(..., min_length=3, max_length=2000)

class ThumbnailBackgroundRequest(BaseModel):
    prompt: str = ""
    instruction: str = ""
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str = "story-writer:latest"
    messages: list[ChatMessage]
    system_prompt: str | None = None

class ParseDirectScriptRequest(BaseModel):
    text: str
    language: str = "bn"

@app.get("/api/system/status")
async def get_system_status():
    ollama_ok = False
    ollama_models = []
    default_model = "qwen3.5:9b"
    comfyui_ok = False
    vram_used_gb = vram_total_gb = None

    async with httpx.AsyncClient(timeout=3.0) as client:
        # Check Ollama
        try:
            r = await client.get(f"{ai_engine.OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                ollama_ok = True
                data = r.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
                if "qwen3.5:9b" in ollama_models:
                    default_model = "qwen3.5:9b"
                elif "story-writer:latest" in ollama_models:
                    default_model = "story-writer:latest"
                elif ollama_models:
                    default_model = ollama_models[0]
        except Exception:
            ollama_ok = False

        # Check ComfyUI
        try:
            r = await client.get(f"{ai_engine.COMFYUI_URL}/system_stats")
            if r.status_code == 200:
                comfyui_ok = True
                devices = r.json().get("devices") or []
                if devices and devices[0].get("vram_total"):
                    vram_total_gb = round(devices[0]["vram_total"] / 1024**3, 1)
                    vram_used_gb = round(vram_total_gb - devices[0].get("vram_free", 0) / 1024**3, 1)
        except Exception:
            comfyui_ok = False

    return {
        "ollama_online": ollama_ok,
        "models": ollama_models,
        "default_model": default_model,
        "comfyui_online": comfyui_ok,
        "platform": sys.platform,
        "wan_available": ai_engine.WAN_SUPPORTED,
        "video_encoder": await asyncio.to_thread(ai_engine.get_video_encoder),
        "gpu_name": await asyncio.to_thread(_gpu_name),
        "vram_used_gb": vram_used_gb,
        "vram_total_gb": vram_total_gb,
    }

_gpu_name_cache: str | None = None

def _gpu_name() -> str:
    """Primary accelerator name, detected once (nvidia-smi is too slow to run on every status poll)."""
    global _gpu_name_cache
    if _gpu_name_cache is None:
        gpus = model_catalog.device_info()["gpus"]
        _gpu_name_cache = gpus[0]["name"] if gpus else ""
    return _gpu_name_cache

def _mask(key: str) -> str:
    return f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ("***" if key else "")

@app.get("/api/tts/engines")
def get_tts_engines():
    return tts_engine.get_all_tts_engines()

@app.get("/api/tts/config")
def get_tts_config_api():
    cfg = tts_engine.get_tts_config()
    eleven_key = cfg.get("elevenlabs_api_key", "")
    gemini_key = cfg.get("gemini_api_key", "")
    return {
        "has_elevenlabs_key": bool(eleven_key),
        "masked_key": _mask(eleven_key),
        "has_gemini_key": bool(gemini_key),
        "gemini_masked_key": _mask(gemini_key),
        "default_engine": cfg["default_engine"],
        "local_tts_model": tts_engine.get_local_tts_model(),
        "local_tts_models": tts_engine.LOCAL_TTS_MODELS,
    }

@app.post("/api/tts/config")
def set_tts_config_api(req: TTSConfigRequest):
    update_data = {}
    if req.elevenlabs_api_key is not None:
        update_data["elevenlabs_api_key"] = req.elevenlabs_api_key.strip()
    if req.gemini_api_key is not None:
        update_data["gemini_api_key"] = req.gemini_api_key.strip()
    if req.default_engine is not None:
        if req.default_engine not in tts_engine.ENGINES:
            raise HTTPException(status_code=400, detail="Unknown TTS engine")
        update_data["default_engine"] = req.default_engine
    if req.local_tts_model is not None:
        if req.local_tts_model not in tts_engine.LOCAL_TTS_MODELS:
            raise HTTPException(status_code=400, detail="Unknown local voice model")
        update_data["local_tts_model"] = req.local_tts_model
    saved = tts_engine.save_tts_config(update_data)
    return {
        "ok": True,
        "has_elevenlabs_key": bool(saved.get("elevenlabs_api_key")),
        "has_gemini_key": bool(saved.get("gemini_api_key"))
    }

@app.post("/api/tts/test_key")
async def test_tts_key(req: TestKeyRequest):
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key is required")
    try:
        return await tts_engine.test_api_key(req.provider, key)
    except Exception as e:
        return {"valid": False, "message": f"Connection error: {str(e)}"}

@app.get("/api/voices/preview")
async def get_voice_preview(voice: str, engine: str = "gemini", language: str = "bn", force: bool = False):
    if not voice:
        raise HTTPException(status_code=400, detail="Voice is required")
    try:
        url = await tts_engine.generate_voice_sample(voice=voice, engine=engine, language=language, force=force)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/voices/custom")
def list_custom_voices():
    return [v for v in tts_engine.list_f5_voices() if v["custom"]]

@app.post("/api/voices/custom")
async def add_custom_voice(
    name: str = Form(...),
    transcript: str = Form(...),
    language: str = Form("bn"),
    file: UploadFile = File(...)
):
    audio = await file.read()
    if len(audio) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Recording is too large (max 25 MB)")
    try:
        return await asyncio.to_thread(tts_engine.save_custom_voice, name, transcript, language, audio, file.filename or "")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/voices/custom/{voice_id}")
def remove_custom_voice(voice_id: str):
    if not tts_engine.delete_custom_voice(voice_id):
        raise HTTPException(status_code=404, detail="Voice not found")
    return {"ok": True}

@app.post("/api/ollama/generate_story")
async def generate_story_api(req: GenerateStoryRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
    try:
        res = await ai_engine.generate_story_script(
            topic=req.topic,
            language=req.language,
            model=req.model,
            genre=req.genre,
            tone=req.tone,
            scene_count=req.scene_count,
            video_type=req.video_type,
            target_duration=req.target_duration
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama generation error: {str(e)}")

@app.post("/api/ollama/chat")
async def chat_with_ollama(req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")
    
    ollama_messages = []
    if req.system_prompt:
        ollama_messages.append({"role": "system", "content": req.system_prompt})
    
    for m in req.messages:
        ollama_messages.append({"role": m.role, "content": m.content})
        
    try:
        await ai_engine.free_gpu_memory(unload_comfy=True, unload_ollama=False)
        async with httpx.AsyncClient(timeout=180.0) as client:
            payload = {
                "model": req.model,
                "messages": ollama_messages,
                "stream": False,
                "keep_alive": "30s"
            }
            res = await client.post(f"{ai_engine.OLLAMA_URL}/api/chat", json=payload)
            if res.status_code != 200:
                err_detail = res.text
                try:
                    err_detail = res.json().get("error", res.text)
                except Exception:
                    pass
                raise HTTPException(status_code=res.status_code, detail=f"Ollama error: {err_detail}")
            data = res.json()
            return {
                "message": data["message"]["content"],
                "model": data.get("model", req.model)
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama chat error: {str(e)}")

@app.get("/api/models")
async def list_models():
    catalog = model_catalog.catalog()
    catalog["device"], catalog["local"] = await asyncio.gather(
        asyncio.to_thread(model_catalog.device_info),
        asyncio.to_thread(model_catalog.scan_device),
    )
    return catalog

class VerifyModelRequest(BaseModel):
    model_id: str
    file_name: str = ""

@app.post("/api/models/verify")
async def verify_model_file(req: VerifyModelRequest):
    try:
        return await asyncio.to_thread(model_catalog.verify_hash, req.model_id, req.file_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e.args[0]) if e.args else "Cannot verify this file")

@app.get("/api/music")
def list_music():
    return {"tracks": music_library.list_tracks()}

@app.get("/api/jobs")
def list_jobs():
    return get_all_jobs()

@app.post("/api/jobs")
def create_job(req: CreateJobRequest):
    if not req.story_prompt.strip():
        raise HTTPException(status_code=400, detail="Story prompt cannot be empty")
    job_id = f"job_{uuid.uuid4().hex[:8]}"
    title = req.title.strip() or req.story_prompt.strip()[:40] + "..."
    scenes_json = json.dumps(req.scenes, ensure_ascii=False) if req.scenes else "[]"
    if req.tts_engine not in tts_engine.ENGINES:
        raise HTTPException(status_code=400, detail="Unknown TTS engine")
    voice_identifier = req.voice if ":" in req.voice else f"{req.tts_engine}:{req.voice}"
    if req.music_track and not music_library.resolve_track(req.music_track):
        raise HTTPException(status_code=400, detail="Selected background music track was not found")

    add_job(
        job_id=job_id,
        title=title,
        story_prompt=req.story_prompt,
        language=req.language,
        voice=voice_identifier,
        aspect_ratio=req.aspect_ratio,
        scenes_json=scenes_json,
        video_type=req.video_type,
        target_duration=req.target_duration,
        motion_mode=req.motion_mode,
        music_theme=req.music_theme,
        narrator_style=req.narrator_style,
        music_track=req.music_track,
        music_volume=req.music_volume,
        voice_volume=req.voice_volume,
        music_ducking=req.music_ducking,
        enable_subtitles=req.enable_subtitles,
        resolution=req.resolution,
        fps=req.fps,
        script_mode=req.script_mode,
        character_references=json.dumps(req.character_references, ensure_ascii=False) if (req.enable_character_ref and req.character_references) else "[]"
    )
    return {"id": job_id, "status": "QUEUED"}

@app.post("/api/script/parse_direct")
async def parse_direct_script_endpoint(req: ParseDirectScriptRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Script text cannot be empty")
    try:
        scenes = await ai_engine.build_scenes_from_direct_script(req.text, req.language)
        return {"scenes": scenes, "count": len(scenes)}
    except Exception as e:
        logger.exception("Error parsing direct script")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}")
def get_job_detail(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.delete("/api/jobs")
def remove_all_jobs():
    """Deletes all projects and every asset they produced."""
    jobs = get_all_jobs()
    delete_all_jobs()
    projects.purge_all_project_files()
    return {"ok": True, "count": len(jobs)}

@app.delete("/api/jobs/{job_id}")
def remove_job(job_id: str):
    """Deletes a project and every asset it produced. A render in progress is stopped by the worker."""
    if not projects.is_valid_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid project id")
    delete_job(job_id)
    projects.purge_project_files(job_id)
    return {"ok": True}

# ---------------------------------------------------------------------------
# Project revisions: regenerate / refine
# ---------------------------------------------------------------------------

REGENERATE_CLEARS = {
    "script": ("audio_", "image_", "clip_", "raw_wan_", "tmp_", "scene_"),
    "media": ("audio_", "image_", "clip_", "raw_wan_", "tmp_", "scene_"),
    "visuals": ("image_", "clip_", "raw_wan_", "tmp_", "scene_"),
}

def _project_or_404(job_id: str) -> dict:
    job = get_job(job_id) if projects.is_valid_id(job_id) else None
    if not job:
        raise HTTPException(status_code=404, detail="Project not found")
    return job

def _revisable_project(job_id: str) -> dict:
    job = _project_or_404(job_id)
    if job["status"] == "QUEUED" or job["status"] in RUNNING_STATUSES:
        raise HTTPException(status_code=409, detail="This project is already rendering. Wait for it to finish first.")
    return job

@app.post("/api/jobs/{job_id}/regenerate")
def regenerate_project(job_id: str, req: RegenerateRequest):
    _revisable_project(job_id)
    work = projects.work_dir(job_id)
    if work.exists():
        for f in work.iterdir():
            if f.is_file() and f.name.startswith(REGENERATE_CLEARS[req.mode]):
                f.unlink(missing_ok=True)
    labels = {"script": "new script, voice and visuals", "media": "new voiceover and visuals", "visuals": "new visuals"}
    requeue_job(job_id, step=f"Queued to regenerate with {labels[req.mode]}",
                scenes_json="[]" if req.mode == "script" else None)
    return {"id": job_id, "status": "QUEUED"}

@app.post("/api/jobs/{job_id}/retry")
def retry_project(job_id: str):
    job = _project_or_404(job_id)
    if job["status"] in ("QUEUED", *RUNNING_STATUSES):
        raise HTTPException(status_code=409, detail="This project is already rendering.")
    requeue_job(job_id, step="Resuming project from last saved state...")
    return {"id": job_id, "status": "QUEUED"}

@app.post("/api/jobs/{job_id}/refine")
def refine_project(job_id: str, req: RefineRequest):
    job = _revisable_project(job_id)
    if not job.get("scenes"):
        raise HTTPException(status_code=400, detail="This project has no script to refine yet. Regenerate it instead.")
    requeue_job(job_id, step="Queued to refine with your instructions", refine_instruction=req.instruction.strip())
    return {"id": job_id, "status": "QUEUED"}


@app.get("/api/jobs/{job_id}/download/{kind}")
def download_project_file(job_id: str, kind: Literal["video", "thumbnail", "subtitles"]):
    job = _project_or_404(job_id)
    if kind == "subtitles":
        srt = projects.find_output(job_id, "subtitles", ".srt") or (projects.work_dir(job_id) / "subtitles.srt")
        if not srt or not srt.exists():
            raise HTTPException(status_code=404, detail="This project has no subtitles file")
        return FileResponse(srt, filename=projects.download_name(job["title"], ".srt"), media_type="text/plain; charset=utf-8")
    path = projects.url_to_path(job.get("output_video" if kind == "video" else "thumbnail") or "")
    if not path:
        raise HTTPException(status_code=404, detail=f"This project has no {kind} yet")
    suffix = path.suffix if kind == "video" else f"_thumbnail{path.suffix}"
    return FileResponse(path, filename=projects.download_name(job["title"], suffix))

# ---------------------------------------------------------------------------
# Thumbnail Studio
# ---------------------------------------------------------------------------

MAX_IMAGE_BYTES = 15 * 1024 * 1024
IMAGE_SIGNATURES = {b"\x89PNG\r\n\x1a\n": ".png", b"\xff\xd8\xff": ".jpg", b"RIFF": ".webp"}

def _image_suffix(data: bytes) -> str:
    for sig, suffix in IMAGE_SIGNATURES.items():
        if data.startswith(sig) and (suffix != ".webp" or data[8:12] == b"WEBP"):
            return suffix
    raise HTTPException(status_code=400, detail="Only PNG, JPEG or WebP images are supported")

async def _read_image(file: UploadFile) -> tuple[bytes, str]:
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (max 15 MB)")
    return data, _image_suffix(data)

def _thumb_backgrounds(job_id: str) -> list[str]:
    work = projects.work_dir(job_id)
    files = sorted(work.glob("thumb_bg_*"), key=lambda f: f.stat().st_mtime, reverse=True) if work.exists() else []
    return [projects.work_url(job_id, f.name) for f in files]

def _save_thumb_background(job_id: str, data: bytes, suffix: str) -> str:
    work = projects.work_dir(job_id)
    work.mkdir(parents=True, exist_ok=True)
    name = f"thumb_bg_{int(time.time() * 1000)}{suffix}"
    (work / name).write_bytes(data)
    return projects.work_url(job_id, name)

@app.post("/api/jobs/{job_id}/thumbnail")
async def save_thumbnail(job_id: str, file: UploadFile = File(...), design: str = Form("{}")):
    _project_or_404(job_id)
    data, suffix = await _read_image(file)
    try:
        json.loads(design)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid thumbnail design data")
    thumb = projects.new_output_path(job_id, "thumb", suffix)
    thumb.write_bytes(data)
    if get_job(job_id) is None:  # deleted while uploading
        projects.purge_project_files(job_id)
        raise HTTPException(status_code=404, detail="Project not found")
    projects.remove_old_outputs(job_id, "thumb", keep=thumb)
    url = projects.output_url(job_id, thumb.name)
    update_job_fields(job_id, thumbnail=url, thumbnail_design=design)
    return {"thumbnail": url}

@app.get("/api/jobs/{job_id}/thumbnail/backgrounds")
def list_thumbnail_backgrounds(job_id: str):
    _project_or_404(job_id)
    return {"backgrounds": _thumb_backgrounds(job_id)}

@app.post("/api/jobs/{job_id}/thumbnail/backgrounds")
async def generate_thumbnail_background(job_id: str, req: ThumbnailBackgroundRequest):
    """Generates a new AI background. With an instruction, the prompt is first refined by the LLM."""
    job = _project_or_404(job_id)
    prompt = req.prompt.strip()
    if req.instruction.strip():
        try:
            prompt = await ai_engine.refine_image_prompt(prompt, req.instruction.strip(), job["title"])
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Could not refine the prompt: {e}")
    if not prompt:
        raise HTTPException(status_code=400, detail="Describe the background you want")
    work = projects.work_dir(job_id)
    tmp = work / f"thumb_pending_{uuid.uuid4().hex[:8]}.png"  # not a scene-asset prefix, so worker cleanup leaves it alone
    try:
        await ai_engine.generate_scene_image(prompt, req.aspect_ratio, tmp, project_id=job_id)
        if get_job(job_id) is None:
            projects.purge_project_files(job_id)
            raise HTTPException(status_code=404, detail="Project not found")
        url = _save_thumb_background(job_id, tmp.read_bytes(), ".png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image generation failed (is ComfyUI running?): {e}")
    finally:
        tmp.unlink(missing_ok=True)
    return {"url": url, "prompt": prompt}

@app.post("/api/jobs/{job_id}/thumbnail/backgrounds/upload")
async def upload_thumbnail_background(job_id: str, file: UploadFile = File(...)):
    _project_or_404(job_id)
    data, suffix = await _read_image(file)
    return {"url": _save_thumb_background(job_id, data, suffix)}

@app.post("/api/jobs/{job_id}/thumbnail/headlines")
async def suggest_thumbnail_headlines(job_id: str):
    job = _project_or_404(job_id)
    synopsis = job.get("story_prompt") or " ".join(sc.get("narration", "") for sc in job.get("scenes", [])[:3])
    try:
        headlines = await ai_engine.suggest_thumbnail_headlines(job["title"], synopsis[:1500], job["language"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama could not suggest headlines: {e}")
    return {"headlines": headlines}

@app.post("/api/jobs/{job_id}/poster/generate")
async def generate_thematic_poster(job_id: str):
    """Synthesizes the core theme of the video and renders a master cinematic poster artwork."""
    job = _project_or_404(job_id)
    title = job.get("title", "")
    story_prompt = job.get("story_prompt", "")
    scenes = job.get("scenes", [])
    video_type = job.get("video_type", "story")
    language = job.get("language", "bn")
    aspect_ratio = job.get("aspect_ratio", "16:9")
    character_refs = job.get("character_references") or []
    
    try:
        concept = await ai_engine.generate_thematic_poster_concept(
            title=title,
            story_prompt=story_prompt,
            scenes=scenes,
            video_type=video_type,
            language=language,
            character_references=character_refs
        )
    except Exception as e:
        logger.error(f"Failed to generate poster concept: {e}")
        raise HTTPException(status_code=502, detail=f"Ollama could not generate poster concept: {e}")
    
    poster_prompt = concept.get("poster_prompt", "").strip()
    if not poster_prompt:
        raise HTTPException(status_code=502, detail="Failed to synthesize poster prompt")
        
    work = projects.work_dir(job_id)
    tmp = work / f"thumb_pending_{uuid.uuid4().hex[:8]}.png"
    try:
        await ai_engine.generate_scene_image(poster_prompt, aspect_ratio, tmp, project_id=job_id)
        if get_job(job_id) is None:
            projects.purge_project_files(job_id)
            raise HTTPException(status_code=404, detail="Project not found")
        url = _save_thumb_background(job_id, tmp.read_bytes(), ".png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image generation failed in ComfyUI: {e}")
    finally:
        tmp.unlink(missing_ok=True)
        
    return {
        "url": url,
        "prompt": poster_prompt,
        "headline": concept.get("headline", title),
        "tagline": concept.get("tagline", ""),
        "subline": concept.get("subline", ""),
        "theme_summary": concept.get("theme_summary", ""),
        "recommended_style": concept.get("recommended_style", "cinematic_gold"),
        "textColor": concept.get("textColor", "#ffffff"),
        "accentColor": concept.get("accentColor", "#facc15"),
    }

CHARACTERS_UPLOAD_DIR = projects.JOBS_DIR / "uploads" / "characters"
CHARACTERS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/api/characters/upload")
async def upload_character_image(
    file: UploadFile = File(...),
    character_name: str = Form(""),
    video_type: str = Form("animation")
):
    data, suffix = await _read_image(file)
    CHARACTERS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"char_{uuid.uuid4().hex[:10]}{suffix}"
    out_file = CHARACTERS_UPLOAD_DIR / filename
    out_file.write_bytes(data)
    url = f"/jobs/uploads/characters/{filename}"

    # Analyze face to extract accurate 3D cartoon character likeness
    analysis = await ai_engine.extract_character_face_features(
        image_path=out_file,
        character_name=character_name,
        video_type=video_type
    )

    return {
        "url": url,
        "filename": filename,
        "name": analysis.get("name", character_name),
        "look": analysis.get("look", ""),
        "cartoon_look": analysis.get("cartoon_look", ""),
        "features_summary": analysis.get("features_summary", "")
    }

# =========================================================================
# Character Vault (Git-Tracked Persistent Characters)
# =========================================================================
CHARACTERS_VAULT_DIR = projects.BASE_DIR / "characters"
CHARACTERS_AVATARS_DIR = CHARACTERS_VAULT_DIR / "avatars"
CHARACTERS_ASSETS_DIR = CHARACTERS_VAULT_DIR / "assets"
CHARACTERS_JSON_PATH = CHARACTERS_VAULT_DIR / "characters.json"
CHARACTERS_AVATARS_DIR.mkdir(parents=True, exist_ok=True)
CHARACTERS_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
if not CHARACTERS_JSON_PATH.exists():
    CHARACTERS_JSON_PATH.write_text("[]", encoding="utf-8")

def load_saved_characters() -> list[dict]:
    if not CHARACTERS_JSON_PATH.exists():
        return []
    try:
        return json.loads(CHARACTERS_JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_saved_characters(chars: list[dict]) -> None:
    CHARACTERS_JSON_PATH.write_text(json.dumps(chars, ensure_ascii=False, indent=2), encoding="utf-8")

@app.get("/api/characters")
async def list_saved_characters():
    return load_saved_characters()

@app.post("/api/characters")
async def create_or_update_saved_character(
    name: str = Form(...),
    look: str = Form(""),
    features_summary: str = Form(""),
    voice_preset: str = Form(""),
    existing_image_url: str = Form(""),
    file: UploadFile | None = File(None),
    video_type: str = Form("animation")
):
    chars = load_saved_characters()
    char_id = f"char_{uuid.uuid4().hex[:8]}"
    avatar_url = ""

    # Case A: User uploaded an image file directly
    if file and file.filename:
        data, suffix = await _read_image(file)
        avatar_filename = f"{char_id}{suffix}"
        avatar_path = CHARACTERS_AVATARS_DIR / avatar_filename
        avatar_path.write_bytes(data)
        avatar_url = f"/characters/avatars/{avatar_filename}"
        
        # If look is empty, auto-analyze face
        if not look:
            analysis = await ai_engine.extract_character_face_features(
                image_path=avatar_path,
                character_name=name,
                video_type=video_type
            )
            look = analysis.get("look") or ""
            if not features_summary:
                features_summary = analysis.get("features_summary") or ""

    # Case B: User already uploaded via /api/characters/upload and wants to save it to vault
    elif existing_image_url:
        if existing_image_url.startswith("/characters/avatars/"):
            avatar_url = existing_image_url
        else:
            rel = existing_image_url.lstrip("/").replace("jobs/", "", 1)
            src_file = projects.JOBS_DIR / rel
            if src_file.exists():
                suffix = src_file.suffix or ".png"
                avatar_filename = f"{char_id}{suffix}"
                avatar_path = CHARACTERS_AVATARS_DIR / avatar_filename
                shutil.copy2(src_file, avatar_path)
                avatar_url = f"/characters/avatars/{avatar_filename}"
            else:
                avatar_url = existing_image_url

    new_char = {
        "id": char_id,
        "name": name.strip(),
        "look": look.strip(),
        "features_summary": features_summary.strip(),
        "avatar_url": avatar_url,
        "voice_preset": voice_preset.strip(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    # Check if a character with exact same name already exists -> update it, otherwise append
    existing_idx = next((i for i, c in enumerate(chars) if c.get("name", "").strip().lower() == name.strip().lower()), None)
    if existing_idx is not None:
        if not avatar_url and chars[existing_idx].get("avatar_url"):
            new_char["avatar_url"] = chars[existing_idx]["avatar_url"]
        new_char["id"] = chars[existing_idx]["id"]
        chars[existing_idx] = new_char
    else:
        chars.append(new_char)

    save_saved_characters(chars)
    return new_char

@app.delete("/api/characters/{char_id}")
async def delete_saved_character(char_id: str):
    chars = load_saved_characters()
    target = next((c for c in chars if c.get("id") == char_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Character not found")
    
    # Remove avatar file if it lives in /characters/avatars/
    if target.get("avatar_url", "").startswith("/characters/avatars/"):
        fname = target["avatar_url"].split("/")[-1]
        (CHARACTERS_AVATARS_DIR / fname).unlink(missing_ok=True)

    # Clean up persistent 3D assets folder
    asset_dir = CHARACTERS_ASSETS_DIR / char_id
    if asset_dir.exists():
        shutil.rmtree(asset_dir, ignore_errors=True)

    chars = [c for c in chars if c.get("id") != char_id]
    save_saved_characters(chars)
    return {"status": "ok", "deleted_id": char_id}

@app.delete("/api/3d/characters/{char_id}")
async def delete_3d_character(char_id: str):
    """Deletes character completely from vault and removes all persistent 3D assets."""
    chars = load_saved_characters()
    target = next((c for c in chars if c.get("id") == char_id), None)
    if target:
        if target.get("avatar_url", "").startswith("/characters/avatars/"):
            fname = target["avatar_url"].split("/")[-1]
            (CHARACTERS_AVATARS_DIR / fname).unlink(missing_ok=True)
        chars = [c for c in chars if c.get("id") != char_id]
        save_saved_characters(chars)
    
    asset_dir = CHARACTERS_ASSETS_DIR / char_id
    if asset_dir.exists():
        shutil.rmtree(asset_dir, ignore_errors=True)
    
    return {"status": "ok", "deleted_character_id": char_id}

@app.delete("/api/3d/characters/{char_id}/assets")
async def reset_3d_character_assets(char_id: str):
    """Resets/cleans generated 3D files while keeping reference image and vault profile."""
    asset_dir = CHARACTERS_ASSETS_DIR / char_id
    if asset_dir.exists():
        for filename in ["mesh.glb", "rigged.glb", "character.blend", "profile.json"]:
            (asset_dir / filename).unlink(missing_ok=True)
    # Re-initialize fresh clean profile
    prof = character_3d_engine.load_character_3d_profile(char_id)
    return {"status": "ok", "profile": prof}

@app.delete("/api/3d/characters/{char_id}/renders/{video_filename}")
async def delete_3d_rendered_video(char_id: str, video_filename: str):
    """Deletes a specific rendered scene video file."""
    video_path = CHARACTERS_ASSETS_DIR / char_id / "renders" / video_filename
    if video_path.exists():
        video_path.unlink(missing_ok=True)
        return {"status": "ok", "deleted": video_filename}
    raise HTTPException(status_code=404, detail="Rendered video not found")

# =========================================================================
# Persistent 3D Character Animation System Endpoints
# =========================================================================

class Render3DSceneRequest(BaseModel):
    character_id: str
    scene_id: int = 1
    animation: str = "walk"
    camera_mode: str = "medium"
    lighting_preset: str = "studio"
    duration: float = 4.0
    dialogue: str = ""
    voice: str = "Charon"
    tts_engine: str = "gemini"
    language: str = "bn"
    aspect_ratio: str = "9:16"

@app.get("/api/3d/status")
async def get_3d_system_status():
    blender_bin = character_3d_engine.find_blender_binary()
    tripo_key = get_tripo3d_api_key()
    return {
        "blender_installed": bool(blender_bin),
        "blender_path": blender_bin,
        "tripo3d_configured": bool(tripo_key),
        "animation_presets": character_3d_engine.ANIMATION_PRESETS,
        "blendshape_targets": character_3d_engine.ARKit_FACIAL_BLENDSHAPES,
        "gpu": "NVIDIA GeForce RTX 5070 Ti (16GB VRAM)"
    }

@app.get("/api/3d/characters")
async def list_3d_characters():
    saved = load_saved_characters()
    result = []
    for c in saved:
        cid = c.get("id")
        if not cid:
            continue
        prof = character_3d_engine.load_character_3d_profile(cid)
        prof["name"] = c.get("name", prof.get("name", ""))
        prof["avatar_url"] = c.get("avatar_url", "")
        prof["look"] = c.get("look", "")
        result.append(prof)
    return result

@app.get("/api/3d/characters/{char_id}")
async def get_3d_character_profile(char_id: str):
    saved = load_saved_characters()
    char_info = next((c for c in saved if c.get("id") == char_id), None)
    prof = character_3d_engine.load_character_3d_profile(char_id)
    if char_info:
        prof["name"] = char_info.get("name", "")
        prof["avatar_url"] = char_info.get("avatar_url", "")
        prof["look"] = char_info.get("look", "")
    return prof

@app.post("/api/3d/characters/{char_id}/generate-local")
async def generate_local_3d_character(char_id: str):
    saved = load_saved_characters()
    char_info = next((c for c in saved if c.get("id") == char_id), None)
    avatar_path = None
    if char_info and char_info.get("avatar_url"):
        raw_url = char_info["avatar_url"].lstrip("/")
        candidate = projects.BASE_DIR / raw_url
        if candidate.exists():
            avatar_path = candidate

    try:
        prof = await character_3d_engine.generate_local_rigged_character(char_id, avatar_path)
        if char_info:
            prof["name"] = char_info.get("name", "")
            prof["avatar_url"] = char_info.get("avatar_url", "")
        return {"status": "SUCCESS", "profile": prof}
    except Exception as e:
        logger.error(f"Local 3D character generation failed for {char_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/3d/characters/{char_id}/generate-tripo3d")
async def generate_tripo3d_character(char_id: str):
    tripo = Tripo3DProvider()
    if not tripo.is_configured():
        raise HTTPException(status_code=400, detail="Tripo3D API key is not configured. Add 'tripo3d_api_key' to config.json or use local Blender generation.")

    saved = load_saved_characters()
    char_info = next((c for c in saved if c.get("id") == char_id), None)
    if not char_info or not char_info.get("avatar_url"):
        raise HTTPException(status_code=400, detail="Character has no reference avatar photo.")

    raw_url = char_info["avatar_url"].lstrip("/")
    avatar_path = projects.BASE_DIR / raw_url
    if not avatar_path.exists():
        raise HTTPException(status_code=400, detail=f"Avatar photo not found at {avatar_path}")

    try:
        task_info = await tripo.generate_mesh(avatar_path, prompt=char_info.get("look", ""))
        return {"status": "QUEUED", "task": task_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/3d/tripo3d/task/{task_id}")
async def poll_tripo3d_task(task_id: str, char_id: str = ""):
    tripo = Tripo3DProvider()
    task = await tripo.poll_task(task_id)

    # If completed and char_id provided, download model to asset profile
    if task.get("status") == "SUCCESS" and task.get("model_url") and char_id:
        char_dir = character_3d_engine.get_character_asset_dir(char_id)
        mesh_path = char_dir / "mesh.glb"
        await tripo.download_asset(task["model_url"], mesh_path)
        prof = character_3d_engine.load_character_3d_profile(char_id)
        prof["status"] = "MESH_READY"
        prof["mesh_file"] = f"/characters/assets/{char_id}/mesh.glb"
        character_3d_engine.save_character_3d_profile(char_id, prof)

    return task

@app.post("/api/3d/characters/{char_id}/import-model")
async def import_character_model(
    char_id: str,
    file: UploadFile = File(...),
    is_rigged: bool = Form(False)
):
    char_dir = character_3d_engine.get_character_asset_dir(char_id)
    suffix = Path(file.filename or "model.glb").suffix.lower()
    
    if suffix in (".glb", ".gltf"):
        dest_name = "rigged.glb" if is_rigged else "mesh.glb"
    elif suffix == ".fbx":
        dest_name = "model.fbx"
    elif suffix == ".blend":
        dest_name = "character.blend"
    else:
        raise HTTPException(status_code=400, detail="Unsupported 3D file format. Use .glb, .fbx, or .blend.")

    dest_path = char_dir / dest_name
    content = await file.read()
    dest_path.write_bytes(content)

    prof = character_3d_engine.load_character_3d_profile(char_id)
    if dest_name == "character.blend":
        prof["status"] = "BLENDER_PROJECT_READY"
        prof["blend_file"] = f"/characters/assets/{char_id}/character.blend"
    elif is_rigged:
        prof["status"] = "RIGGED"
        prof["rigged_file"] = f"/characters/assets/{char_id}/rigged.glb"
    else:
        prof["status"] = "MESH_READY"
        prof["mesh_file"] = f"/characters/assets/{char_id}/mesh.glb"

    character_3d_engine.save_character_3d_profile(char_id, prof)
    return {"status": "SUCCESS", "imported_file": dest_name, "profile": prof}

@app.post("/api/3d/characters/{char_id}/create-blend")
async def create_character_blend(char_id: str):
    try:
        prof = await character_3d_engine.create_blender_project(char_id)
        return {"status": "SUCCESS", "profile": prof}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/3d/render-scene")
async def render_3d_character_scene(req: Render3DSceneRequest):
    char_dir = character_3d_engine.get_character_asset_dir(req.character_id)
    audio_path = None

    # Step 1: Voiceover & Speech Lip-Sync Audio Generation
    if req.dialogue.strip():
        renders_dir = char_dir / "renders"
        renders_dir.mkdir(parents=True, exist_ok=True)
        raw_audio = renders_dir / f"scene_{req.scene_id}_speech.wav"
        try:
            voice_id = req.voice if ":" in req.voice else f"{req.tts_engine}:{req.voice}"
            await tts_engine.generate_voiceover(
                text=req.dialogue.strip(),
                voice=voice_id,
                output_path=raw_audio,
                language=req.language
            )
            if raw_audio.exists():
                audio_path = raw_audio
                # Auto-calculate duration from generated audio
                dur = await asyncio.to_thread(ai_engine.get_audio_duration, raw_audio)
                if dur > 0.5:
                    req.duration = round(dur, 2)
        except Exception as e:
            logger.warning(f"Could not generate dialogue voiceover: {e}; rendering with silent animation")

    # Step 2: Deterministic 3D Blender Animation Rendering
    try:
        out_video = await character_3d_engine.render_scene_3d(
            char_id=req.character_id,
            scene_id=req.scene_id,
            animation=req.animation,
            camera_mode=req.camera_mode,
            lighting_preset=req.lighting_preset,
            audio_path=audio_path,
            duration=req.duration,
            aspect_ratio=req.aspect_ratio
        )
        video_url = f"/characters/assets/{req.character_id}/renders/{out_video.name}"
        return {
            "status": "DONE",
            "video_url": video_url,
            "scene_id": req.scene_id,
            "character_id": req.character_id,
            "duration": req.duration,
            "animation": req.animation,
            "camera_mode": req.camera_mode,
            "lighting_preset": req.lighting_preset
        }
    except Exception as e:
        logger.error(f"3D Scene render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/jobs", StaticFiles(directory=str(JOBS_DIR)), name="jobs")
app.mount("/characters", StaticFiles(directory=str(CHARACTERS_VAULT_DIR)), name="characters")
music_library.LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
app.mount(music_library.LIBRARY_URL, StaticFiles(directory=str(music_library.LIBRARY_DIR)), name="music-library")

UI_DIST = BASE_DIR / "ui" / "dist"
if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8700, reload=False)

