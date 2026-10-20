import asyncio
import json
import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
import httpx
from loguru import logger

BASE_DIR = Path(__file__).resolve().parent.parent
AI_ROOT = BASE_DIR.parent
IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

CONFIG_FILE = BASE_DIR / "backend" / "config.json"
if not CONFIG_FILE.exists():
    CONFIG_FILE = BASE_DIR / "config.json"

def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _setting(key: str, env_var: str, default: str) -> str:
    """Environment variable wins, then config.json, then the per-OS default."""
    return os.environ.get(env_var) or _load_config().get(key) or default

def _default_comfyui_dir() -> Path:
    if IS_WINDOWS:
        return AI_ROOT / "ComfyUI_windows_portable" / "ComfyUI"
    return AI_ROOT / "ComfyUI"

def _default_f5_python(comfy_dir: Path) -> Path:
    """F5-TTS runs in ComfyUI's Python environment, where torch is already installed."""
    candidates = [
        comfy_dir.parent / "python_embeded" / "python.exe",  # Windows portable build
        comfy_dir / ".venv" / "Scripts" / "python.exe",
        comfy_dir / "venv" / "Scripts" / "python.exe",
        comfy_dir / ".venv" / "bin" / "python",
        comfy_dir / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)

OLLAMA_URL = _setting("ollama_url", "VIDFORGE_OLLAMA_URL", "http://127.0.0.1:11434")
COMFYUI_URL = _setting("comfyui_url", "VIDFORGE_COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_DIR = Path(_setting("comfyui_dir", "VIDFORGE_COMFYUI_DIR", str(_default_comfyui_dir())))
COMFYUI_INPUT = COMFYUI_DIR / "input"
COMFYUI_OUTPUT = COMFYUI_DIR / "output"
FFMPEG = _setting("ffmpeg_path", "VIDFORGE_FFMPEG", "ffmpeg")
FFPROBE = _setting("ffprobe_path", "VIDFORGE_FFPROBE", "ffprobe")
VIDEO_ENCODER_SETTING = _setting("video_encoder", "VIDFORGE_VIDEO_ENCODER", "auto")

# Wan 2.1 14B ships as FP8 weights, which Apple's MPS backend cannot run
WAN_SUPPORTED = not IS_MACOS

_video_encoder: str | None = None

def _encoder_works(name: str) -> bool:
    # Builds can list nvenc without an NVIDIA GPU present, so test with a tiny real encode
    cmd = [
        FFMPEG, "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2",
        "-c:v", name, "-pix_fmt", "yuv420p", "-f", "null", "-"
    ]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0
    except Exception:
        return False

def get_video_encoder() -> str:
    """Picks the H.264 encoder once: NVENC (NVIDIA), VideoToolbox (macOS), else libx264 on the CPU."""
    global _video_encoder
    if _video_encoder:
        return _video_encoder
    if VIDEO_ENCODER_SETTING != "auto":
        _video_encoder = VIDEO_ENCODER_SETTING
    else:
        preferred = ["h264_videotoolbox"] if IS_MACOS else ["h264_nvenc"]
        _video_encoder = next((enc for enc in preferred if _encoder_works(enc)), "libx264")
    logger.info(f"Using video encoder: {_video_encoder}")
    return _video_encoder

def video_encoder_args(quality: int) -> list[str]:
    """Encoder flags at a comparable quality level (lower = better, CRF-style)."""
    enc = get_video_encoder()
    if enc == "h264_nvenc":
        return ["-c:v", enc, "-preset", "p5", "-cq", str(quality)]
    if enc == "h264_videotoolbox":
        return ["-c:v", enc, "-b:v", "12M"]
    if enc == "libx264":
        return ["-c:v", enc, "-preset", "medium", "-crf", str(quality)]
    return ["-c:v", enc]

WORKFLOWS_DIR = BASE_DIR / "workflows"

ASPECT_RESOLUTIONS = {
    "9:16": {"width": 768, "height": 1344, "render_w": 1080, "render_h": 1920, "wan_w": 480, "wan_h": 832},
    "16:9": {"width": 1344, "height": 768, "render_w": 1920, "render_h": 1080, "wan_w": 832, "wan_h": 480}
}

VIDEO_TYPES_CONFIG = {
    "story": {
        "name": "Cinematic Story & Folklore",
        "persona": "You are a master cinematic film director and historical storyteller.",
        "narration_guidelines": "Evocative, dramatic, emotionally moving storytelling with heroic and immersive depth.",
        "visual_guidelines": "Cinematic 8K film lighting, volumetric fog, historical authenticity, shallow depth of field, dramatic character close-ups.",
        "default_music": "cinematic_epic"
    },
    "news": {
        "name": "News Reporting & Journalism",
        "persona": "You are a seasoned executive news director and broadcast journalist.",
        "narration_guidelines": "Factual, crisp, authoritative, objective news reporting. Immediate headlines-first approach. Do NOT use fairy-tale language (never say 'Once upon a time' or 'একদা'). Speak directly with news gravity: 'আজকের প্রধান সংবাদ...', 'বিশেষ অনুসন্ধানী প্রতিবেদনে জানা গেছে...'.",
        "visual_guidelines": "Photorealistic television broadcast journalism, sleek modern studio desk, field reportage, on-the-scene news cameras, clean editorial lighting, 8k documentary capture.",
        "default_music": "cinematic_epic"
    },
    "presentation": {
        "name": "Project & Business Presentation",
        "persona": "You are a Silicon Valley tech executive, keynote presenter, and project architect.",
        "narration_guidelines": "Professional, articulate, compelling presentation pitch. Structure logically: Executive Problem Statement, The Technological Innovation & Architecture, Key Features & Capabilities, Business Impact & Future Vision. Confident, modern, and clear.",
        "visual_guidelines": "Ultra-modern enterprise tech visuals, sleek 3D dashboard interfaces, futuristic engineering schematics, minimalist glassmorphism product design, executive keynote aesthetic.",
        "default_music": "emotional_drama"
    },
    "explainer": {
        "name": "Educational Explainer & Tech Breakdown",
        "persona": "You are an award-winning science and technology educator and documentary host.",
        "narration_guidelines": "Clear, engaging, educational breakdown. Demystify complex ideas with intuitive explanations ('কীভাবে এটি কাজ করে...', 'এর পেছনের মূল কারণ...'). Insightful and easy to follow.",
        "visual_guidelines": "Crystal-clear informational visuals, conceptual diagrams, realistic educational environments, crisp visual storytelling.",
        "default_music": "ancient_history"
    },
    "commercial": {
        "name": "Product Showcase & Commercial Promo",
        "persona": "You are an elite creative director for luxury and innovative tech brand commercials.",
        "narration_guidelines": "Dynamic, high-energy, value-driven commercial hook. Highlight key benefits, evoke desire, and end with an inspiring call to action.",
        "visual_guidelines": "High-end studio commercial lighting, sleek product renders, glossy 4k macro details, vibrant aesthetic reflections.",
        "default_music": "cinematic_epic"
    },
    "reel": {
        "name": "Social Media Viral Short / Reel",
        "persona": "You are a top viral short-form video creator and audience retention specialist.",
        "narration_guidelines": "High-retention 3-second hook, fast-moving curiosity loops, punchy, concise sentences that keep viewers glued to the screen until the end.",
        "visual_guidelines": "Bold saturated colors, eye-catching composition optimized for mobile vertical 9:16 viewing, dynamic focal elements.",
        "default_music": "cinematic_epic"
    },
    "documentary": {
        "name": "Nature & World Documentary",
        "persona": "You are an acclaimed documentary filmmaker and wildlife narrator.",
        "narration_guidelines": "Calm, awe-inspiring, observational documentary narration. Reveal fascinating facts gradually, build a sense of wonder, and keep a measured, respectful tone throughout.",
        "visual_guidelines": "Sweeping aerial landscapes, telephoto wildlife photography, golden-hour natural light, rich textures, National Geographic style realism.",
        "default_music": "emotional_drama"
    },
    "biography": {
        "name": "Biography & Life Story",
        "persona": "You are a renowned biographer and historical portrait filmmaker.",
        "narration_guidelines": "Chronological life story: early life, struggles, turning point, greatest achievements and legacy. Human, respectful and inspiring, with key dates and concrete details.",
        "visual_guidelines": "Period-accurate portraits and settings, warm archival film grain, intimate character close-ups, era-specific costumes and architecture.",
        "default_music": "ancient_history"
    },
    "motivational": {
        "name": "Motivational & Self-Improvement",
        "persona": "You are a world-class motivational speaker and life coach.",
        "narration_guidelines": "Powerful, uplifting, second-person speech ('আপনি পারবেন...'). Open with a relatable struggle, build intensity, share one clear lesson and end with a strong, actionable call to rise.",
        "visual_guidelines": "Silhouettes at sunrise, mountain summits, athletes in training, dramatic rim lighting, high-contrast cinematic grading.",
        "default_music": "cinematic_epic"
    },
    "travel": {
        "name": "Travel & Destination Guide",
        "persona": "You are an enthusiastic travel filmmaker and destination guide host.",
        "narration_guidelines": "Vivid, inviting travel narration. Describe the place's character, history, food, culture and must-see spots, with practical tips. Make the viewer want to go there.",
        "visual_guidelines": "Stunning destination cinematography, bustling local markets, landmark wide shots, vibrant street life, warm travel-vlog color grading.",
        "default_music": "emotional_drama"
    },
    "kids": {
        "name": "Kids Story & Moral Tale",
        "persona": "You are a beloved children's storyteller and animated film writer.",
        "narration_guidelines": "Simple, warm, playful language for young children. Gentle adventure with friendly characters, clear and kind emotions, and a clear moral lesson at the end. Nothing frightening or violent.",
        "visual_guidelines": "Bright colorful 3D animated storybook style, soft rounded characters, cheerful lighting, Pixar-like friendly environments.",
        "default_music": "emotional_drama"
    },
    "mystery": {
        "name": "Mystery & Unsolved Cases",
        "persona": "You are a gripping mystery storyteller and investigative documentary host.",
        "narration_guidelines": "Suspenseful, slow-burn narration. Open with an intriguing question, reveal clues one by one, present theories fairly, and end with a haunting open question. No graphic gore.",
        "visual_guidelines": "Moody low-key lighting, fog and shadows, abandoned locations, old documents and clues on a desk, desaturated noir color grading.",
        "default_music": "ancient_history"
    }
}

# Engine-neutral performance cues the script writer may use; tts_engine renders them per engine
PERFORMANCE_CUES = ["[whispers]", "[softly]", "[excited]", "[sad]", "[sighs]", "[laughs]", "[gasps]", "[short pause]", "[long pause]"]

def calculate_duration_profile(target_duration: int = 60) -> tuple[int, int, int]:
    """Calculates (scene_count, words_target, words_per_scene) for modern high-retention video (cut every 4-6s)"""
    target_sec = max(15, min(600, int(target_duration or 60)))
    
    # Modern audience retention: Scene cut every 4.5 to 5.5 seconds (prevents boredom)
    sec_per_scene = 5.2
    scene_count = max(3, min(36, int(round(target_sec / sec_per_scene))))
    
    # Average speech: 1.95 - 2.0 words per second, leaving ~0.6s of breathing room after each scene
    words_target = int(max(10, target_sec - scene_count * 0.6) * 2.0)
    words_per_scene = max(8, int(round(words_target / scene_count)))
    return scene_count, words_target, words_per_scene

async def free_gpu_memory(unload_comfy: bool = True, unload_ollama: bool = False):
    """Proactively frees VRAM from ComfyUI and/or Ollama to prevent CUDA out-of-memory errors."""
    if unload_comfy:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                await client.post(f"{COMFYUI_URL}/free", json={"unload_models": True, "free_memory": True})
                logger.info("Proactively freed ComfyUI VRAM cache")
        except Exception:
            pass
    if unload_ollama:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{OLLAMA_URL}/api/tags")
                if r.status_code == 200:
                    installed = [m["name"] for m in r.json().get("models", [])]
                    for m in installed:
                        try:
                            await client.post(f"{OLLAMA_URL}/api/chat", json={"model": m, "messages": [], "keep_alive": 0})
                        except Exception:
                            pass
                    logger.info("Unloaded idle Ollama models from VRAM")
        except Exception:
            pass

def parse_ollama_json(raw_text: str) -> dict:
    """Robust JSON parser that strips markdown code blocks and extracts root object."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx + 1]
    return json.loads(text)

async def generate_story_script(
    topic: str,
    language: str = "bn",
    model: str = "qwen3.5:9b",
    genre: str = "historical",
    tone: str = "epic",
    scene_count: int | None = None,
    video_type: str = "story",
    target_duration: int = 60
) -> dict:
    """Uses Ollama to generate a structured storyboard script with dynamic high-retention visual cuts"""
    lang_names = {
        "bn": "Bengali (বাংলা)",
        "hi": "Hindi (हिन्दी)",
        "en": "English"
    }
    target_lang = lang_names.get(language, "Bengali (বাংলা)")
    cfg = VIDEO_TYPES_CONFIG.get(video_type, VIDEO_TYPES_CONFIG["story"])

    computed_scenes, words_target, words_per_scene = calculate_duration_profile(target_duration)
    final_scene_count = scene_count if (scene_count and scene_count > 0) else computed_scenes
    
    system_prompt = f"""{cfg['persona']}
Generate a complete, professional, highly engaging video production script with EXACTLY {final_scene_count} chronological scenes based on the user's prompt.
Production Format: {cfg['name']}
Target Total Video Duration: Approximately {target_duration} seconds (~{target_duration // 60}m {target_duration % 60}s).

Strict Timing & High-Retention Pacing Rules:
- You MUST generate EXACTLY {final_scene_count} chronological scenes.
- Visual Pacing: Each scene MUST cut/transition quickly (every ~4 to 6 seconds) to maintain viewer retention and avoid boredom.
- Narration Length: Each scene's spoken voiceover contains approximately {words_per_scene} words (1-3 short, natural sentences in {target_lang}).
- Total Spoken Words: The total narration across all {final_scene_count} scenes MUST be approximately {words_target} words so the spoken voiceover matches ~{target_duration}s.

Voice Performance Rules (the narration is performed by an expressive human-like voice actor):
- Write the narration as ONE continuous performance: each scene must flow naturally from the previous one, following an emotional arc (build tension, release it, contrast quiet and powerful moments).
- Use natural punctuation for rhythm: commas, "…" for a lingering pause, "—" for a sudden break.
- You MAY insert performance cues inside the narration, written in English square brackets, ONLY from this list: {', '.join(PERFORMANCE_CUES)}. Use 0-2 cues per scene, only where a real narrator would change delivery. Never put any other words in square brackets.

Requirements for each scene:
1. "narration": Spoken voiceover STRICTLY in {target_lang} (~{words_per_scene} words, cues not counted).
   Format Guidelines: {cfg['narration_guidelines']}
2. "delivery": 2-6 English words telling the voice actor HOW to speak this scene: emotion, volume and pace (e.g. "hushed, slow, suspenseful", "rising, proud, powerful", "soft, tender, intimate").
3. "pause_after": Seconds of silence after this scene: 0.3 for quick flow, 0.6 normally, 1.0-1.5 before a dramatic turn and after the final scene.
4. "visual_prompt": A unique, distinct visual description written in English for 8K photorealistic image generation (ComfyUI Z-Image-Turbo). Vary camera angles, subjects, macro details, and perspectives between scenes!
   Visual Guidelines: {cfg['visual_guidelines']}
5. "motion_prompt": A camera motion description in English for smooth Ken Burns cinematic panning/zooming (e.g. "slow cinematic push in", "gentle pan right", "dynamic zoom out", "tilt up").

Respond ONLY with valid JSON in this exact structure:
{{
  "title": "Clear Gripping Title",
  "synopsis": "1-2 sentence overview of the video content",
  "narrator_style": "3-8 English words describing the narrator's overall voice persona (e.g. warm, intimate documentary storyteller)",
  "scenes": [
    {{
      "id": 1,
      "narration": "Voiceover in {target_lang} (~{words_per_scene} words), optionally with cues like [short pause]",
      "delivery": "How to speak it, in English",
      "pause_after": 0.6,
      "visual_prompt": "Visual description in English",
      "motion_prompt": "Camera motion in English"
    }}
  ]
}}"""

    # Free ComfyUI VRAM first so Ollama has full GPU headroom
    await free_gpu_memory(unload_comfy=True, unload_ollama=False)

    # Determine candidate models to try in order (requested model first, then others)
    candidate_models = [model] if model else []
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                installed = [m["name"] for m in r.json().get("models", [])]
                for m in ["qwen3.5:9b", "story-writer:latest"] + installed:
                    if m in installed and m not in candidate_models:
                        candidate_models.append(m)
    except Exception:
        pass

    if not candidate_models:
        candidate_models = ["qwen3.5:9b", "story-writer:latest"]

    last_error = None
    for candidate in candidate_models:
        try:
            logger.info(f"Generating story script with Ollama model: {candidate}...")
            async with httpx.AsyncClient(timeout=240.0) as client:
                payload = {
                    "model": candidate,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Topic / Concept:\n{topic}"}
                    ],
                    "stream": False,
                    "format": "json",
                    "keep_alive": "30s"
                }
                res = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
                if res.status_code != 200:
                    err_detail = res.text
                    try:
                        err_detail = res.json().get("error", res.text)
                    except Exception:
                        pass
                    logger.warning(f"Ollama model '{candidate}' returned HTTP {res.status_code}: {err_detail}")
                    # Free memory aggressively before trying next candidate
                    await free_gpu_memory(unload_comfy=True, unload_ollama=True)
                    last_error = RuntimeError(f"Ollama error ({candidate}): {err_detail}")
                    continue

                content = res.json()["message"]["content"]
                result = parse_ollama_json(content)
                logger.info(f"Successfully generated script with {candidate} ({len(result.get('scenes', []))} scenes)")
                # Proactively unload Ollama model so 100% of GPU is ready for ComfyUI / F5-TTS
                await free_gpu_memory(unload_comfy=False, unload_ollama=True)
                return result
        except Exception as e:
            logger.warning(f"Failed generation with candidate {candidate}: {e}")
            last_error = e
            await free_gpu_memory(unload_comfy=True, unload_ollama=True)

    raise RuntimeError(f"Ollama script generation failed: {last_error}")

async def get_active_ollama_model() -> str:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if "qwen3.5:9b" in models:
                    return "qwen3.5:9b"
                if "story-writer:latest" in models:
                    return "story-writer:latest"
                if models:
                    return models[0]
    except Exception:
        pass
    return "qwen3.5:9b"

async def plan_script(prompt: str, language: str, video_type: str = "story", target_duration: int = 60, model: str = None) -> dict:
    if not model:
        model = await get_active_ollama_model()
    return await generate_story_script(
        topic=prompt,
        language=language,
        model=model,
        video_type=video_type,
        target_duration=target_duration
    )

async def plan_story(prompt: str, language: str, model: str = None) -> dict:
    return await plan_script(prompt, language, video_type="story", target_duration=60, model=model)

def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        FFPROBE, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def pad_audio_with_silence(audio_path: Path, seconds: float) -> Path:
    """Appends a breathing pause so consecutive scenes don't run into each other."""
    if seconds <= 0:
        return audio_path
    tmp = audio_path.with_name(f"{audio_path.stem}_padded{audio_path.suffix}")
    cmd = [FFMPEG, "-y", "-i", str(audio_path), "-af", f"apad=pad_dur={seconds:.2f}", str(tmp)]
    subprocess.run(cmd, check=True, capture_output=True)
    os.replace(tmp, audio_path)
    return audio_path

async def generate_scene_image(visual_prompt: str, aspect: str, output_path: Path) -> Path:
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    wf_path = BASE_DIR / "z_image_turbo_text_to_image_api.json"
    if not wf_path.exists():
        wf_path = BASE_DIR / "workflows" / "z_image_turbo_text_to_image_api.json"
    
    wf = json.loads(wf_path.read_text(encoding="utf-8"))

    for node in wf.values():
        title = node.get("_meta", {}).get("title")
        if title == "VF_PROMPT":
            node["inputs"]["text"] = visual_prompt
        elif title == "VF_LATENT":
            node["inputs"]["width"] = dims["width"]
            node["inputs"]["height"] = dims["height"]
        elif title == "VF_SAMPLER":
            node["inputs"]["seed"] = random.randint(1, 2**31 - 1)

    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(f"{COMFYUI_URL}/prompt", json={"prompt": wf})
        r.raise_for_status()
        prompt_id = r.json()["prompt_id"]

        t0 = time.time()
        while time.time() - t0 < 300:
            hist_res = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            hist = hist_res.json()
            if prompt_id in hist:
                status = hist[prompt_id].get("status", {})
                if status.get("status_str") == "error":
                    raise RuntimeError(f"ComfyUI Image Error: {status}")
                if status.get("completed"):
                    outputs = hist[prompt_id]["outputs"]
                    for out in outputs.values():
                        if "images" in out and len(out["images"]) > 0:
                            img_info = out["images"][0]
                            img_data = (await client.get(
                                f"{COMFYUI_URL}/view",
                                params={"filename": img_info["filename"], "subfolder": img_info.get("subfolder", ""), "type": "output"}
                            )).content
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_bytes(img_data)
                            return output_path
            await asyncio.sleep(1.5)

    raise TimeoutError("ComfyUI Image generation timed out")

async def animate_scene_wan(image_path: Path, motion_prompt: str, aspect: str, raw_clip_path: Path) -> bool:
    """Invokes Wan 2.1 I2V in ComfyUI to animate the character/scene"""
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    
    # 1. Place input image into ComfyUI input folder
    COMFYUI_INPUT.mkdir(parents=True, exist_ok=True)
    input_filename = f"wan_in_{image_path.stem}.png"
    dest_input = COMFYUI_INPUT / input_filename
    shutil.copy(image_path, dest_input)

    prefix = f"wan_{image_path.stem}"

    # Wan 2.1 I2V API workflow
    wan_prompt = {
        "37": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors",
                "weight_dtype": "default"
            }
        },
        "38": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "wan",
                "device": "default"
            }
        },
        "39": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "wan_2.1_vae.safetensors"
            }
        },
        "49": {
            "class_type": "CLIPVisionLoader",
            "inputs": {
                "clip_name": "clip_vision_h.safetensors"
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["38", 0],
                "text": f"{motion_prompt}, cinematic motion, photorealistic, fluid natural movement, dynamic studio lighting, highly detailed"
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["38", 0],
                "text": "blurry, static, distorted, artifacts, low quality, jittery, disfigured, deformed, noisy"
            }
        },
        "54": {
            "class_type": "ModelSamplingSD3",
            "inputs": {
                "model": ["37", 0],
                "shift": 8.0
            }
        },
        "52": {
            "class_type": "LoadImage",
            "inputs": {
                "image": input_filename
            }
        },
        "51": {
            "class_type": "CLIPVisionEncode",
            "inputs": {
                "clip_vision": ["49", 0],
                "image": ["52", 0],
                "crop": "center"
            }
        },
        "50": {
            "class_type": "WanImageToVideo",
            "inputs": {
                "positive": ["6", 0],
                "negative": ["7", 0],
                "vae": ["39", 0],
                "clip_vision_output": ["51", 0],
                "start_image": ["52", 0],
                "width": dims["wan_w"],
                "height": dims["wan_h"],
                "length": 33, # 33 frames (4n+1) at 16fps = 2.06s smooth base motion
                "batch_size": 1
            }
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["54", 0],
                "positive": ["50", 0],
                "negative": ["50", 1],
                "latent_image": ["50", 2],
                "seed": random.randint(1, 2**31 - 1),
                "steps": 20, # 20 steps with uni_pc gives sharp, artifact-free diffusion
                "cfg": 5.0,
                "sampler_name": "uni_pc",
                "scheduler": "simple",
                "denoise": 1.0
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["39", 0]
            }
        },
        "55": {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["8", 0],
                "fps": 16.0
            }
        },
        "56": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["55", 0],
                "filename_prefix": f"video/{prefix}",
                "format": "auto",
                "codec": "auto"
            }
        }
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(f"{COMFYUI_URL}/prompt", json={"prompt": wan_prompt})
            r.raise_for_status()
            prompt_id = r.json()["prompt_id"]

            t0 = time.time()
            while time.time() - t0 < 240:
                hist_res = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
                hist = hist_res.json()
                if prompt_id in hist:
                    status = hist[prompt_id].get("status", {})
                    if status.get("status_str") == "error":
                        logger.warning(f"Wan 2.1 ComfyUI error: {status}")
                        return False
                    if status.get("completed"):
                        outputs = hist[prompt_id].get("outputs", {})
                        # Node 56 is SaveVideo
                        save_node = outputs.get("56", {})
                        video_list = save_node.get("images", []) or save_node.get("videos", [])
                        if video_list:
                            vid_info = video_list[0]
                            # Try downloading from view API
                            vid_resp = await client.get(
                                f"{COMFYUI_URL}/view",
                                params={"filename": vid_info["filename"], "subfolder": vid_info.get("subfolder", "video"), "type": "output"}
                            )
                            if vid_resp.status_code == 200:
                                raw_clip_path.write_bytes(vid_resp.content)
                                logger.info(f"Wan 2.1 video generated: {raw_clip_path}")
                                return True
                            # Or read directly from ComfyUI output
                            disk_file = COMFYUI_OUTPUT / vid_info.get("subfolder", "video") / vid_info["filename"]
                            if disk_file.exists():
                                shutil.copy(disk_file, raw_clip_path)
                                return True
                await asyncio.sleep(2.0)
    except Exception as e:
        logger.warning(f"Wan 2.1 animation failed or timed out: {e}")
        return False

    return False

def extend_video_to_duration(raw_video: Path, target_duration: float, aspect: str, final_video: Path):
    """Seamlessly loops the AI motion clip using forward-reverse ping-pong so character motion never cuts abruptly"""
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    rw, rh = dims["render_w"], dims["render_h"]

    # Filter: ping-pong loop (forward + reverse) repeated to cover target_duration, scaled to output resolution
    filter_str = (
        f"[0:v]scale={rw}:{rh}:force_original_aspect_ratio=increase,crop={rw}:{rh},"
        f"split=2[fwd][rev_in];"
        f"[rev_in]reverse[rev];"
        f"[fwd][rev]concat=n=2:v=1[pingpong];"
        f"[pingpong]loop=loop=-1:size=200[vloop]"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", str(raw_video),
        "-filter_complex", filter_str,
        "-map", "[vloop]",
        "-t", f"{target_duration:.2f}",
        *video_encoder_args(20), "-pix_fmt", "yuv420p",
        str(final_video)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return final_video

def create_fallback_motion_clip(image_path: Path, duration: float, aspect: str, output_path: Path, motion_type: str = "zoom_in") -> Path:
    """High-quality Ken Burns camera motion with multi-axis movements, pristine 2X upscale headroom, and smooth fade transitions"""
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    rw, rh = dims["render_w"], dims["render_h"]
    fps = 30
    total_frames = max(30, int(duration * fps))

    # High quality upscale for zoompan headroom
    scale_w = rw * 2
    scale_h = rh * 2

    # Smooth Ken Burns camera movements
    if motion_type == "zoom_in":
        # Slow cinematic zoom in from 1.0 to 1.15
        vf = f"scale={scale_w}:{scale_h},zoompan=z='min(zoom+0.0008,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    elif motion_type == "zoom_out":
        # Slow cinematic zoom out from 1.15 to 1.0
        vf = f"scale={scale_w}:{scale_h},zoompan=z='if(lte(zoom,1.0),1.15,max(1.001,zoom-0.0008))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    elif motion_type == "pan_right":
        # Gentle pan from left to right with slight 1.10 zoom
        vf = f"scale={scale_w}:{scale_h},zoompan=z='1.10':x='(it/{duration})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    elif motion_type == "pan_left":
        # Gentle pan from right to left with slight 1.10 zoom
        vf = f"scale={scale_w}:{scale_h},zoompan=z='1.10':x='(1-it/{duration})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    elif motion_type == "tilt_up":
        # Gentle tilt from bottom to top with slight 1.08 zoom
        vf = f"scale={scale_w}:{scale_h},zoompan=z='1.08':x='iw/2-(iw/zoom/2)':y='(1-it/{duration})*(ih-ih/zoom)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    else: # static_subtle / clean presentation
        # Subtle breathe zoom (1.0 to 1.04)
        vf = f"scale={scale_w}:{scale_h},zoompan=z='min(zoom+0.0003,1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"

    # Soft cinematic dissolve/fade transition at clip boundaries (0.35s in, 0.35s out)
    fade_d = min(0.35, duration / 4)
    fade_out_st = max(0.1, duration - fade_d)
    vf += f",fade=t=in:st=0:d={fade_d:.2f},fade=t=out:st={fade_out_st:.2f}:d={fade_d:.2f}"

    cmd = [
        FFMPEG, "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf,
        "-t", f"{duration:.2f}",
        *video_encoder_args(18), "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path

async def animate_scene(image_path: Path, motion_prompt: str, duration: float, aspect: str, output_path: Path, fallback_idx: int = 0, motion_mode: str = "kenburns") -> Path:
    """Full animation controller: supports Ken Burns (Ultra HD), Wan 2.1 AI Motion, and Clean Presentation"""
    mtypes = ["zoom_in", "pan_right", "zoom_out", "tilt_up", "pan_left"]
    chosen_motion = mtypes[fallback_idx % len(mtypes)] if motion_mode != "static" else "static_subtle"

    if motion_mode == "wan" and not WAN_SUPPORTED:
        logger.info(f"Wan 2.1 is not supported on {sys.platform}; using Ken Burns ({chosen_motion})")
    elif motion_mode == "wan":
        raw_wan = output_path.parent / f"raw_wan_{output_path.stem}.mp4"
        success = await animate_scene_wan(image_path, motion_prompt, aspect, raw_wan)
        if success and raw_wan.exists() and raw_wan.stat().st_size > 1000:
            logger.info(f"Applying seamless ping-pong loop to Wan 2.1 clip for duration {duration:.2f}s...")
            await asyncio.to_thread(extend_video_to_duration, raw_wan, duration, aspect, output_path)
            return output_path
        logger.info(f"Wan 2.1 unavailable or timed out; falling back to Ken Burns ({chosen_motion})")

    # Ultra HD Ken Burns camera motion (recommended, 100% distortion-free)
    # FFmpeg runs in a thread so the API stays responsive while it renders
    logger.info(f"Rendering Ken Burns motion ({chosen_motion}) with smooth fade transitions for {output_path.name}")
    await asyncio.to_thread(create_fallback_motion_clip, image_path, duration, aspect, output_path, motion_type=chosen_motion)
    return output_path

# Auto-balance targets: narration sits at a standard speech loudness and the music bed
# ~14 LU below it, so speech stays clear before any ducking is applied.
VOICE_TARGET_LUFS = -16
MUSIC_TARGET_LUFS = -30


def _gain(percent: int) -> float:
    """UI level (100 = auto-balanced) -> linear gain, clamped to 0–200%."""
    return max(0, min(200, int(percent))) / 100


def assemble_final_video(
    scene_videos: list[Path],
    scene_audios: list[Path],
    output_path: Path,
    aspect: str,
    music_file: Path | None = None,
    music_volume: int = 100,
    voice_volume: int = 100,
    music_ducking: bool = True,
) -> Path:
    """Concatenates scene clips and the voiceover, optionally mixing in a background music bed.

    Voice and music are loudness-normalised first (auto balance); music_volume / voice_volume
    then adjust each relative to that balance. With ducking on, the music dips further while
    the narrator speaks.
    """
    job_dir = output_path.parent
    concat_file = job_dir / "concat_list.txt"
    with open(concat_file, "w", encoding="utf-8") as f:
        for v in scene_videos:
            f.write(f"file '{v.as_posix()}'\n")

    audio_concat = job_dir / "audio_concat.txt"
    with open(audio_concat, "w", encoding="utf-8") as f:
        for a in scene_audios:
            f.write(f"file '{a.as_posix()}'\n")

    full_video = job_dir / "combined_video.mp4"
    full_voice = job_dir / "combined_voice.wav"

    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(full_video)], check=True, capture_output=True)
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(audio_concat), "-c:a", "pcm_s16le", str(full_voice)], check=True, capture_output=True)

    voice_chain = (
        f"aresample=48000,loudnorm=I={VOICE_TARGET_LUFS}:TP=-1.5:LRA=11,aresample=48000,"
        f"volume={_gain(voice_volume):.2f}"
    )
    use_music = music_file is not None and music_file.exists() and _gain(music_volume) > 0

    if use_music:
        total_dur = get_audio_duration(full_voice)
        fade_out = min(3.0, max(0.5, total_dur / 4))
        fade_out_start = max(0.0, total_dur - fade_out)
        logger.info(
            f"Mixing background music: {music_file.name} (music {music_volume}%, voice {voice_volume}%, ducking {'on' if music_ducking else 'off'})"
        )
        # [1:a] voice, [2:a] music looped to cover the whole narration
        music_chain = (
            f"[2:a]aresample=48000,loudnorm=I={MUSIC_TARGET_LUFS}:TP=-8:LRA=11,aresample=48000,"
            f"volume={_gain(music_volume):.2f},"
            f"afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f}[bg];"
        )
        if music_ducking:
            filter_complex = (
                f"[1:a]{voice_chain},asplit=2[voice][sc];"
                + music_chain
                + "[bg][sc]sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350[bed];"
            )
        else:
            filter_complex = f"[1:a]{voice_chain}[voice];" + music_chain + "[bg]anull[bed];"
        # normalize=0 keeps the balanced levels; the limiter guards against clipping
        filter_complex += "[voice][bed]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[aout]"

        cmd = [
            FFMPEG, "-y",
            "-i", str(full_video),
            "-i", str(full_voice),
            "-stream_loop", "-1", "-i", str(music_file),
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
    else:
        cmd = [
            FFMPEG, "-y",
            "-i", str(full_video),
            "-i", str(full_voice),
            "-filter_complex", f"[1:a]{voice_chain},alimiter=limit=0.95[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
    subprocess.run(cmd, check=True, capture_output=True)

    return output_path
