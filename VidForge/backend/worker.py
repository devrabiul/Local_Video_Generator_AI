import asyncio
import json
import shutil
import time
import traceback
from pathlib import Path
from loguru import logger
from database import get_next_queued_job, update_job_status
import ai_engine

BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "jobs"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

async def process_job(job: dict):
    job_id = job["id"]
    work_dir = JOBS_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting job {job_id} | Language: {job['language']} | Aspect: {job['aspect_ratio']}")

    try:
        # Step 1: Script & Scene Planning
        scenes = []
        if job.get("scenes_json") and job["scenes_json"] != "[]":
            try:
                scenes = json.loads(job["scenes_json"])
                logger.info(f"Using {len(scenes)} pre-planned scenes from Ollama Story Studio")
            except Exception:
                scenes = []

        if not scenes:
            update_job_status(job_id, status="SCRIPTING", progress=10, current_step="Generating narrative scenes with Ollama...")
            plan = await ai_engine.plan_story(job["story_prompt"], job["language"])
            scenes = plan.get("scenes", [])
            title = plan.get("title", job.get("title") or "Untitled Story")
            if not scenes:
                raise ValueError("Ollama failed to generate scenes")
        else:
            title = job.get("title") or "Untitled Story"

        update_job_status(job_id, status="SCRIPTING", progress=25, current_step=f"Ready with {len(scenes)} scenes: {title}", scenes_json=json.dumps(scenes, ensure_ascii=False))

        # Step 2: Voiceover generation (ElevenLabs / F5-TTS / Edge-TTS)
        voice_label = job.get("voice", "neural")
        update_job_status(job_id, status="VOICEOVER", progress=30, current_step=f"Generating voiceover using {voice_label}...")
        scene_audios = []
        scene_durations = []
        for i, sc in enumerate(scenes):
            audio_path = work_dir / f"scene_{i+1}.mp3"
            await ai_engine.generate_voiceover(sc["narration"], job["voice"], audio_path)
            duration = ai_engine.get_audio_duration(audio_path)
            sc["duration"] = duration
            scene_audios.append(audio_path)
            scene_durations.append(duration)
            logger.info(f"Scene {i+1} audio duration: {duration:.2f}s")

        update_job_status(job_id, status="VOICEOVER", progress=45, current_step="Voiceover complete. Starting AI image generation...", scenes_json=json.dumps(scenes, ensure_ascii=False))

        # Step 3: Visual Generation with ComfyUI Z-Image-Turbo
        update_job_status(job_id, status="GENERATING_IMAGES", progress=50, current_step="Rendering base visuals in ComfyUI...")
        scene_images = []
        for i, sc in enumerate(scenes):
            img_path = work_dir / f"scene_{i+1}.png"
            update_job_status(job_id, status="GENERATING_IMAGES", progress=50 + int((i / len(scenes)) * 20), current_step=f"Generating image {i+1}/{len(scenes)}...")
            await ai_engine.generate_scene_image(sc["visual_prompt"], job["aspect_ratio"], img_path)
            sc["image"] = str(img_path)
            scene_images.append(img_path)

        # Step 4: Character & Scene Animation with Wan 2.1 I2V
        update_job_status(job_id, status="ANIMATING_VIDEO", progress=72, current_step="Animating characters & scenes with Wan 2.1 I2V...")
        scene_videos = []
        for i, (img_path, dur, sc) in enumerate(zip(scene_images, scene_durations, scenes)):
            vid_path = work_dir / f"scene_{i+1}.mp4"
            motion_desc = sc.get("motion_prompt", "character moving and breathing naturally, cinematic camera motion")
            update_job_status(job_id, status="ANIMATING_VIDEO", progress=72 + int((i / len(scenes)) * 20), current_step=f"Animating character motion for scene {i+1}/{len(scenes)}...")
            await ai_engine.animate_scene(img_path, motion_desc, dur, job["aspect_ratio"], vid_path, fallback_idx=i)
            scene_videos.append(vid_path)

        # Step 5: Final Composition & Cinematic Soundtrack Mix
        update_job_status(job_id, status="COMPOSING", progress=94, current_step="Mixing cinematic music track with audio ducking...")
        final_mp4 = OUTPUT_DIR / f"{job_id}.mp4"
        thumbnail = OUTPUT_DIR / f"{job_id}_thumb.png"

        ai_engine.assemble_final_video(scene_videos, scene_audios, final_mp4, job["aspect_ratio"], music_theme="cinematic_epic")
        if scene_images:
            shutil.copy(scene_images[0], thumbnail)

        update_job_status(
            job_id,
            status="DONE",
            progress=100,
            current_step="Video complete and ready to watch!",
            output_video=f"/output/{job_id}.mp4",
            thumbnail=f"/output/{job_id}_thumb.png",
            scenes_json=json.dumps(scenes, ensure_ascii=False)
        )
        logger.success(f"Job {job_id} successfully completed! Saved to {final_mp4}")

    except Exception as e:
        err = traceback.format_exc()
        logger.error(f"Job {job_id} failed: {err}")
        update_job_status(job_id, status="FAILED", error_message=str(e), current_step="Error occurred during generation")

async def worker_loop():
    logger.info("VidForge Queue Worker initialized and polling for jobs...")
    while True:
        try:
            job = get_next_queued_job()
            if job:
                await process_job(job)
            else:
                await asyncio.sleep(2.0)
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(3.0)
