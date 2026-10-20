import asyncio
import json
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from database import init_db, add_job, get_all_jobs, get_job, delete_job
from worker import worker_loop
import ai_engine
import music_library
import tts_engine

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
JOBS_DIR = BASE_DIR / "jobs"
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

@app.delete("/api/jobs/{job_id}")
def remove_job(job_id: str):
    delete_job(job_id)
    return {"ok": True}

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

