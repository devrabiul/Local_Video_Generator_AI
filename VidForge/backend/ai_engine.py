import asyncio
import base64
import hashlib
import json
import os
import random
import re
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

def video_encoder_args(quality: int, size: tuple[int, int] = (1080, 1920), fps: int = 30) -> list[str]:
    """Encoder flags at a comparable quality level (lower = better, CRF-style).

    VideoToolbox has no CRF mode, so its bitrate scales with pixels per second
    (12 Mbps at 1080p30, ~43 Mbps at 1440p60, never below 4 Mbps).
    """
    enc = get_video_encoder()
    if enc == "h264_nvenc":
        return ["-c:v", enc, "-preset", "p5", "-cq", str(quality)]
    if enc == "h264_videotoolbox":
        mbps = max(4, round(12 * (size[0] * size[1] * fps) / (1080 * 1920 * 30)))
        return ["-c:v", enc, "-b:v", f"{mbps}M"]
    if enc == "libx264":
        return ["-c:v", enc, "-preset", "medium", "-crf", str(quality)]
    return ["-c:v", enc]

WORKFLOWS_DIR = BASE_DIR / "workflows"

# Output resolutions (the short side) and frame rates offered in the UI
RESOLUTIONS = (480, 720, 1080, 1440)
FPS_OPTIONS = (24, 25, 30, 60)


def render_size(aspect: str, resolution: int = 1080) -> tuple[int, int]:
    """(width, height) of the final video: 9:16 → 1080x1920, 16:9 → 1920x1080, etc. Always even."""
    short = resolution if resolution in RESOLUTIONS else 1080
    long = int(round(short * 16 / 9 / 2)) * 2  # 480 → 854, 720 → 1280, 1080 → 1920, 1440 → 2560
    return (short, long) if aspect == "9:16" else (long, short)

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
    "animation": {
        "name": "3D Animated Film & Cartoon",
        "persona": "You are a master animation director and Pixar/DreamWorks lead visual artist.",
        "narration_guidelines": "Expressive, animated, emotionally rich and engaging character-driven storytelling with lively pacing and a sense of wonder.",
        "visual_guidelines": "High-end 3D animated CGI feature film look, Pixar/Disney style character modeling, detailed skin and fabric textures, expressive eyes, vibrant cinematic lighting, richly detailed magical cartoon environments, ultra-high coherence.",
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
LANGUAGE_NAMES = {
    "bn": "Bengali (বাংলা)",
    "hi": "Hindi (हिन्दी)",
    "en": "English"
}

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
    target_duration: int = 60,
    character_references: list[dict] | None = None
) -> dict:
    """Uses Ollama to generate a structured storyboard script with dynamic high-retention visual cuts"""
    target_lang = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["bn"])
    cfg = VIDEO_TYPES_CONFIG.get(video_type, VIDEO_TYPES_CONFIG["story"])

    computed_scenes, words_target, words_per_scene = calculate_duration_profile(target_duration)
    final_scene_count = scene_count if (scene_count and scene_count > 0) else computed_scenes
    
    custom_char_system_prompt = ""
    custom_char_user_prompt = ""
    if character_references:
        formatted_chars = []
        for cr in character_references:
            name = cr.get("name", "").strip() or "Main Character"
            look = cr.get("look", "").strip()
            if video_type == "animation":
                char_style = f"3D animated CGI feature film character, Pixar/Disney 3D style rendition of {name}"
                if look:
                    char_style += f", featuring: {look}"
                else:
                    char_style += ", expressive 3D animated face, Pixar-like eyes, stylized hair and clothing, smooth 3D render texture"
            else:
                char_style = f"Photorealistic real human character {name}"
                if look:
                    char_style += f", featuring: {look}"
                else:
                    char_style += ", natural authentic skin texture, realistic facial features, cinematic lighting"
            formatted_chars.append(f"- Name: \"{name}\" | Look: \"{char_style}\"")

        custom_char_system_prompt = f"""

MANDATORY CHARACTER REFERENCE & CAST (Provided by user):
The story MUST feature these specific characters as the key protagonists:
{chr(10).join(formatted_chars)}
In "story_bible.characters", you MUST register these exact character names and looks, and feature them actively across the scenes.
"""
        custom_char_user_prompt = f"\n\nFeaturing Characters:\n" + "\n".join(formatted_chars)

    system_prompt = f"""{cfg['persona']}
Write ONE complete, continuous video story with EXACTLY {final_scene_count} chronological scenes, based on the user's prompt.
Production Format: {cfg['name']}
Target Total Video Duration: Approximately {target_duration} seconds (~{target_duration // 60}m {target_duration % 60}s).
{custom_char_system_prompt}
STORY CONTINUITY (most important — the video must feel like one film, not separate clips):
- Plan the whole story first: a hook, rising tension, a climax, and a resolution. Every scene is the direct result of the scene before it.
- Each scene's narration picks up exactly where the previous scene ended (cause → effect, "then", "but", "meanwhile", "at that moment"). Never restart, never summarise, never repeat information.
- Keep the same main characters, with the same names and roles, from start to finish. Introduce each character once.
- Keep one narrator voice and point of view, and one tense, for the whole story.

STORY BIBLE (keeps every image consistent across the entire video):
- "characters": exactly the 1-3 KEY recurring characters in this story. Give each a FIXED, detailed English "look": species/age, gender, skin/material, face, hair/features, build, and exact iconic clothing with colours and accessories. This exact look is reused across every scene.
- "setting": overarching world, era, and recurring locations (in English).
- "visual_style": ONE consistent art direction for the whole video. Visual Guidelines: {cfg['visual_guidelines']}

CRITICAL CHARACTER ISOLATION & LANGUAGE RULES:
- "narration" is the ONLY field written in {target_lang}. It must be natural, flowing storyteller prose.
- ALL OTHER FIELDS MUST BE 100% IN ENGLISH ("story_bible", "characters", "look", "location", "action", "visual_prompt", "motion_prompt", "setting", "visual_style").
- NEVER invent random extra people, bystanders, or unrelated characters. Each scene must focus exclusively on the specific characters listed in its "characters" field.

PACING:
- EXACTLY {final_scene_count} scenes, each ~4-6 seconds on screen.
- Each scene's narration is ~{words_per_scene} words (natural, flowing storyteller sentences in {target_lang}); ~{words_target} words in total.

VOICE PERFORMANCE:
- One consistent narrator persona for the whole story; only the intensity changes with the emotional arc (hook → deepening → climax → reflective ending).
- Use natural punctuation for rhythm: commas, "…" for a lingering pause, "—" for a sudden break.
- You MAY insert performance cues in English square brackets, ONLY from: {', '.join(PERFORMANCE_CUES)}. 0-2 per scene. Never put other words in square brackets.

Fields for each scene:
1. "narration": spoken voiceover STRICTLY in {target_lang} (~{words_per_scene} words, cues not counted). {cfg['narration_guidelines']}
2. "delivery": 2-6 vivid English words for this scene's emotion, volume and pace (e.g. "hushed, slow suspense", "grief-stricken, voice trembling", "fierce and booming").
3. "pause_after": seconds of silence after this scene: 0.0 for seamless continuous storytelling (default), 0.4-0.5 only after the final scene.
4. "characters": names (from the story bible) visible in this scene; [] if none.
5. "location": where this scene happens, in English (reuse the same wording when the place repeats).
6. "action": one English sentence — what visibly happens in this scene.
7. "continuity": one English sentence — how this scene follows from the previous one ("opening" for scene 1).
8. "visual_prompt": English, for photorealistic image generation — composition, camera angle, framing, the action, expressions, lighting. Describe ONLY the featured characters, never extra people.
9. "motion_prompt": English, for image-to-video AI. Use SUBTLE, physically plausible motion only: breathing, blinking, a slow head turn, hair or cloth moving in wind, smoke, flickering fire, drifting dust, water ripples — plus ONE slow camera move (slow push in, slow pan, gentle dolly). Avoid running, fighting, fast gestures, crowds in motion, close-up hands, transformations and spinning cameras: they cause distortion.
10. "music_level": background-music intensity for this moment: "low" (intimate, sad, tense whisper, revelations), "medium" (normal storytelling) or "high" (action, triumph, climax).

Respond ONLY with valid JSON in this exact structure:
{{
  "title": "Clear Gripping Title",
  "synopsis": "1-2 sentence overview",
  "narrator_style": "3-8 English words describing the narrator's single voice persona (e.g. warm, intimate documentary storyteller)",
  "story_bible": {{
    "characters": [{{"name": "Name", "look": "Fixed English visual description"}}],
    "setting": "Era, place, recurring locations",
    "visual_style": "One consistent art direction"
  }},
  "scenes": [
    {{
      "id": 1,
      "narration": "Voiceover in {target_lang}",
      "delivery": "How to speak it, in English",
      "pause_after": 0.0,
      "characters": ["Name"],
      "location": "Where",
      "action": "What happens",
      "continuity": "How it follows the previous scene",
      "visual_prompt": "Image description in English",
      "motion_prompt": "Subtle motion and one slow camera move, in English",
      "music_level": "medium"
    }}
  ]
}}"""

    plan = await ollama_json(system_prompt, f"Topic / Concept:\n{topic}{custom_char_user_prompt}", model=model, task="script generation")
    plan = await sanitize_visual_prompts_to_english(plan, model=model)
    return normalize_plan(plan, character_references=character_references, video_type=video_type)


async def sanitize_visual_prompts_to_english(plan: dict | list, model: str | None = None) -> dict | list:
    """Ensures character looks and scene visual prompts are in clean, descriptive English for ComfyUI."""
    is_list = isinstance(plan, list)
    plan_dict = {"scenes": plan} if is_list else plan

    bible = plan_dict.get("story_bible") or {}
    chars = bible.get("characters") or []
    has_bengali = any(isinstance(c, dict) and re.search(r'[\u0980-\u09FF]', str(c.get("look", ""))) for c in chars)
    if not has_bengali:
        has_bengali = any(isinstance(sc, dict) and re.search(r'[\u0980-\u09FF]', str(sc.get("visual_prompt", "") or sc.get("action", ""))) for sc in plan_dict.get("scenes") or [])
    
    if not has_bengali:
        return plan

    logger.info("Translating non-English character looks and visual prompts to English for ComfyUI...")
    system_prompt = """You are an AI visual art director.
ComfyUI diffusion models only understand English.
Translate and rewrite the character looks and scene visual descriptions below into vivid, detailed ENGLISH prompts for image generation.
Keep character names unchanged. Ensure each character has a specific, consistent appearance (colors, clothing, traits).
Respond ONLY with valid JSON:
{
  "characters": [{"name": "Name", "look": "Exact English visual appearance"}],
  "setting": "English setting description",
  "scenes": [{"id": 1, "visual_prompt": "Detailed English visual composition"}]
}"""
    to_translate = {
        "characters": [{"name": c.get("name"), "look": c.get("look")} for c in chars if isinstance(c, dict)],
        "setting": bible.get("setting", ""),
        "scenes": [{"id": sc.get("id", i+1), "visual_prompt": sc.get("visual_prompt") or sc.get("action", "") or sc.get("narration", "")} for i, sc in enumerate(plan_dict.get("scenes") or []) if isinstance(sc, dict)]
    }
    try:
        translated = await ollama_json(system_prompt, json.dumps(to_translate, ensure_ascii=False), model=model, task="visual prompt translation")
        if translated.get("characters"):
            bible["characters"] = translated["characters"]
        if translated.get("setting"):
            bible["setting"] = translated["setting"]
        trans_scenes = {s.get("id"): s.get("visual_prompt") for s in (translated.get("scenes") or []) if isinstance(s, dict)}
        for sc in plan_dict.get("scenes") or []:
            sc_id = sc.get("id")
            if sc_id in trans_scenes and trans_scenes[sc_id]:
                sc["visual_prompt"] = trans_scenes[sc_id]
    except Exception as e:
        logger.warning(f"Could not translate visual prompts to English: {e}")
    return plan_dict["scenes"] if is_list else plan_dict


MUSIC_LEVELS = ("low", "medium", "high")


def normalize_plan(plan: dict, character_references: list[dict] | None = None, video_type: str = "story") -> dict:
    """Validates the planner's JSON and copies the story bible into every scene.

    Scenes are the only thing persisted with a project (and edited in Story Studio), so each
    scene carries the fixed looks of its characters and the shared style; that keeps images
    consistent even after scenes are edited, reordered or refined.
    """
    bible = plan.get("story_bible") if isinstance(plan.get("story_bible"), dict) else {}
    looks = {}
    for ch in bible.get("characters") or []:
        if isinstance(ch, dict) and str(ch.get("name", "")).strip() and str(ch.get("look", "")).strip():
            looks[str(ch["name"]).strip()] = str(ch["look"]).strip()

    # Ensure custom character references are guaranteed in looks
    if character_references:
        for cr in character_references:
            c_name = str(cr.get("name", "")).strip()
            if not c_name:
                continue
            c_look = str(cr.get("look", "")).strip()
            if video_type == "animation":
                styled = f"3D animated CGI feature film character, Pixar/Disney 3D style rendition of {c_name}"
                if c_look:
                    styled += f", {c_look}"
                else:
                    styled += ", expressive 3D animated face, Pixar-like eyes, stylized hair and clothing, smooth 3D render texture"
            else:
                styled = f"Photorealistic real human character {c_name}"
                if c_look:
                    styled += f", {c_look}"
                else:
                    styled += ", natural authentic skin texture, realistic facial features, cinematic lighting"
            looks[c_name] = styled

    style = str(bible.get("visual_style", "")).strip()
    setting = str(bible.get("setting", "")).strip()

    scenes = []
    primary_char_name = list(looks.keys())[0] if looks else None

    for sc in plan.get("scenes") or []:
        if not isinstance(sc, dict) or not str(sc.get("narration", "")).strip():
            continue
        names = [str(n).strip() for n in (sc.get("characters") or []) if isinstance(n, str)]

        # If user supplied custom characters and scene has no recognized cast, include primary character
        if character_references and not any(n in looks for n in names) and primary_char_name:
            names.append(primary_char_name)

        sc["cast"] = [{"name": n, "look": looks[n]} for n in names if n in looks]
        sc["style"] = style
        sc["setting"] = setting
        level = str(sc.get("music_level", "medium")).strip().lower()
        sc["music_level"] = level if level in MUSIC_LEVELS else "medium"
        sc["id"] = len(scenes) + 1

        # Ensure visual_prompt is never None or empty
        vp = sc.get("visual_prompt")
        if not vp or str(vp).strip().lower() in ("none", "null", ""):
            vp = sc.get("action") or sc.get("additional") or sc.get("description") or sc.get("narration") or ""
        sc["visual_prompt"] = str(vp).strip()

        scenes.append(sc)
    plan["scenes"] = scenes
    plan["story_bible"] = {"characters": [{"name": n, "look": l} for n, l in looks.items()], "setting": setting, "visual_style": style}
    return plan


SHOT_CAMERA_ANGLES = [
    "cinematic wide establishing shot, expansive depth of field, full environment framing",
    "cinematic medium dynamic shot, engaging perspective, focused character action, rich visual depth",
    "dramatic cinematic close-up shot, intense focal detail, expressive character reaction, atmospheric lighting",
    "cinematic low angle heroic shot, dramatic upward perspective, powerful cinematic lighting",
    "cinematic tracking cutaway perspective, atmospheric environmental depth, vivid cinematic angle",
]


def split_scene_into_shots(narration: str, duration: float) -> list[dict]:
    """Splits a scene's narrative into 1 to 4 cinematic visual cutaway shots based on sentences and duration.
    
    Each shot receives its corresponding subtitle sentence and proportional duration.
    """
    clean = re.sub(r'\[[^\]]*\]', '', narration).strip()
    if not clean:
        return [{"text": "", "duration": duration, "index": 0}]

    # Split by Bengali (।) and English sentence delimiters
    parts = [s.strip() for s in re.split(r'([।?!.\n]+)', clean) if s.strip()]
    sents = []
    i = 0
    while i < len(parts):
        s = parts[i]
        if i + 1 < len(parts) and re.match(r'^[।?!.\n]+$', parts[i + 1]):
            s += parts[i + 1]
            i += 1
        sents.append(s)
        i += 1

    # Merge very short tokens (e.g. 1-2 words or numbers) with preceding sentence
    merged: list[str] = []
    for s in sents:
        if merged and (len(merged[-1].split()) < 3 or len(merged[-1]) < 15):
            merged[-1] = merged[-1] + " " + s
        else:
            merged.append(s)

    # Cap shots so every shot has at least ~3.2s of screen time
    max_shots = max(1, int(round(duration / 3.4)))

    # If narration only had 1 sentence but duration is long (>= 6.5s), create 2 shots
    if len(merged) <= 1 and duration >= 6.5 and max_shots >= 2:
        comma_split = [c.strip() for c in re.split(r'([,;—]+)', clean) if c.strip()]
        if len(comma_split) >= 3:
            mid = len(comma_split) // 2
            merged = [" ".join(comma_split[:mid]).strip(), " ".join(comma_split[mid:]).strip()]
        else:
            merged = [clean, clean]

    # Limit to max_shots
    if len(merged) > max_shots:
        chunk_size = len(merged) / max_shots
        condensed = []
        for k in range(max_shots):
            start = int(round(k * chunk_size))
            end = int(round((k + 1) * chunk_size))
            condensed.append(" ".join(merged[start:end]))
        merged = condensed

    num_shots = max(1, len(merged))
    weights = [max(1, len(re.sub(r'\s+', '', s))) for s in merged]
    total_w = sum(weights) or 1

    shots = []
    assigned_time = 0.0
    for idx, (text_chunk, w) in enumerate(zip(merged, weights)):
        if idx == num_shots - 1:
            shot_dur = max(0.5, round(duration - assigned_time, 3))
        else:
            shot_dur = max(0.5, round(duration * (w / total_w), 3))
            assigned_time += shot_dur
        shots.append({
            "index": idx,
            "text": text_chunk.strip(),
            "duration": shot_dur,
        })
    return shots


def concat_shot_clips(shot_clips: list[Path], output_path: Path) -> Path:
    """Concatenates multiple sub-shot clips into a seamless single scene video."""
    if not shot_clips:
        raise ValueError("Cannot concatenate empty list of shot clips")
    if len(shot_clips) == 1:
        if shot_clips[0] != output_path:
            shutil.copy(shot_clips[0], output_path)
        return output_path

    concat_list = output_path.with_name(f"{output_path.stem}_concat.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in shot_clips:
            f.write(f"file '{clip.as_posix()}'\n")

    subprocess.run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(output_path)],
        check=True, capture_output=True,
    )
    concat_list.unlink(missing_ok=True)
    return output_path


def compose_image_prompt(scene: dict, shot_index: int = 0, total_shots: int = 1) -> str:
    """Scene prompt + fixed looks of characters in it + strict isolation + setting/style + dynamic shot camera framing."""
    parts = []

    # 1. Base visual prompt
    vp = scene.get("visual_prompt") or scene.get("action") or scene.get("additional") or ""
    vp = str(vp).strip().rstrip(".")
    if vp and vp.lower() not in ("none", "null"):
        parts.append(vp)

    # Dynamic camera framing for multi-shot visual progression within the scene
    if total_shots > 1:
        angle_cue = SHOT_CAMERA_ANGLES[shot_index % len(SHOT_CAMERA_ANGLES)]
        parts.append(angle_cue)

    # 2. Characters & Cast Isolation
    cast_members = scene.get("cast") or []
    if cast_members:
        char_tokens = []
        char_names = []
        for m in cast_members:
            name = m.get("name", "").strip()
            look = m.get("look", "").strip()
            if name and look:
                char_tokens.append(f"{name} ({look})")
                char_names.append(name)
        if char_tokens:
            parts.append(f"Featuring: {', '.join(char_tokens)}")
            parts.append(f"Depict ONLY {', '.join(char_names)}. Strictly no extra people, no random bystanders, maintain consistent character appearance")
    if scene.get("location"):
        parts.append(f"Location: {scene['location']}")
    if scene.get("setting"):
        parts.append(f"Setting: {scene['setting']}")
    if scene.get("style"):
        parts.append(f"Style: {scene['style']}")

    return ". ".join(p for p in parts if p) + "."


def project_seed(project_id: str) -> int:
    """One seed per project, so every scene is rendered with the same noise and looks related."""
    return int(hashlib.sha1((project_id or "vidforge").encode()).hexdigest()[:8], 16) % (2**31 - 1) + 1

async def ollama_json(system_prompt: str, user_content: str, model: str | None = None, task: str = "generation") -> dict:
    """Runs a JSON-mode Ollama chat, falling back through installed models, and frees VRAM afterwards."""
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
            logger.info(f"Ollama {task} with model: {candidate}...")
            async with httpx.AsyncClient(timeout=240.0) as client:
                payload = {
                    "model": candidate,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
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
                logger.info(f"Ollama {task} succeeded with {candidate}")
                # Proactively unload Ollama model so 100% of GPU is ready for ComfyUI / F5-TTS
                await free_gpu_memory(unload_comfy=False, unload_ollama=True)
                return result
        except Exception as e:
            logger.warning(f"Failed generation with candidate {candidate}: {e}")
            last_error = e
            await free_gpu_memory(unload_comfy=True, unload_ollama=True)

    raise RuntimeError(f"Ollama {task} failed: {last_error}")

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

async def plan_script(prompt: str, language: str, video_type: str = "story", target_duration: int = 60, model: str = None, character_references: list[dict] | None = None) -> dict:
    if not model:
        model = await get_active_ollama_model()
    return await generate_story_script(
        topic=prompt,
        language=language,
        model=model,
        video_type=video_type,
        target_duration=target_duration,
        character_references=character_references
    )

async def plan_story(prompt: str, language: str, model: str = None, character_references: list[dict] | None = None) -> dict:
    return await plan_script(prompt, language, video_type="story", target_duration=60, model=model, character_references=character_references)

SCENE_FIELDS = ("narration", "delivery", "pause_after", "characters", "location", "action", "continuity",
                "visual_prompt", "motion_prompt", "music_level")
# Copied from the original script into revised scenes; the planner fills them from the story bible
BIBLE_FIELDS = ("cast", "style", "setting")

def parse_direct_script_raw(text: str) -> list[dict]:
    """Parses raw user-submitted script into structured scenes without altering any narration words.
    
    Supported formats:
    1. JSON array: [{"narration": "...", "visual_prompt": "..."}]
    2. Tagged format:
       [Scene 1] or [দৃশ্য ১]
       Narration / ভয়েসওভার: ...
       Visual / চিত্রায়ন: ...
    3. Blank-line separated paragraphs (each paragraph = 1 scene).
    """
    text = text.strip()
    if not text:
        return []

    # 1. Try parsing JSON array
    if (text.startswith("[") and text.endswith("]")) or (text.startswith("{") and "scenes" in text):
        try:
            parsed = json.loads(text)
            items = parsed if isinstance(parsed, list) else parsed.get("scenes", [])
            scenes = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                narration = str(item.get("narration") or item.get("voiceover") or item.get("text") or "").strip()
                if not narration:
                    continue
                scenes.append({
                    "narration": narration,
                    "visual_prompt": str(item.get("visual_prompt") or item.get("visual") or item.get("image_prompt") or "").strip(),
                    "delivery": str(item.get("delivery") or "").strip(),
                    "motion_prompt": str(item.get("motion_prompt") or "subtle cinematic motion, slow push in").strip(),
                    "pause_after": float(item.get("pause_after", 0.0)),
                    "characters": item.get("characters") if isinstance(item.get("characters"), list) else [],
                    "location": str(item.get("location") or "").strip(),
                    "action": str(item.get("action") or "").strip(),
                    "continuity": str(item.get("continuity") or "").strip(),
                    "music_level": item.get("music_level", "medium") if item.get("music_level") in MUSIC_LEVELS else "medium",
                })
            if scenes:
                return scenes
        except Exception:
            pass

    # 2. Try parsing tagged scenes: [Scene 1: title], [Scene 1], [দৃশ্য ১: শিরোনাম], [দৃশ্য ১], Scene 1:, দৃশ্য ১:, শেষ বার্তা:, Outro:
    scene_header_pattern = re.compile(
        r'(?:^|\n)\s*(?:\[\s*(?:Scene|দৃশ্য|Scène|Escena|Outro|শেষ বার্তা|উপসংহার)[^\]]*\]|(?:Scene|দৃশ্য|Scène|Escena|Outro|শেষ বার্তা|উপসংহার)\s*#?[০-৯\d]*\s*[:\-])',
        re.IGNORECASE
    )
    splits = list(scene_header_pattern.finditer(text))
    if splits:
        scenes = []
        is_animation = any(w in text.lower() for w in ("animation", "animated", "cartoon", "3d animation", "anime", "pixar", "disney"))
        for i, match in enumerate(splits):
            header_text = match.group(0).strip()
            start = match.end()
            end = splits[i + 1].start() if i + 1 < len(splits) else len(text)
            block = text[start:end].strip()
            if not block:
                continue

            is_outro = bool(re.search(r'শেষ বার্তা|Outro|উপসংহার', header_text, re.IGNORECASE))

            narr_match = re.search(
                r'(?:Narration|ভয়েসওভার|বক্তব্য|Voiceover|Script)\s*[:\-]\s*(.+?)(?=\n\s*(?:Visual|চিত্রায়ন|ছবি|Prompt|Image|Delivery|ডেলিভারি|Motion|মোশন)\s*[:\-]|$)',
                block, re.DOTALL | re.IGNORECASE
            )
            vis_match = re.search(
                r'(?:Visual|চিত্রায়ন|ছবি|Prompt|Image)\s*[:\-]\s*(.+?)(?=\n\s*(?:Narration|ভয়েসওভার|Delivery|ডেলিভারি|Motion|মোশন)\s*[:\-]|$)',
                block, re.DOTALL | re.IGNORECASE
            )
            deliv_match = re.search(
                r'(?:Delivery|ডেলিভারি)\s*[:\-]\s*(.+?)(?=\n\s*(?:Narration|Visual|Motion)\s*[:\-]|$)',
                block, re.DOTALL | re.IGNORECASE
            )
            mot_match = re.search(
                r'(?:Motion|মোশন)\s*[:\-]\s*(.+?)(?=\n\s*(?:Narration|Visual|Delivery)\s*[:\-]|$)',
                block, re.DOTALL | re.IGNORECASE
            )

            if narr_match:
                narration = narr_match.group(1).strip()
            else:
                if vis_match:
                    narration = block[:vis_match.start()].strip()
                else:
                    narration = block

            # Strip any accidental metadata tags from narration
            narration = re.sub(r'^(?:Narration|ভয়েসওভার|বক্তব্য|Voiceover|Script)\s*[:\-]\s*', '', narration, flags=re.IGNORECASE).strip()
            narration = re.sub(r'\n\s*(?:Visual|চিত্রায়ন|ছবি|Prompt|Image)\s*[:\-].*$', '', narration, flags=re.DOTALL | re.IGNORECASE).strip()

            visual_prompt = vis_match.group(1).strip() if vis_match else ""
            visual_prompt = re.sub(r'^(?:Visual|চিত্রায়ন|ছবি|Prompt|Image)\s*[:\-]\s*', '', visual_prompt, flags=re.IGNORECASE).strip()

            if is_outro and not visual_prompt:
                visual_prompt = (
                    "Warm heartfelt closing scene, inspirational quote, friendship theme, cinematic 3D animation, soft golden glow"
                    if is_animation else
                    "Warm heartfelt closing scene, inspirational quote, friendship theme, soft golden sunlight glow, cinematic atmosphere"
                )

            delivery = deliv_match.group(1).strip() if deliv_match else ""
            motion_prompt = mot_match.group(1).strip() if mot_match else "subtle cinematic motion, slow push in"

            if narration:
                scenes.append({
                    "narration": narration,
                    "visual_prompt": visual_prompt,
                    "delivery": delivery,
                    "motion_prompt": motion_prompt,
                    "pause_after": 0.0,
                    "characters": [],
                    "location": "",
                    "action": "",
                    "continuity": "",
                    "music_level": "medium",
                })
        if scenes:
            return scenes

    # 3. Simple Paragraph format: blank lines separate scenes
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]
    scenes = []
    for p in paragraphs:
        # Strip any accidental tags if someone pasted without headers
        clean_p = re.sub(r'^(?:Narration|ভয়েসওভার|বক্তব্য|Voiceover|Script)\s*[:\-]\s*', '', p, flags=re.IGNORECASE).strip()
        scenes.append({
            "narration": clean_p,
            "visual_prompt": "",
            "delivery": "",
            "motion_prompt": "subtle cinematic motion, slow push in",
            "pause_after": 0.0,
            "characters": [],
            "location": "",
            "action": "",
            "continuity": "",
            "music_level": "medium",
        })
    return scenes

async def build_scenes_from_direct_script(
    prompt: str,
    language: str = "bn",
    character_references: list[dict] | None = None,
    video_type: str = "story"
) -> list[dict]:
    """Builds video scenes from an exact direct script.
    
    Guarantees that narration is 100% word-for-word identical to the user's input.
    Generates English visual prompts for ComfyUI Z-Image Turbo if needed and guarantees
    that uploaded character likeness definitions are attached to every scene.
    """
    raw_scenes = parse_direct_script_raw(prompt)
    if not raw_scenes:
        raise ValueError("Could not parse any scenes from the provided script. Please check formatting.")

    is_animation = any(w in prompt.lower() for w in ("animation", "animated", "cartoon", "3d animation", "anime", "pixar", "disney"))

    cast = []
    if character_references:
        for cr in character_references:
            if not isinstance(cr, dict):
                continue
            c_name = str(cr.get("name", "")).strip()
            c_look = str(cr.get("look", "")).strip()
            if c_name and c_look:
                cast.append({"name": c_name, "look": c_look})

    # Check if any scene is missing an English visual prompt
    needs_visual = any(
        not sc.get("visual_prompt") or any(ord(c) > 127 for c in sc.get("visual_prompt", ""))
        for sc in raw_scenes
    )

    if needs_visual:
        target_lang = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["bn"])
        narrations_summary = "\n".join([f"Scene {i+1}: {sc['narration']}" for i, sc in enumerate(raw_scenes)])
        style_instruction = (
            "cinematic 3D animated CGI feature film look, Pixar/Disney style 3D character modeling, expressive stylized faces, vibrant lighting, animated movie aesthetic. DO NOT describe realistic real-life human photos."
            if is_animation else
            "rich photorealistic cinematic lighting, detailed environment, dramatic camera angle, atmospheric lighting."
        )
        cast_text = ""
        if cast:
            cast_lines = "\n".join(f"- {c['name']}: {c['look']}" for c in cast)
            cast_text = f"\nMANDATORY PROTAGONISTS TO FEATURE IN EVERY VISUAL PROMPT:\n{cast_lines}\nEnsure the visual_prompt explicitly depicts these character(s) in action.\n"

        system_prompt = f"""You are a visual director for an AI image generator (Z-Image Turbo).
The director has provided the exact voiceover narration for {len(raw_scenes)} scenes.
DO NOT change, edit, or translate the voiceover narration.
{cast_text}
For each scene, write:
1. "visual_prompt": A vivid English image prompt ({style_instruction}) illustrating what happens in that scene and featuring the protagonist.
2. "action": One English sentence describing the visible action.
3. "location": The place in English.
4. "motion_prompt": Subtle cinematic motion (e.g. "slow push in, subtle breathing and dust motes").

Respond ONLY with valid JSON:
{{
  "scenes": [
    {{
      "id": 1,
      "visual_prompt": "English visual description...",
      "action": "Visible action in English...",
      "location": "Location in English...",
      "motion_prompt": "slow push in"
    }}
  ]
}}"""
        try:
            model = await get_active_ollama_model()
            res = await ollama_json(system_prompt, f"Scene Narrations ({target_lang}):\n{narrations_summary}", model=model, task="direct script visual prompt generation")
            planned = res.get("scenes", [])
            for i, sc in enumerate(raw_scenes):
                if i < len(planned) and isinstance(planned[i], dict):
                    p = planned[i]
                    if not sc.get("visual_prompt") or any(ord(c) > 127 for c in sc.get("visual_prompt", "")):
                        sc["visual_prompt"] = p.get("visual_prompt") or sc.get("visual_prompt") or ""
                    sc["action"] = p.get("action") or sc.get("action") or ""
                    sc["location"] = p.get("location") or sc.get("location") or ""
                    if p.get("motion_prompt"):
                        sc["motion_prompt"] = p["motion_prompt"]
        except Exception as e:
            logger.warning(f"Could not generate visual prompts with Ollama for direct script: {e}")
            fallback_style = "cinematic 3D animation, Pixar Disney 3D animated movie style, expressive character faces" if is_animation else "cinematic film lighting, photorealistic 8k"
            for i, sc in enumerate(raw_scenes):
                if not sc.get("visual_prompt") or any(ord(c) > 127 for c in sc.get("visual_prompt", "")):
                    sc["visual_prompt"] = f"{fallback_style}, scene depicting: {sc['narration'][:120]}"

    # Final sanitization: ensure IDs, cast likeness, 0.0 pause for continuous speech, sanitize prompts to English
    for i, sc in enumerate(raw_scenes):
        sc["id"] = i + 1
        sc["pause_after"] = 0.0
        if cast:
            sc["cast"] = cast
            sc["characters"] = [c["name"] for c in cast]
        if not sc.get("music_level") or sc.get("music_level") not in MUSIC_LEVELS:
            sc["music_level"] = "medium"
        if not sc.get("motion_prompt"):
            sc["motion_prompt"] = "subtle cinematic motion, slow push in"

    # Sanitize visual prompts to English for ComfyUI
    raw_scenes = await sanitize_visual_prompts_to_english(raw_scenes)
    return raw_scenes


async def refine_script(title: str, scenes: list[dict], instruction: str, language: str, video_type: str = "story") -> list[dict]:
    """Revises an existing storyboard according to a user instruction.

    Scenes the instruction does not touch are copied verbatim, so the worker can reuse
    their already-rendered voiceover, image and clip.
    """
    target_lang = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["bn"])
    cfg = VIDEO_TYPES_CONFIG.get(video_type, VIDEO_TYPES_CONFIG["story"])
    current = [{k: sc.get(k) for k in SCENE_FIELDS if sc.get(k) is not None} for sc in scenes]
    system_prompt = f"""{cfg['persona']}
You are revising an existing video script titled "{title}" according to the director's instruction.

Rules:
- Apply the instruction faithfully. It may change narration, visuals, camera motion, pacing, or add/remove/reorder scenes.
- Any scene the instruction does not affect MUST be copied back EXACTLY, character for character, so it does not need to be re-rendered.
- "narration" stays STRICTLY in {target_lang}. "delivery", "visual_prompt" and "motion_prompt" stay in English.
- Performance cues inside narration may only come from: {', '.join(PERFORMANCE_CUES)}.
- Each scene keeps the fields: narration, delivery, pause_after, characters, location, action, continuity, visual_prompt, motion_prompt, music_level.
- Keep the story continuous: every scene still follows from the one before it, with the same characters and names.
- motion_prompt stays subtle and physically plausible with one slow camera move; music_level is "low", "medium" or "high".

Respond ONLY with valid JSON: {{"scenes": [ ...every scene of the revised script, in order... ]}}"""
    user_content = (
        f"Current script (JSON):\n{json.dumps({'scenes': current}, ensure_ascii=False, indent=1)}\n\n"
        f"Director's instruction:\n{instruction}"
    )
    result = await ollama_json(system_prompt, user_content, task="script refinement")
    revised = []
    for i, sc in enumerate(result.get("scenes") or []):
        if not isinstance(sc, dict) or not str(sc.get("narration", "")).strip() or not str(sc.get("visual_prompt", "")).strip():
            continue
        clean = {k: sc[k] for k in SCENE_FIELDS if k in sc}
        clean["id"] = i + 1
        revised.append(clean)
    # Re-attach the fixed character looks and shared style from the original script
    looks = {m["name"]: m["look"] for sc in scenes for m in (sc.get("cast") or []) if m.get("name") and m.get("look")}
    shared = next((sc for sc in scenes if sc.get("style") or sc.get("setting")), {})
    for sc in revised:
        names = [n for n in (sc.get("characters") or []) if isinstance(n, str)]
        sc["cast"] = [{"name": n, "look": looks[n]} for n in names if n in looks]
        sc["style"] = shared.get("style", "")
        sc["setting"] = shared.get("setting", "")
        if sc.get("music_level") not in MUSIC_LEVELS:
            sc["music_level"] = "medium"
    if not revised:
        raise ValueError("The AI did not return a usable revised script")
    return revised

async def refine_image_prompt(base_prompt: str, instruction: str, title: str = "") -> str:
    """Rewrites an image prompt to apply a refinement instruction (used for thumbnail backgrounds)."""
    system_prompt = """You write prompts for a photorealistic text-to-image model (Z-Image-Turbo).
Rewrite the given prompt so the image satisfies the user's instruction while keeping everything the instruction does not change.
The image is a video thumbnail background: one bold, instantly readable focal subject, strong contrast, dramatic lighting,
and clean negative space for a headline. Never ask for text, letters or logos in the image.
Respond ONLY with valid JSON: {"prompt": "the rewritten English prompt"}"""
    user_content = f"Video title: {title}\nCurrent prompt: {base_prompt or '(none yet)'}\nInstruction: {instruction}"
    result = await ollama_json(system_prompt, user_content, task="thumbnail prompt refinement")
    prompt = str(result.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("The AI did not return an image prompt")
    return prompt

async def suggest_thumbnail_headlines(title: str, synopsis: str, language: str) -> list[str]:
    target_lang = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["bn"])
    system_prompt = f"""You are a YouTube packaging expert. Write 5 short, high-click-through thumbnail headlines
in {target_lang} for the video below. Each is 2-5 words, punchy, curiosity-driven, no hashtags, no emojis, no quotes.
Respond ONLY with valid JSON: {{"headlines": ["...", "...", "...", "...", "..."]}}"""
    result = await ollama_json(system_prompt, f"Title: {title}\nAbout: {synopsis}", task="thumbnail headlines")
    return [str(h).strip() for h in (result.get("headlines") or []) if str(h).strip()][:5]

async def generate_thematic_poster_concept(
    title: str,
    story_prompt: str,
    scenes: list[dict],
    video_type: str = "story",
    language: str = "bn",
    character_references: list[dict] | None = None
) -> dict:
    """Synthesizes the entire story, characters, and emotional arc into an iconic, theatrical movie poster concept."""
    target_lang = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["bn"])
    
    # Safely parse scenes if passed as JSON string
    if isinstance(scenes, str):
        try:
            scenes = json.loads(scenes)
        except Exception:
            scenes = []
    if not isinstance(scenes, list):
        scenes = []

    # Compile the full story context from scenes or story_prompt
    story_narrations = []
    characters_set = set()
    for i, s in enumerate(scenes):
        if not isinstance(s, dict):
            continue
        narr = s.get("narration", "").strip()
        if narr:
            story_narrations.append(f"Scene {i+1}: {narr}")
        chars = s.get("characters", [])
        if isinstance(chars, list):
            for c in chars:
                if c and isinstance(c, str):
                    characters_set.add(c)
                
    full_narrative = "\n".join(story_narrations) if story_narrations else story_prompt
    characters_info = ", ".join(characters_set) if characters_set else "Main story characters"
    
    # Safely parse character_references if passed as JSON string
    if isinstance(character_references, str):
        try:
            character_references = json.loads(character_references)
        except Exception:
            character_references = []
    if not isinstance(character_references, list):
        character_references = []

    char_styling_hint = ""
    cr_lines = []
    for cr in character_references:
        if isinstance(cr, dict) and cr.get("look"):
            cr_lines.append(f"- {cr.get('name', 'Hero')}: {cr.get('look', '')}")
    if cr_lines:
        char_styling_hint = "Featured Characters:\n" + "\n".join(cr_lines)

    system_prompt = f"""You are an award-winning cinematic art director and film poster designer (specialized in Hollywood theatrical key art, Pixar/Disney animation one-sheets, and Criterion collection posters).
Your mission is to analyze the ENTIRE story below and design a MASTER THEMATIC POSTER that captures the deep soul, core conflict, and emotional heart of the whole video.

A REAL POSTER DOES NOT SIMPLY SHOW A SINGLE RANDOM SCENE OR SCREENSHOT.
Instead, a real poster:
1. Synthesizes the full narrative journey, emotional climax, and thematic essence in ONE iconic, visually arresting composition.
2. Features iconic, symbolic character staging: the central figures posed with expressive chemistry and dynamic hierarchy that encapsulates their relationship.
3. Uses masterwork visual storytelling: dramatic theatrical lighting, atmospheric depth, rich layered composition (foreground symbolism, striking midground figures, evocative backdrop).
4. Genre aesthetic: The video type is "{video_type}".
   - If animation: Pixar/DreamWorks 3D CGI cinematic movie poster key visual, expressive stylized characters, rich tactile textures, magical theatrical rim lighting, vibrant color palette.
   - If story/historical/drama: Epic theatrical film one-sheet, cinematic chiaroscuro, sweeping atmospheric lighting.
   - If mystery/thriller: Tense chiaroscuro, moody silhouettes, symbolic clues, deep shadows.
5. Provides deliberate negative space at the top or bottom for theatrical poster typography.
6. CRITICAL: NEVER include any text, letters, titles, watermarks, or words inside the "poster_prompt" image description.

Respond ONLY with valid JSON in this exact structure:
{{
  "poster_prompt": "English text-to-image prompt describing the grand theatrical poster artwork in vivid detail (composition, subjects, expressions, lighting, colors, style). Do not ask for text.",
  "tagline": "Evocative, powerful movie poster tagline in {target_lang} (4-8 words capturing the soul/essence of the entire story)",
  "headline": "Grand theatrical movie title in {target_lang}",
  "subline": "Cinematic subtitle or credit line in {target_lang}",
  "theme_summary": "1-sentence English explanation of the core theme and visual metaphor chosen",
  "recommended_style": "cinematic_gold",
  "textColor": "#ffffff",
  "accentColor": "#facc15"
}}"""

    user_content = f"""Title: {title}
Video Type: {video_type}
Characters: {characters_info}
{char_styling_hint}

Full Narrative:
{full_narrative[:2500]}"""

    result = await ollama_json(system_prompt, user_content, task="thematic poster concept")
    return {
        "poster_prompt": str(result.get("poster_prompt", "")).strip(),
        "tagline": str(result.get("tagline", "")).strip(),
        "headline": str(result.get("headline", title)).strip() or title,
        "subline": str(result.get("subline", "")).strip(),
        "theme_summary": str(result.get("theme_summary", "")).strip(),
        "recommended_style": str(result.get("recommended_style", "cinematic_gold")),
        "textColor": str(result.get("textColor", "#ffffff")),
        "accentColor": str(result.get("accentColor", "#facc15")),
    }

async def extract_character_face_features(
    image_path: Path | str,
    character_name: str = "",
    video_type: str = "animation"
) -> dict:
    """Analyzes a real person's portrait photo using local vision AI (moondream) and synthesizes
    an accurate, highly detailed 3D Pixar/Disney cartoon character description preserving their
    authentic facial features (face structure, eyes, hairstyle, beard, smile, and accessories).
    """
    image_path = Path(image_path)
    if not image_path.exists():
        logger.warning(f"Character image not found: {image_path}")
        return {"name": character_name, "look": "", "cartoon_look": "", "features_summary": ""}

    name = character_name.strip() or "Protagonist"
    img_bytes = image_path.read_bytes()
    b64_img = base64.b64encode(img_bytes).decode("utf-8")

    raw_face_description = ""
    # 1. Primary: Use Ollama local vision model (moondream)
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            v_payload = {
                "model": "moondream:latest",
                "prompt": (
                    "Describe this person's facial features in detail: "
                    "1. Gender and estimated age. "
                    "2. Skin tone and complexion. "
                    "3. Face shape (jawline, cheekbones, chin). "
                    "4. Eyes: eye shape, color, eyelid folds, eyebrow shape and thickness. "
                    "5. Nose shape and mouth/lips/smile. "
                    "6. Hair: color, cut/style, parting, length, texture. "
                    "7. Facial hair: clean-shaven, stubble, mustache, or beard style. "
                    "8. Glasses, clothing, or distinctive features. Be very specific."
                ),
                "images": [b64_img],
                "stream": False
            }
            res = await client.post(f"{OLLAMA_URL}/api/generate", json=v_payload)
            if res.status_code == 200:
                raw_face_description = res.json().get("response", "").strip()
                logger.info(f"Ollama vision face extraction succeeded: {raw_face_description[:120]}...")
    except Exception as e:
        logger.warning(f"Ollama vision face extraction failed: {e}")

    # 2. Synthesize into high-fidelity Pixar/Disney 3D animation character specification
    system_prompt = f"""You are a senior lead character designer at Pixar Animation Studios and Walt Disney Animation.
Your task is to take facial analysis observations of a real person and generate a 3D animated character visual description that:
1. FAITHFULLY AND ACCURATELY CAPTURES THIS SPECIFIC PERSON'S UNMISTAKABLE FACIAL LIKENESS.
2. The generated cartoon character MUST have:
   - Their exact face structure (jaw, chin, cheek fullness, face shape)
   - Their exact skin tone & complexion
   - Their exact hairstyle, hairline, parting, hair texture, and color
   - Their exact eyes: eye shape, iris color, eyebrow shape and thickness
   - Their exact facial hair (exact beard/mustache shape or clean-shaven)
   - Their exact glasses or distinctive facial marks
3. Translates their real features into an appealing, expressive Pixar/Disney 3D CGI stylized animation aesthetic.
4. Output MUST be in English.

Respond ONLY with valid JSON in this structure:
{{
  "character_name": "{name}",
  "features_summary": "1 concise sentence summarizing the person's key facial features (e.g. Young South Asian man, neat black side-parted hair, rectangular glasses, trimmed goatee beard, warm smile)",
  "facial_structure": "detailed description of face shape, jawline, cheeks, chin",
  "hair_and_facial_hair": "detailed description of hair cut, part, texture, and facial hair",
  "eyes_and_expression": "detailed description of eyes, brows, expression",
  "cartoon_look": "Complete Pixar/Disney 3D animated CGI feature film character prompt describing {name}'s exact stylized facial likeness, hair, skin, eyes, facial hair, and clothing in rich detail. Emphasize 'unmistakable facial likeness of {name}'."
}}"""

    user_content = f"Character Name: {name}\n\nObserved Facial Features from Photo:\n{raw_face_description if raw_face_description else 'A real person whose portrait is provided.'}"

    try:
        res = await ollama_json(system_prompt, user_content, task="character face synthesis")
        cartoon_look = res.get("cartoon_look", "").strip()
        summary = res.get("features_summary", "").strip()
        look = cartoon_look if cartoon_look else f"3D animated CGI Pixar/Disney style rendition of {name}, featuring authentic facial likeness, stylized hair, expressive eyes, smooth 3D render textures"
        return {
            "name": name,
            "look": look,
            "cartoon_look": cartoon_look,
            "features_summary": summary,
            "raw_analysis": raw_face_description
        }
    except Exception as e:
        logger.error(f"Failed to synthesize character cartoon look: {e}")
        return {
            "name": name,
            "look": f"3D animated CGI Pixar/Disney style rendition of {name}, featuring authentic facial likeness, styled hair, expressive eyes, smooth 3D render textures",
            "cartoon_look": "",
            "features_summary": "",
            "raw_analysis": raw_face_description
        }

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
    if not audio_path.exists():
        logger.warning(f"pad_audio_with_silence: audio file not found, skipping: {audio_path}")
        return audio_path
    tmp = audio_path.with_name(f"{audio_path.stem}_padded{audio_path.suffix}")
    cmd = [FFMPEG, "-y", "-i", str(audio_path), "-af", f"apad=pad_dur={seconds:.2f}", str(tmp)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        err = res.stderr.strip() if res.stderr else f"ffmpeg exited with {res.returncode}"
        raise RuntimeError(f"FFmpeg padding failed for {audio_path.name}: {err}")
    os.replace(tmp, audio_path)
    return audio_path

def comfy_subfolder(project_id: str) -> str:
    """ComfyUI output subfolder for a project's renders, so they can be purged with it."""
    return f"vidforge/{project_id}"

async def generate_scene_image(visual_prompt: str, aspect: str, output_path: Path, project_id: str = "") -> Path:
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    wf_path = BASE_DIR / "z_image_turbo_text_to_image_api.json"
    if not wf_path.exists():
        wf_path = BASE_DIR / "workflows" / "z_image_turbo_text_to_image_api.json"
    
    wf = json.loads(wf_path.read_text(encoding="utf-8"))

    for node in wf.values():
        title = node.get("_meta", {}).get("title")
        if title == "VF_PROMPT":
            node["inputs"]["text"] = visual_prompt
        elif title in ("VF_NEG", "VF_NEGATIVE"):
            is_animation = any(w in visual_prompt.lower() for w in ("animation", "animated", "cartoon", "pixar", "disney", "3d cgi", "3d animated"))
            if is_animation:
                node["inputs"]["text"] = "blurry, low quality, distorted, extra limbs, bad anatomy, deformed, ugly face, mismatched facial features, photorealistic real human photo, grainy, text, watermark"
            else:
                node["inputs"]["text"] = "blurry, low quality, distorted, extra limbs, bad anatomy, deformed, ugly, cartoon, 3d render, illustration, anime, text, watermark"
        elif title == "VF_LATENT":
            node["inputs"]["width"] = dims["width"]
            node["inputs"]["height"] = dims["height"]
        elif title == "VF_SAMPLER":
            node["inputs"]["seed"] = project_seed(project_id) if project_id else random.randint(1, 2**31 - 1)
        elif title == "VF_SAVE" and project_id:
            node["inputs"]["filename_prefix"] = f"{comfy_subfolder(project_id)}/image"

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

# ---------------------------------------------------------------------------
# Wan 2.1 image-to-video
# ---------------------------------------------------------------------------
# Every scene clip is rendered at this frame rate with an exact frame count, and each scene's
# audio is snapped to the same frame grid, so picture and narration never drift apart.
VIDEO_FPS = 30
WAN_FPS = 16  # Wan 2.1 is trained at 16 fps (wan/configs/shared_config.py: sample_fps)

# Checkpoints in preference order. All run at 832x480, the size VidForge renders Wan at.
# The 480p GGUF quantisations (city96/Wan2.1-I2V-14B-480P-gguf) fit in 16 GB of VRAM; the FP8
# checkpoints are 16.4 GB and make ComfyUI offload part of the model to system RAM.
WAN_MODEL_CANDIDATES = (
    "wan2.1-i2v-14b-480p-Q5_K_M.gguf",
    "wan2.1-i2v-14b-480p-Q4_K_M.gguf",
    "wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors",
    "wan2.1_i2v_720p_14B_fp8_e4m3fn.safetensors",
)
WAN_UNET = _setting("wan_unet", "VIDFORGE_WAN_UNET", "")
WAN_QUALITY = _setting("wan_quality", "VIDFORGE_WAN_QUALITY", "balanced")
# Official I2V defaults (Wan2.1 generate.py): 40 steps, guide scale 5.0, shift 3.0 at 832x480, 81 frames.
WAN_PRESETS = {
    "fast": {"max_frames": 33, "steps": 20},
    "balanced": {"max_frames": 49, "steps": 30},
    "quality": {"max_frames": 81, "steps": 40},
}
WAN_SHIFT_480P = 3.0
WAN_CFG = 5.0
# Official negative prompt (wan/configs/shared_config.py) plus an English summary of the same artifacts
WAN_NEGATIVE_PROMPT = (
    "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，"
    "丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，"
    "杂乱的背景，三条腿，背景人很多，倒着走, "
    "deformed face, morphing, warped background, extra limbs, flickering, text, watermark"
)


def pick_wan_model() -> str:
    """The configured Wan checkpoint, else the best one installed in ComfyUI."""
    if WAN_UNET:
        return WAN_UNET
    for name in WAN_MODEL_CANDIDATES:
        for folder in ("diffusion_models", "unet"):
            if (COMFYUI_DIR / "models" / folder / name).exists():
                return name
    return WAN_MODEL_CANDIDATES[-1]


def wan_frame_count(duration: float, max_frames: int) -> int:
    """Frames to generate for a scene: covers the scene where possible, 4n+1 as Wan requires."""
    wanted = int(duration * WAN_FPS) + 1
    frames = min(max_frames, max(17, wanted))
    return ((frames - 1) // 4) * 4 + 1


async def comfy_vram() -> tuple[float, float] | None:
    """(used_gb, total_gb) of ComfyUI's GPU, or None if it can't be read."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            dev = (await client.get(f"{COMFYUI_URL}/system_stats")).json()["devices"][0]
        total = dev["vram_total"] / 1024**3
        return total - dev["vram_free"] / 1024**3, total
    except Exception:
        return None


async def animate_scene_wan(image_path: Path, motion_prompt: str, aspect: str, raw_clip_path: Path,
                            project_id: str = "", duration: float = 5.0) -> bool:
    """Invokes Wan 2.1 I2V in ComfyUI to animate the scene image."""
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    preset = WAN_PRESETS.get(WAN_QUALITY, WAN_PRESETS["balanced"])
    unet = pick_wan_model()
    frames = wan_frame_count(duration, preset["max_frames"])

    COMFYUI_INPUT.mkdir(parents=True, exist_ok=True)
    input_filename = f"wan_in_{project_id}_{image_path.stem}.png" if project_id else f"wan_in_{image_path.stem}.png"
    shutil.copy(image_path, COMFYUI_INPUT / input_filename)
    prefix = f"wan_{image_path.stem}"

    loader = (
        {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": unet}}  # ComfyUI-GGUF custom node
        if unet.endswith(".gguf")
        else {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}}
    )
    wan_prompt = {
        "37": loader,
        "38": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "39": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "49": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["38", 0], "text": (
            f"{motion_prompt}. Subtle natural motion, stable camera, the same characters and background as the "
            "first frame, consistent faces and anatomy, cinematic lighting, highly detailed"
        )}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["38", 0], "text": WAN_NEGATIVE_PROMPT}},
        "54": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["37", 0], "shift": WAN_SHIFT_480P}},
        "52": {"class_type": "LoadImage", "inputs": {"image": input_filename}},
        "51": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["49", 0], "image": ["52", 0], "crop": "center"}},
        "50": {"class_type": "WanImageToVideo", "inputs": {
            "positive": ["6", 0], "negative": ["7", 0], "vae": ["39", 0], "clip_vision_output": ["51", 0],
            "start_image": ["52", 0], "width": dims["wan_w"], "height": dims["wan_h"], "length": frames, "batch_size": 1,
        }},
        "3": {"class_type": "KSampler", "inputs": {
            "model": ["54", 0], "positive": ["50", 0], "negative": ["50", 1], "latent_image": ["50", 2],
            "seed": project_seed(project_id + image_path.stem), "steps": preset["steps"], "cfg": WAN_CFG,
            "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0,
        }},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["39", 0]}},
        "55": {"class_type": "CreateVideo", "inputs": {"images": ["8", 0], "fps": float(WAN_FPS)}},
        "56": {"class_type": "SaveVideo", "inputs": {
            "video": ["55", 0],
            "filename_prefix": f"{comfy_subfolder(project_id)}/{prefix}" if project_id else f"video/{prefix}",
            "format": "auto", "codec": "auto",
        }},
    }

    vram = await comfy_vram()
    logger.info(
        f"Wan 2.1: {unet}, {frames} frames, {preset['steps']} steps ({WAN_QUALITY})"
        + (f", GPU memory {vram[0]:.1f}/{vram[1]:.1f} GB in use" if vram else "")
    )
    # A 14B FP8 checkpoint (16.4 GB) does not fit in 16 GB of VRAM; ComfyUI then streams part of it
    # from system RAM. That is slower but normal — it is not an error.
    if vram and not unet.endswith(".gguf") and vram[1] < 20:
        logger.warning(
            f"Wan 2.1 FP8 checkpoint ({unet}) is larger than this GPU's {vram[1]:.0f} GB VRAM; ComfyUI will offload "
            "part of it to system RAM. A 480p GGUF Q4_K_M/Q5_K_M checkpoint fits fully in VRAM and runs faster."
        )

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            r = await client.post(f"{COMFYUI_URL}/prompt", json={"prompt": wan_prompt})
            r.raise_for_status()
            prompt_id = r.json()["prompt_id"]

            t0 = time.time()
            # Generation time grows with frames x steps; allow up to 25 minutes per scene
            while time.time() - t0 < 1500:
                hist = (await client.get(f"{COMFYUI_URL}/history/{prompt_id}")).json()
                if prompt_id in hist:
                    status = hist[prompt_id].get("status", {})
                    if status.get("status_str") == "error":
                        logger.warning(f"Wan 2.1 ComfyUI error: {status}")
                        return False
                    if status.get("completed"):
                        save_node = hist[prompt_id].get("outputs", {}).get("56", {})
                        video_list = save_node.get("images", []) or save_node.get("videos", [])
                        if video_list:
                            vid_info = video_list[0]
                            vid_resp = await client.get(
                                f"{COMFYUI_URL}/view",
                                params={"filename": vid_info["filename"], "subfolder": vid_info.get("subfolder", "video"), "type": "output"},
                            )
                            if vid_resp.status_code == 200:
                                raw_clip_path.write_bytes(vid_resp.content)
                                logger.info(f"Wan 2.1 video generated in {time.time() - t0:.0f}s: {raw_clip_path}")
                                return True
                            disk_file = COMFYUI_OUTPUT / vid_info.get("subfolder", "video") / vid_info["filename"]
                            if disk_file.exists():
                                shutil.copy(disk_file, raw_clip_path)
                                return True
                await asyncio.sleep(2.0)
    except Exception as e:
        logger.warning(f"Wan 2.1 animation failed or timed out: {e}")
        return False

    return False


def frames_for(duration: float, fps: int = VIDEO_FPS) -> int:
    return max(1, round(duration * fps))


def fit_clip_to_duration(raw_video: Path, target_duration: float, aspect: str, final_video: Path,
                         resolution: int = 1080, fps: int = VIDEO_FPS) -> Path:
    """Fits an AI motion clip to the scene length without reversing it.

    A clip that is a little short is slowed down (up to 1.3x); anything left over holds the last
    frame. The result is exactly frames_for(target_duration, fps) frames.
    """
    rw, rh = render_size(aspect, resolution)
    clip_len = max(0.1, get_audio_duration(raw_video))  # ffprobe format duration works for video too
    stretch = min(1.3, max(1.0, target_duration / clip_len))
    fade_d = min(0.3, target_duration / 4)
    vf = (
        f"setpts={stretch:.4f}*PTS,fps={fps},"
        f"scale={rw}:{rh}:force_original_aspect_ratio=increase:flags=lanczos,crop={rw}:{rh},"
        f"tpad=stop_mode=clone:stop_duration={target_duration:.3f},"
        f"fade=t=in:st=0:d={fade_d:.2f},fade=t=out:st={max(0.0, target_duration - fade_d):.2f}:d={fade_d:.2f}"
    )
    cmd = [
        FFMPEG, "-y", "-i", str(raw_video), "-vf", vf, "-an",
        "-frames:v", str(frames_for(target_duration, fps)),
        *video_encoder_args(20, (rw, rh), fps), "-pix_fmt", "yuv420p", "-r", str(fps),
        str(final_video),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return final_video


def snap_audio_to_frames(audio_path: Path, fps: int = VIDEO_FPS) -> float:
    """Pads/trims a scene's audio to a whole number of video frames and returns the new duration.

    Each scene clip is a whole number of frames; without this the tiny remainders add up over
    many scenes and the narration drifts away from the picture.
    """
    if not audio_path.exists():
        logger.warning(f"snap_audio_to_frames: audio file not found: {audio_path}")
        return 0.0
    duration = get_audio_duration(audio_path)
    target = frames_for(duration, fps) / fps
    if abs(target - duration) < 0.0005:
        return duration
    tmp = audio_path.with_name(f"{audio_path.stem}_snap{audio_path.suffix}")
    res = subprocess.run(
        [FFMPEG, "-y", "-i", str(audio_path), "-af", f"apad=whole_dur={target:.4f},atrim=end={target:.4f}", str(tmp)],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        err = res.stderr.strip() if res.stderr else f"ffmpeg exited with {res.returncode}"
        raise RuntimeError(f"FFmpeg snap_audio_to_frames failed for {audio_path.name}: {err}")
    os.replace(tmp, audio_path)
    return get_audio_duration(audio_path)


def create_fallback_motion_clip(image_path: Path, duration: float, aspect: str, output_path: Path, motion_type: str = "zoom_in",
                                resolution: int = 1080, fps: int = VIDEO_FPS) -> Path:
    """High-quality Ken Burns camera motion with multi-axis movements, upscale headroom, and smooth fade transitions"""
    rw, rh = render_size(aspect, resolution)
    total_frames = frames_for(duration, fps)

    # Upscale for zoompan headroom (2x; 1.5x above 1080p to keep 1440p renders manageable)
    headroom = 2 if max(rw, rh) <= 1920 else 1.5
    scale_w = int(rw * headroom) // 2 * 2
    scale_h = int(rh * headroom) // 2 * 2
    # zoompan steps once per frame: scale the per-frame zoom so motion speed is the same at any fps
    step = 30 / fps

    # Smooth Ken Burns camera movements
    if motion_type == "zoom_in":
        # Slow cinematic zoom in from 1.0 to 1.15
        vf = f"scale={scale_w}:{scale_h},zoompan=z='min(zoom+{0.0008 * step:.6f},1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    elif motion_type == "zoom_out":
        # Slow cinematic zoom out from 1.15 to 1.0
        vf = f"scale={scale_w}:{scale_h},zoompan=z='if(lte(zoom,1.0),1.15,max(1.001,zoom-{0.0008 * step:.6f}))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
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
        vf = f"scale={scale_w}:{scale_h},zoompan=z='min(zoom+{0.0003 * step:.6f},1.04)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"

    # Soft cinematic dissolve/fade transition at clip boundaries (0.35s in, 0.35s out)
    fade_d = min(0.35, duration / 4)
    fade_out_st = max(0.1, duration - fade_d)
    vf += f",fade=t=in:st=0:d={fade_d:.2f},fade=t=out:st={fade_out_st:.2f}:d={fade_d:.2f}"

    cmd = [
        FFMPEG, "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf,
        "-frames:v", str(total_frames),
        *video_encoder_args(18, (rw, rh), fps), "-pix_fmt", "yuv420p", "-r", str(fps),
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path

def scene_motion_type(fallback_idx: int, motion_mode: str) -> str:
    mtypes = ["zoom_in", "pan_right", "zoom_out", "tilt_up", "pan_left"]
    return mtypes[fallback_idx % len(mtypes)] if motion_mode != "static" else "static_subtle"

async def animate_scene(image_path: Path, motion_prompt: str, duration: float, aspect: str, output_path: Path, fallback_idx: int = 0, motion_mode: str = "kenburns", project_id: str = "",
                        resolution: int = 1080, fps: int = VIDEO_FPS) -> Path:
    """Full animation controller: supports Ken Burns (Ultra HD), Wan 2.1 AI Motion, and Clean Presentation"""
    chosen_motion = scene_motion_type(fallback_idx, motion_mode)

    if motion_mode == "wan" and not WAN_SUPPORTED:
        logger.info(f"Wan 2.1 is not supported on {sys.platform}; using Ken Burns ({chosen_motion})")
    elif motion_mode == "wan":
        raw_wan = output_path.parent / f"raw_wan_{output_path.stem}.mp4"
        success = await animate_scene_wan(image_path, motion_prompt, aspect, raw_wan, project_id=project_id, duration=duration)
        if success and raw_wan.exists() and raw_wan.stat().st_size > 1000:
            logger.info(f"Fitting Wan 2.1 clip to the scene length ({duration:.2f}s)...")
            await asyncio.to_thread(fit_clip_to_duration, raw_wan, duration, aspect, output_path, resolution, fps)
            return output_path
        logger.info(f"Wan 2.1 unavailable or timed out; falling back to Ken Burns ({chosen_motion})")

    # Ultra HD Ken Burns camera motion (recommended, 100% distortion-free)
    # FFmpeg runs in a thread so the API stays responsive while it renders
    logger.info(f"Rendering Ken Burns motion ({chosen_motion}) with smooth fade transitions for {output_path.name}")
    await asyncio.to_thread(create_fallback_motion_clip, image_path, duration, aspect, output_path,
                            motion_type=chosen_motion, resolution=resolution, fps=fps)
    return output_path

# Auto-balance targets: narration sits at a standard speech loudness and the music bed
# ~14 LU below it, so speech stays clear before any ducking is applied.
VOICE_TARGET_LUFS = -16
MUSIC_TARGET_LUFS = -30


# Scene music levels from the script planner, relative to the auto-balanced bed.
# Even "high" stays ~11 LU under the narration, and ducking still lowers it while someone speaks.
MUSIC_LEVEL_GAIN = {"low": 0.6, "medium": 1.0, "high": 1.45}
MUSIC_RAMP = 1.2  # seconds to glide between two scene levels


def music_envelope(levels: list[str], durations: list[float]) -> str:
    """ffmpeg volume expression (in t) that follows each scene's music level with smooth ramps."""
    gains = [MUSIC_LEVEL_GAIN.get(lv, 1.0) for lv in levels] or [1.0]
    if all(abs(g - gains[0]) < 1e-6 for g in gains):
        return f"{gains[0]:.3f}"
    ramp = min(MUSIC_RAMP, 0.8 * min(durations))
    # Ordered (until_time, value) pieces: hold a level, then glide to the next across the boundary
    pieces: list[tuple[float, str]] = []
    boundary = 0.0
    for i in range(len(gains) - 1):
        boundary += durations[i]
        start, end = boundary - ramp / 2, boundary + ramp / 2
        pieces.append((start, f"{gains[i]:.3f}"))
        if abs(gains[i + 1] - gains[i]) > 1e-6:
            pieces.append((end, f"({gains[i]:.3f}+({gains[i + 1] - gains[i]:.3f})*(t-{start:.3f})/{ramp:.3f})"))
    expr = f"{gains[-1]:.3f}"
    for until, value in reversed(pieces):
        expr = f"if(lt(t,{until:.3f}),{value},{expr})"
    return expr


_FILTER_CACHE: dict[str, bool] = {}


def ffmpeg_has_filter(name: str) -> bool:
    """Whether this ffmpeg build includes a filter (e.g. 'ass' needs ffmpeg built with libass)."""
    if name not in _FILTER_CACHE:
        try:
            out = subprocess.run([FFMPEG, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=10).stdout
            _FILTER_CACHE[name] = any(line.split()[1:2] == [name] for line in out.splitlines() if len(line.split()) > 1)
        except (OSError, subprocess.SubprocessError):
            _FILTER_CACHE[name] = False
    return _FILTER_CACHE[name]


def _gain(percent: int) -> float:
    """UI level (100 = auto-balanced) -> linear gain, clamped to 0–200%."""
    return max(0, min(200, int(percent))) / 100


def format_srt_time(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))  # round once, so .9996s can't become ",1000"
    hrs, rem = divmod(total_ms, 3_600_000)
    mins, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def generate_srt_subtitles(scenes: list[dict], scene_durations: list[float], output_srt: Path) -> Path:
    """Generates standard UTF-8 SRT subtitles synchronized with scene shot progressions."""
    lines = []
    current_time = 0.0
    sub_idx = 1
    for sc, dur in zip(scenes, scene_durations):
        raw_text = sc.get("narration", "")
        shots = split_scene_into_shots(raw_text, dur)
        for sh in shots:
            clean_text = re.sub(r"\[[^\]]+\]", "", sh.get("text", "")).strip()
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            shot_dur = sh.get("duration", dur)
            if not clean_text:
                current_time += shot_dur
                continue

            start_time = current_time
            end_time = max(start_time + 0.5, current_time + shot_dur - 0.06)

            lines.append(f"{sub_idx}")
            lines.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
            lines.append(clean_text)
            lines.append("")
            sub_idx += 1
            current_time += shot_dur

    output_srt.write_text("\n".join(lines), encoding="utf-8")
    return output_srt

def format_ass_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = min(99, int(round((seconds - int(seconds)) * 100)))
    return f"{hrs:d}:{mins:02d}:{secs:02d}.{centis:02d}"

def generate_ass_subtitles(scenes: list[dict], scene_durations: list[float], aspect: str, output_ass: Path) -> Path:
    """Generates standard UTF-8 ASS subtitles with Nirmala UI font synchronized with scene shot progressions."""
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    rw, rh = dims["render_w"], dims["render_h"]
    is_vertical = rh > rw
    # Balanced font size: elegant, modern, highly legible
    font_size = 46 if is_vertical else 38
    margin_v = 150 if is_vertical else 80
    outline = 2.8 if is_vertical else 2.2

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {rw}
PlayResY: {rh}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Nirmala UI,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,{outline:.1f},1.2,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogues = []
    current_time = 0.0
    for sc, dur in zip(scenes, scene_durations):
        raw_text = sc.get("narration", "")
        shots = split_scene_into_shots(raw_text, dur)
        for sh in shots:
            clean_text = re.sub(r"\[[^\]]+\]", "", sh.get("text", "")).strip()
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            shot_dur = sh.get("duration", dur)
            if not clean_text:
                current_time += shot_dur
                continue

            start_time = current_time
            end_time = max(start_time + 0.5, current_time + shot_dur - 0.06)
            dialogues.append(f"Dialogue: 0,{format_ass_time(start_time)},{format_ass_time(end_time)},Default,,0,0,0,,{clean_text}")
            current_time += shot_dur

    output_ass.write_text(header + "\n".join(dialogues) + "\n", encoding="utf-8")
    return output_ass

    output_ass.write_text(header + "\n".join(dialogues) + "\n", encoding="utf-8")
    return output_ass


def assemble_final_video(
    scene_videos: list[Path],
    scene_audios: list[Path],
    output_path: Path,
    aspect: str,
    music_file: Path | None = None,
    music_volume: int = 100,
    voice_volume: int = 100,
    music_ducking: bool = True,
    enable_subtitles: bool = True,
    subtitles_file: Path | None = None,
    music_levels: list[str] | None = None,
    resolution: int = 1080,
    fps: int = VIDEO_FPS,
) -> Path:
    """Concatenates scene clips and the voiceover, optionally mixing in a background music bed
    with silky smooth fade transitions and dynamic sidechain ducking. Optionally burns synchronized
    subtitles onto the video.
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

    # Determine video encoding: burn subtitles if enabled and subtitle file exists
    use_subs = enable_subtitles and subtitles_file is not None and subtitles_file.exists() and subtitles_file.stat().st_size > 10
    sub_filter = "ass" if subtitles_file is not None and subtitles_file.suffix.lower() == ".ass" else "subtitles"
    if use_subs and not ffmpeg_has_filter(sub_filter):
        logger.warning(
            f"This ffmpeg build has no '{sub_filter}' filter (it needs libass), so captions are not burned in. "
            "The .srt subtitle file is still saved. Install an ffmpeg built with libass to burn captions."
        )
        use_subs = False
    if use_subs:
        logger.info(f"Burning subtitles onto video from {subtitles_file.name}...")
        posix_path = subtitles_file.resolve().as_posix()
        escaped_path = posix_path.replace(":", r"\:")
        filter_name = "ass" if subtitles_file.suffix.lower() == ".ass" else "subtitles"
        vf_sub = f"{filter_name}=filename='{escaped_path}'"
        video_args = ["-vf", vf_sub, *video_encoder_args(20, render_size(aspect, resolution), fps), "-pix_fmt", "yuv420p"]
    else:
        video_args = ["-c:v", "copy"]

    if use_music:
        total_dur = get_audio_duration(full_voice)
        fade_out = min(3.5, max(1.0, total_dur / 5))
        fade_out_start = max(0.0, total_dur - fade_out)
        logger.info(
            f"Mixing background music: {music_file.name} (music {music_volume}%, voice {voice_volume}%, ducking {'on' if music_ducking else 'off'})"
        )
        # Per-scene emotional level (low / medium / high) with smooth glides between scenes
        envelope = music_envelope(music_levels or [], [get_audio_duration(a) for a in scene_audios]) if music_levels else "1.0"
        # Smooth S-curve / sine fade-in (2.5s) and gentle fade-out at the end
        music_chain = (
            f"[2:a]aresample=48000,loudnorm=I={MUSIC_TARGET_LUFS}:TP=-8:LRA=11,aresample=48000,"
            f"volume={_gain(music_volume):.2f},volume='{envelope}':eval=frame,"
            f"afade=t=in:st=0:d=2.5:curve=esin,afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f}:curve=esin[bg];"
        )
        if music_ducking:
            # Professional smooth ducking: attack=45ms (gentle drop), release=700ms (silky recovery), knee=2.8
            filter_complex = (
                f"[1:a]{voice_chain},asplit=2[voice][sc];"
                + music_chain
                + "[bg][sc]sidechaincompress=threshold=0.035:ratio=4.5:attack=45:release=700:knee=2.8[bed];"
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
            *video_args,
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
            *video_args,
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
    subprocess.run(cmd, check=True, capture_output=True, cwd=str(job_dir))

    return output_path
