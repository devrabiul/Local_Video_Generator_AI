import asyncio
import json
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
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

class TTSConfigRequest(BaseModel):
    elevenlabs_api_key: str | None = None
    gemini_api_key: str | None = None
    default_engine: str | None = None

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

@app.get("/api/system/status")
async def get_system_status():
    ollama_ok = False
    ollama_models = []
    default_model = "qwen3.5:9b"
    comfyui_ok = False

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
        except Exception:
            comfyui_ok = False

    return {
        "ollama_online": ollama_ok,
        "models": ollama_models,
        "default_model": default_model,
        "comfyui_online": comfyui_ok,
        "platform": sys.platform,
        "wan_available": ai_engine.WAN_SUPPORTED,
        "video_encoder": await asyncio.to_thread(ai_engine.get_video_encoder)
    }

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
        "default_engine": cfg["default_engine"]
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
async def get_voice_preview(voice: str, engine: str = "gemini", language: str = "bn"):
    if not voice:
        raise HTTPException(status_code=400, detail="Voice is required")
    try:
        url = await tts_engine.generate_voice_sample(voice=voice, engine=engine, language=language)
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
        music_ducking=req.music_ducking
    )
    return {"id": job_id, "status": "QUEUED"}

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
def download_project_file(job_id: str, kind: Literal["video", "thumbnail"]):
    job = _project_or_404(job_id)
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

app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
app.mount("/jobs", StaticFiles(directory=str(JOBS_DIR)), name="jobs")
music_library.LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
app.mount(music_library.LIBRARY_URL, StaticFiles(directory=str(music_library.LIBRARY_DIR)), name="music-library")

UI_DIST = BASE_DIR / "ui" / "dist"
if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8700, reload=False)

