import asyncio
import json
import os
import random
import shutil
import subprocess
import time
from pathlib import Path
import httpx
from loguru import logger
import edge_tts

BASE_DIR = Path(__file__).resolve().parent.parent
OLLAMA_URL = "http://127.0.0.1:11434"
COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT = Path("D:/AI/ComfyUI_windows_portable/ComfyUI/input")
COMFYUI_OUTPUT = Path("D:/AI/ComfyUI_windows_portable/ComfyUI/output")
WORKFLOWS_DIR = BASE_DIR / "workflows"
MUSIC_DIR = BASE_DIR / "music"

ASPECT_RESOLUTIONS = {
    "9:16": {"width": 768, "height": 1344, "render_w": 1080, "render_h": 1920, "wan_w": 480, "wan_h": 832},
    "16:9": {"width": 1344, "height": 768, "render_w": 1920, "render_h": 1080, "wan_w": 832, "wan_h": 480}
}

VOICES = {
    "bn": {
        "bn-BD-PradeepNeural": "Pradeep (বাংলাদেশী গম্ভীর ড্রামাটিক পুরুষ - Epic & Cinematic)",
        "bn-BD-NabanitaNeural": "Nabanita (বাংলাদেশী সাবলীল আবেগঘন নারী - Soft & Narrative)",
        "bn-IN-BashkarNeural": "Bashkar (পশ্চিমবঙ্গীয় ক্লাসিক বর্ণনাকারী পুরুষ - Classic Doc)",
        "bn-IN-TanishaaNeural": "Tanishaa (পশ্চিমবঙ্গীয় আবেগঘন স্পষ্ট নারী - Modern & Clear)"
    },
    "hi": {
        "hi-IN-MadhurNeural": "Madhur (गंभीर कथावाचक पुरुष - Epic Hindi)",
        "hi-IN-SwaraNeural": "Swara (भावुक महिला स्वर - Emotional Hindi)"
    },
    "en": {
        "en-US-ChristopherNeural": "Christopher (US Male - Deep & Authoritative Documentary)",
        "en-GB-RyanNeural": "Ryan (UK Male - Epic Historical British)",
        "en-US-GuyNeural": "Guy (US Male - Cinematic Storyteller)",
        "en-US-BrianMultilingualNeural": "Brian (US Male - Crisp & Expressive)",
        "en-US-AriaNeural": "Aria (US Female - Cinematic & Engaging)",
        "en-US-EmmaMultilingualNeural": "Emma (US Female - Warm & Emotional)",
        "en-GB-SoniaNeural": "Sonia (UK Female - Sophisticated British Narration)",
        "en-IN-PrabhatNeural": "Prabhat (Indian English Male - Clear & Articulate)",
        "en-IN-NeerjaExpressiveNeural": "Neerja (Indian English Female - Expressive & Vivid)"
    },
    "ur": {
        "ur-PK-AsadNeural": "Asad (پاکستانی گہرا مردانہ بیان - Epic Male)",
        "ur-PK-UzmaNeural": "Uzma (پاکستانی جذباتی زنانہ آواز - Expressive Female)",
        "ur-IN-SalmanNeural": "Salman (بھارتی کلاسیک مردانہ آواز - Indian Urdu Male)",
        "ur-IN-GulNeural": "Gul (بھارتی نرم زنانہ آواز - Warm Indian Urdu Female)"
    },
    "ar": {
        "ar-SA-HamedNeural": "Hamed (عربي سعودي عميق - Epic Historical Male)",
        "ar-SA-ZariyahNeural": "Zariyah (عربي سعودي واضح - Clear Arabic Female)"
    }
}

ELEVENLABS_VOICES = {
    "pNInz6obpgDQGcFmaJgB": {
        "name": "Adam",
        "description": "Deep, Authoritative Narration - US Male (Documentary & Epic)",
        "gender": "male",
        "lang": "multilingual"
    },
    "ErXwobaYiN019PkySvjV": {
        "name": "Antoni",
        "description": "Dramatic Storyteller & Engaging - US Male",
        "gender": "male",
        "lang": "multilingual"
    },
    "JBFqnCBsd6RMkjVDRZzb": {
        "name": "George",
        "description": "Warm, Eloquent British Documentary - UK Male",
        "gender": "male",
        "lang": "multilingual"
    },
    "21m00Tcm4TlvDq8ikWAM": {
        "name": "Rachel",
        "description": "Calm, Intimate & Clear Narration - US Female",
        "gender": "female",
        "lang": "multilingual"
    },
    "EXAVITQu4vr4xnSDxMaL": {
        "name": "Bella",
        "description": "Expressive, Vibrant & Emotional - US Female",
        "gender": "female",
        "lang": "multilingual"
    },
    "onwK4e9ZLuTAKqWW03F9": {
        "name": "Daniel",
        "description": "Authoritative, Deep Broadcast - UK Male",
        "gender": "male",
        "lang": "multilingual"
    },
    "TX3LPaxmHKxFdv7VOQHJ": {
        "name": "Liam",
        "description": "Young, Energetic & Direct - US Male",
        "gender": "male",
        "lang": "multilingual"
    }
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

SAMPLE_PHRASES = {
    "bn": "স্বাগতম VidForge এ। আমি আপনার ঐতিহাসিক কাহিনীর কণ্ঠস্বর।",
    "hi": "VidForge में आपका स्वागत है। मैं आपकी कहानी का स्वर हूँ।",
    "en": "Welcome to VidForge AI Studio. I am your cinematic narrator.",
    "ur": "VidForge میں خوش آمدید۔ میں آپ کی کہانی کی آواز ہوں۔",
    "ar": "مرحباً بكم في استوديو VidForge للذكاء الاصطناعي."
}

CONFIG_FILE = BASE_DIR / "backend" / "config.json"
if not CONFIG_FILE.exists():
    CONFIG_FILE = BASE_DIR / "config.json"

def get_tts_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"elevenlabs_api_key": "", "default_engine": "edge"}

def save_tts_config(data: dict) -> dict:
    cfg = get_tts_config()
    cfg.update(data)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg

def get_all_tts_engines() -> dict:
    cfg = get_tts_config()
    has_eleven_key = bool(cfg.get("elevenlabs_api_key"))
    return {
        "edge": {
            "name": "Edge-TTS (Standard & Fast)",
            "description": "Fast multilingual neural voices provided by Microsoft",
            "voices": VOICES
        },
        "elevenlabs": {
            "name": "ElevenLabs Studio (Ultra-Realistic Human)",
            "description": "Hyper-realistic emotion, breaths, pauses, and cadence",
            "configured": has_eleven_key,
            "voices": ELEVENLABS_VOICES
        },
        "f5tts": {
            "name": "F5-TTS (Local Zero-Shot Voice Cloning)",
            "description": "Local AI voice cloning running on your RTX 5070 Ti GPU",
            "ready": True,
            "voices": F5_PRESET_VOICES
        }
    }

PYTHON_EMBEDDED = Path("D:/AI/ComfyUI_windows_portable/python_embeded/python.exe")
F5_CLI_SCRIPT = BASE_DIR / "backend" / "f5_infer_cli.py"
REF_VOICES_DIR = BASE_DIR / "backend" / "ref_voices"

async def generate_elevenlabs_voiceover(text: str, voice_id: str, output_path: Path, api_key: str = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not api_key:
        cfg = get_tts_config()
        api_key = cfg.get("elevenlabs_api_key") or os.environ.get("ELEVENLABS_API_KEY", "")
    
    if not api_key:
        raise ValueError("ElevenLabs API Key is required. Please add your API key in ElevenLabs settings.")
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key.strip(),
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(url, json=payload, headers=headers)
        if res.status_code != 200:
            err_msg = res.text
            try:
                err_json = res.json()
                err_msg = err_json.get("detail", {}).get("message") or err_json.get("message") or res.text
            except Exception:
                pass
            raise RuntimeError(f"ElevenLabs error ({res.status_code}): {err_msg}")
        output_path.write_bytes(res.content)
    return output_path

async def generate_f5_voiceover(text: str, ref_key: str, output_path: Path, ref_audio_custom: str = None, ref_text_custom: str = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ref_file = None
    ref_txt = ""

    if ref_audio_custom and Path(ref_audio_custom).exists():
        ref_file = Path(ref_audio_custom)
        ref_txt = ref_text_custom or ""
    elif ref_key in F5_PRESET_VOICES:
        meta = F5_PRESET_VOICES[ref_key]
        candidate = REF_VOICES_DIR / meta["file"]
        if candidate.exists():
            ref_file = candidate
            ref_txt = meta["text"]

    if not ref_file or not ref_file.exists():
        ref_file = REF_VOICES_DIR / "en_nature.wav"
        ref_txt = "Some call me nature, others call me mother nature."

    cmd = [
        str(PYTHON_EMBEDDED),
        str(F5_CLI_SCRIPT),
        "--ref_audio", str(ref_file),
        "--ref_text", ref_txt,
        "--gen_text", text,
        "--output", str(output_path),
        "--speed", "1.0",
        "--remove_silence"
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err_msg = stderr.decode(errors="replace")
        logger.error(f"F5-TTS failed: {err_msg}")
        raise RuntimeError(f"F5-TTS error: {err_msg}")
    
    return output_path

async def generate_voice_sample(voice: str, engine: str = "edge", ref_audio: str = "", ref_text: str = "", api_key: str = "") -> str:
    """Generates an audio preview for a voice from any engine and caches it"""
    samples_dir = BASE_DIR / "output" / "voice_samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    
    clean_voice = voice.replace(":", "_").replace("/", "_").replace("\\", "_")
    sample_file = samples_dir / f"{engine}_{clean_voice}.mp3"
    
    if not sample_file.exists() or sample_file.stat().st_size == 0:
        phrase = SAMPLE_PHRASES["en"]
        if clean_voice.startswith("bn") or "bn" in clean_voice or voice in ("bn_epic_male", "bn_soft_female"):
            phrase = SAMPLE_PHRASES["bn"]
        elif clean_voice.startswith("hi") or "hi" in clean_voice:
            phrase = SAMPLE_PHRASES["hi"]

        await generate_voiceover(
            text=phrase,
            voice=voice,
            output_path=sample_file,
            tts_engine=engine,
            ref_audio=ref_audio,
            ref_text=ref_text,
            api_key=api_key
        )
        
    return f"/output/voice_samples/{engine}_{clean_voice}.mp3"

async def generate_story_script(
    topic: str,
    language: str = "bn",
    model: str = "story-writer:latest",
    genre: str = "historical",
    tone: str = "epic",
    scene_count: int = 5
) -> dict:
    """Uses Ollama to generate a structured storyboard script"""
    lang_names = {
        "bn": "Bengali (বাংলা)",
        "hi": "Hindi (हिन्दी)",
        "en": "English",
        "ur": "Urdu (اردو)",
        "ar": "Arabic (العربية)"
    }
    target_lang = lang_names.get(language, "Bengali (বাংলা)")
    
    system_prompt = f"""You are a master cinematic film director and historical storyteller.
Generate a cohesive, thrilling, cinematic script with EXACTLY {scene_count} chronological scenes based on the user's topic.
Genre: {genre}
Tone: {tone}

Requirements for each scene:
1. "narration": The spoken voiceover script STRICTLY in {target_lang}. Make it deeply evocative, epic, dramatic, and emotionally moving with natural pauses (... and —).
2. "visual_prompt": A highly detailed visual description written in English for 8K photorealistic cinematic image generation (e.g. lighting, camera angle, character appearance, mood, historical authenticity).
3. "motion_prompt": A specific character and camera motion description in English for AI video animation (e.g. "slow cinematic push in, character breathing heavily, cape fluttering in wind, dust drifting").

Respond ONLY with valid JSON in this exact structure:
{{
  "title": "Short Gripping Title",
  "synopsis": "Brief 1-2 sentence overview of the storyline",
  "scenes": [
    {{
      "id": 1,
      "narration": "Voiceover line in {target_lang}",
      "visual_prompt": "Cinematic visual description in English",
      "motion_prompt": "Motion description in English"
    }}
  ]
}}"""

    async with httpx.AsyncClient(timeout=240.0) as client:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Topic / Story Concept:\n{topic}"}
            ],
            "stream": False,
            "format": "json"
        }
        res = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        res.raise_for_status()
        content = res.json()["message"]["content"]
        return json.loads(content)

async def get_active_ollama_model() -> str:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if "story-writer:latest" in models:
                    return "story-writer:latest"
                if "qwen3.5:9b" in models:
                    return "qwen3.5:9b"
                if models:
                    return models[0]
    except Exception:
        pass
    return "story-writer:latest"

async def plan_story(prompt: str, language: str, model: str = None) -> dict:
    if not model:
        model = await get_active_ollama_model()
    return await generate_story_script(
        topic=prompt,
        language=language,
        model=model,
        genre="historical drama",
        tone="cinematic epic",
        scene_count=5
    )

async def generate_voiceover(
    text: str,
    voice: str,
    output_path: Path,
    tts_engine: str = "edge",
    ref_audio: str = "",
    ref_text: str = "",
    api_key: str = ""
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Detect engine from voice prefix if embedded
    if voice.startswith("elevenlabs:"):
        tts_engine = "elevenlabs"
        voice = voice.replace("elevenlabs:", "")
    elif voice.startswith("f5:") or voice.startswith("f5tts:"):
        tts_engine = "f5-tts"
        voice = voice.replace("f5tts:", "").replace("f5:", "")
    elif voice.startswith("edge:"):
        tts_engine = "edge"
        voice = voice.replace("edge:", "")

    logger.info(f"Generating voiceover: engine='{tts_engine}', voice='{voice}'")

    if tts_engine == "elevenlabs":
        return await generate_elevenlabs_voiceover(text=text, voice_id=voice, output_path=output_path, api_key=api_key)
    elif tts_engine in ("f5-tts", "f5tts"):
        return await generate_f5_voiceover(text=text, ref_key=voice, output_path=output_path, ref_audio_custom=ref_audio, ref_text_custom=ref_text)
    else:
        # Edge-TTS with cinematic -4% rate and -1Hz pitch
        communicate = edge_tts.Communicate(text=text, voice=voice, rate="-4%", pitch="-1Hz")
        await communicate.save(str(output_path))
        return output_path

def get_audio_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

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
                "text": f"{motion_prompt}, cinematic motion, character moving naturally, dynamic lighting"
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "clip": ["38", 0],
                "text": "blurry, static, distorted, artifacts, low quality, jittery"
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
                "length": 17, # 17 frames at 16fps = 1.06s base motion
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
                "steps": 10,
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
        "ffmpeg", "-y",
        "-i", str(raw_video),
        "-filter_complex", filter_str,
        "-map", "[vloop]",
        "-t", f"{target_duration:.2f}",
        "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "20", "-pix_fmt", "yuv420p",
        str(final_video)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return final_video

def create_fallback_motion_clip(image_path: Path, duration: float, aspect: str, output_path: Path, motion_type: str = "zoom_in") -> Path:
    """High-quality Ken Burns camera motion fallback with multi-axis movement and subtle camera sway"""
    dims = ASPECT_RESOLUTIONS.get(aspect, ASPECT_RESOLUTIONS["9:16"])
    rw, rh = dims["render_w"], dims["render_h"]
    fps = 30
    total_frames = max(30, int(duration * fps))

    if motion_type == "zoom_in":
        vf = f"scale={rw*2}:{rh*2},zoompan=z='min(zoom+0.0018,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    elif motion_type == "zoom_out":
        vf = f"scale={rw*2}:{rh*2},zoompan=z='if(lte(zoom,1.0),1.25,max(1.001,zoom-0.0018))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"
    else: # Pan with slight zoom
        vf = f"scale={rw*2}:{rh*2},zoompan=z='1.18':x='(it/{duration})*(iw-iw/zoom)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={rw}x{rh}:fps={fps}"

    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
        "-vf", vf,
        "-t", f"{duration:.2f}",
        "-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19", "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path

async def animate_scene(image_path: Path, motion_prompt: str, duration: float, aspect: str, output_path: Path, fallback_idx: int = 0) -> Path:
    """Full animation controller: tries Wan 2.1 I2V character motion first, falls back gracefully if needed"""
    raw_wan = output_path.parent / f"raw_wan_{output_path.stem}.mp4"
    success = await animate_scene_wan(image_path, motion_prompt, aspect, raw_wan)
    if success and raw_wan.exists() and raw_wan.stat().st_size > 1000:
        logger.info(f"Applying seamless ping-pong loop to Wan 2.1 clip for duration {duration:.2f}s...")
        extend_video_to_duration(raw_wan, duration, aspect, output_path)
        return output_path
    
    # Fallback to enhanced dynamic motion
    logger.info(f"Using enhanced dynamic camera motion for {output_path.name}")
    mtypes = ["zoom_in", "pan", "zoom_out"]
    create_fallback_motion_clip(image_path, duration, aspect, output_path, motion_type=mtypes[fallback_idx % len(mtypes)])
    return output_path

def assemble_final_video(scene_videos: list[Path], scene_audios: list[Path], output_path: Path, aspect: str, music_theme: str = "cinematic_epic") -> Path:
    """Concatenates all animated scene clips and mixes voiceover with sidechain-ducked background music"""
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

    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(full_video)], check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(audio_concat), "-c:a", "pcm_s16le", str(full_voice)], check=True, capture_output=True)

    # Check for background music track
    music_file = MUSIC_DIR / f"{music_theme}.mp3"
    if not music_file.exists():
        # Try alternate music in MUSIC_DIR
        available = list(MUSIC_DIR.glob("*.mp3"))
        if available:
            music_file = available[0]

    if music_file and music_file.exists():
        logger.info(f"Mixing background music: {music_file.name} with audio ducking")
        # Total duration from video
        total_dur = get_audio_duration(full_voice)
        fade_out_start = max(1.0, total_dur - 2.5)

        # Sidechain ducking filter:
        # [1:a] is voice. [2:a] is looped music.
        # sidechaincompress ducks music when voice speaks (threshold 0.08, ratio 4:1)
        # afade fades out music smoothly over the last 2.5 seconds
        filter_complex = (
            f"[2:a]volume=0.35,afade=t=out:st={fade_out_start:.2f}:d=2.5[bg];"
            f"[1:a]asplit=2[sc][voice];"
            f"[bg][sc]sidechaincompress=threshold=0.06:ratio=4:attack=50:release=450[ducked_music];"
            f"[voice][ducked_music]amix=inputs=2:duration=first:dropout_transition=2[aout]"
        )

        cmd = [
            "ffmpeg", "-y",
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
        subprocess.run(cmd, check=True, capture_output=True)
    else:
        # Fallback without music bed
        cmd = [
            "ffmpeg", "-y",
            "-i", str(full_video),
            "-i", str(full_voice),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    return output_path
