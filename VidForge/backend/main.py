import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from database import init_db, add_job, get_all_jobs, get_job, delete_job
from worker import worker_loop
import ai_engine

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
    voice: str = "bn-BD-PradeepNeural"
    tts_engine: str = "edge"
    ref_audio: str = ""
    ref_text: str = ""
    aspect_ratio: str = "9:16"
    title: str = ""
    scenes: list[dict] | None = None

class TTSConfigRequest(BaseModel):
    elevenlabs_api_key: str | None = None
    default_engine: str | None = None

class TestElevenKeyRequest(BaseModel):
    api_key: str

class GenerateStoryRequest(BaseModel):
    topic: str
    model: str = "story-writer:latest"
    language: str = "bn"
    genre: str = "historical"
    tone: str = "epic"
    scene_count: int = 5

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
    default_model = "story-writer:latest"
    comfyui_ok = False

    async with httpx.AsyncClient(timeout=3.0) as client:
        # Check Ollama
        try:
            r = await client.get(f"{ai_engine.OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                ollama_ok = True
                data = r.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
                if "story-writer:latest" in ollama_models:
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
        "comfyui_online": comfyui_ok
    }

@app.get("/api/tts/engines")
def get_tts_engines():
    return ai_engine.get_all_tts_engines()

@app.get("/api/tts/config")
def get_tts_config_api():
    cfg = ai_engine.get_tts_config()
    key = cfg.get("elevenlabs_api_key", "")
    masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else ("***" if key else "")
    return {
        "has_elevenlabs_key": bool(key),
        "masked_key": masked,
        "default_engine": cfg.get("default_engine", "edge")
    }

@app.post("/api/tts/config")
def set_tts_config_api(req: TTSConfigRequest):
    update_data = {}
    if req.elevenlabs_api_key is not None:
        update_data["elevenlabs_api_key"] = req.elevenlabs_api_key.strip()
    if req.default_engine is not None:
        update_data["default_engine"] = req.default_engine.strip()
    saved = ai_engine.save_tts_config(update_data)
    return {"ok": True, "has_elevenlabs_key": bool(saved.get("elevenlabs_api_key"))}

@app.post("/api/tts/test_key")
async def test_elevenlabs_key(req: TestElevenKeyRequest):
    key = req.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key is required")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": key})
            if res.status_code == 200:
                data = res.json()
                tier = data.get("tier", "unknown")
                char_count = data.get("character_count", 0)
                char_limit = data.get("character_limit", 0)
                return {
                    "valid": True,
                    "tier": tier,
                    "character_count": char_count,
                    "character_limit": char_limit,
                    "message": f"Valid ({tier} tier, {char_count:,} / {char_limit:,} chars used)"
                }
            else:
                return {"valid": False, "message": f"Verification failed (HTTP {res.status_code})"}
    except Exception as e:
        return {"valid": False, "message": f"Connection error: {str(e)}"}

@app.get("/api/voices")
def get_voices():
    return ai_engine.VOICES

@app.get("/api/voices/preview")
async def get_voice_preview(
    voice: str,
    engine: str = "edge",
    ref_audio: str = "",
    ref_text: str = ""
):
    if not voice:
        raise HTTPException(status_code=400, detail="Voice is required")
    try:
        url = await ai_engine.generate_voice_sample(
            voice=voice,
            engine=engine,
            ref_audio=ref_audio,
            ref_text=ref_text
        )
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            scene_count=req.scene_count
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
        async with httpx.AsyncClient(timeout=180.0) as client:
            payload = {
                "model": req.model,
                "messages": ollama_messages,
                "stream": False
            }
            res = await client.post(f"{ai_engine.OLLAMA_URL}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()
            return {
                "message": data["message"]["content"],
                "model": data.get("model", req.model)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama chat error: {str(e)}")

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
    voice_identifier = req.voice
    if req.tts_engine == "elevenlabs" and not voice_identifier.startswith("elevenlabs:"):
        voice_identifier = f"elevenlabs:{voice_identifier}"
    elif req.tts_engine in ("f5tts", "f5-tts") and not voice_identifier.startswith("f5:"):
        voice_identifier = f"f5:{voice_identifier}"
    elif req.tts_engine == "edge" and not (":" in voice_identifier):
        voice_identifier = f"edge:{voice_identifier}"

    add_job(
        job_id=job_id,
        title=title,
        story_prompt=req.story_prompt,
        language=req.language,
        voice=voice_identifier,
        aspect_ratio=req.aspect_ratio,
        scenes_json=scenes_json
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

UI_DIST = BASE_DIR / "ui" / "dist"
if UI_DIST.exists():
    app.mount("/", StaticFiles(directory=str(UI_DIST), html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8700, reload=False)

