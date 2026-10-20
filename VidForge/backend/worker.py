import asyncio
import hashlib
import json
import os
import shutil
import traceback
from pathlib import Path
from loguru import logger
from database import get_next_queued_job, get_job, update_job_status, clear_refine_instruction
import ai_engine
import music_library
import projects
import tts_engine

projects.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
projects.JOBS_DIR.mkdir(parents=True, exist_ok=True)

# Scene assets are named after a hash of everything that shapes them, so a refined
# script only re-renders the scenes whose content actually changed.
SCENE_ASSET_PREFIXES = ("audio_", "image_", "clip_", "raw_wan_", "tmp_", "scene_")


class ProjectDeleted(Exception):
    """The project was deleted while it was rendering."""


def _checkpoint(job_id: str):
    if get_job(job_id) is None:
        raise ProjectDeleted(job_id)


def _asset_key(*parts) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def _remove_unused_scene_assets(work_dir: Path, keep: set[str]):
    for f in work_dir.iterdir():
        if f.is_file() and f.name.startswith(SCENE_ASSET_PREFIXES) and f.name not in keep:
            f.unlink(missing_ok=True)


async def process_job(job: dict):
    job_id = job["id"]
    work_dir = projects.work_dir(job_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting job {job_id} (revision {job.get('revision') or 1}) | Language: {job['language']} | Aspect: {job['aspect_ratio']}")

    try:
        video_type = job.get("video_type") or "story"
        target_duration = int(job.get("target_duration") or 60)
        motion_mode = job.get("motion_mode") or "kenburns"
        aspect = job["aspect_ratio"]
        music_file = music_library.resolve_track(job.get("music_track") or "")
        if job.get("music_track") and not music_file:
            logger.warning(f"Background music '{job['music_track']}' not found; continuing without music")

        # Step 1: Script & Scene Planning
        scenes = []
        narrator_style = job.get("narrator_style") or ""
        if job.get("scenes_json") and job["scenes_json"] != "[]":
            try:
                scenes = json.loads(job["scenes_json"])
                logger.info(f"Using {len(scenes)} pre-planned scenes")
            except Exception:
                scenes = []

        if not scenes:
            update_job_status(job_id, status="SCRIPTING", progress=10, current_step=f"Generating {video_type.title()} script (~{target_duration}s)...")
            plan = await ai_engine.plan_script(
                prompt=job["story_prompt"],
                language=job["language"],
                video_type=video_type,
                target_duration=target_duration
            )
            scenes = plan.get("scenes", [])
            title = plan.get("title", job.get("title") or "Untitled Production")
            narrator_style = plan.get("narrator_style") or narrator_style
            if not scenes:
                raise ValueError(f"Ollama failed to generate {video_type} scenes")
        else:
            title = job.get("title") or "Untitled Production"

        instruction = (job.get("refine_instruction") or "").strip()
        if instruction:
            update_job_status(job_id, status="SCRIPTING", progress=15, current_step=f"Refining script: {instruction[:80]}")
            scenes = await ai_engine.refine_script(title, scenes, instruction, job["language"], video_type)
            clear_refine_instruction(job_id)

        _checkpoint(job_id)
        update_job_status(job_id, status="SCRIPTING", progress=25, current_step=f"Ready with {len(scenes)} scenes: {title}", scenes_json=json.dumps(scenes, ensure_ascii=False))

        # Step 2: Voiceover generation (Gemini / ElevenLabs / F5-TTS)
        voice_label = job.get("voice", "neural")
        update_job_status(job_id, status="VOICEOVER", progress=30, current_step=f"Generating voiceover using {voice_label}...")
        scene_audios = []
        scene_durations = []
        stitch_ids: list[str] = []  # ElevenLabs request stitching keeps the delivery continuous
        for i, sc in enumerate(scenes):
            _checkpoint(job_id)
            # Breathing room between scenes; the scene clip follows the padded audio length
            try:
                pause = float(sc.get("pause_after", 0.6))
            except (TypeError, ValueError):
                pause = 0.6
            pause = min(max(pause, 0.2), 2.0)
            if i == len(scenes) - 1:
                pause = max(pause, 1.0)

            key = _asset_key(sc["narration"], sc.get("delivery", ""), narrator_style, job["voice"], job["language"], round(pause, 2))
            audio_path = work_dir / f"audio_{key}.mp3"
            progress = 30 + int((i / len(scenes)) * 14)
            if audio_path.exists():
                update_job_status(job_id, status="VOICEOVER", progress=progress, current_step=f"Reusing voiceover for scene {i+1}/{len(scenes)}...")
            else:
                update_job_status(job_id, status="VOICEOVER", progress=progress, current_step=f"Voicing scene {i+1}/{len(scenes)}...")
                tmp = work_dir / f"tmp_{audio_path.name}"

                async def _on_voice_status(msg: str):
                    _checkpoint(job_id)
                    update_job_status(job_id, status="VOICEOVER", progress=progress, current_step=msg)

                await tts_engine.generate_voiceover(
                    sc["narration"],
                    job["voice"],
                    tmp,
                    delivery=sc.get("delivery", ""),
                    narrator_style=narrator_style,
                    previous_text=scenes[i - 1]["narration"] if i > 0 else "",
                    next_text=scenes[i + 1]["narration"] if i + 1 < len(scenes) else "",
                    stitch_ids=stitch_ids,
                    language=job["language"],
                    on_status=_on_voice_status
                )
                await asyncio.to_thread(ai_engine.pad_audio_with_silence, tmp, pause)
                os.replace(tmp, audio_path)
            duration = await asyncio.to_thread(ai_engine.get_audio_duration, audio_path)
            sc["duration"] = duration
            scene_audios.append(audio_path)
            scene_durations.append(duration)
            logger.info(f"Scene {i+1} audio duration: {duration:.2f}s")

        update_job_status(job_id, status="VOICEOVER", progress=45, current_step="Voiceover complete. Starting AI image generation...", scenes_json=json.dumps(scenes, ensure_ascii=False))

        # Step 3: Visual Generation with ComfyUI Z-Image-Turbo
        update_job_status(job_id, status="GENERATING_IMAGES", progress=50, current_step="Rendering base visuals in ComfyUI...")
        scene_images = []
        for i, sc in enumerate(scenes):
            _checkpoint(job_id)
            img_path = work_dir / f"image_{_asset_key(sc['visual_prompt'], aspect)}.png"
            progress = 50 + int((i / len(scenes)) * 20)
            if img_path.exists():
                update_job_status(job_id, status="GENERATING_IMAGES", progress=progress, current_step=f"Reusing image {i+1}/{len(scenes)}...")
            else:
                update_job_status(job_id, status="GENERATING_IMAGES", progress=progress, current_step=f"Generating image {i+1}/{len(scenes)}...")
                tmp = work_dir / f"tmp_{img_path.name}"
                await ai_engine.generate_scene_image(sc["visual_prompt"], aspect, tmp, project_id=job_id)
                os.replace(tmp, img_path)
            sc["image"] = str(img_path)
            sc["image_url"] = projects.work_url(job_id, img_path.name)
            scene_images.append(img_path)

        # Step 4: Camera Motion & Transitions (Ultra HD Ken Burns or Wan 2.1)
        motion_label = "Ultra HD Ken Burns" if motion_mode == "kenburns" else ("Wan 2.1 AI Motion" if motion_mode == "wan" else "Clean Presentation")
        update_job_status(job_id, status="ANIMATING_VIDEO", progress=72, current_step=f"Composing {motion_label} and transitions...")
        scene_videos = []
        for i, (img_path, dur, sc) in enumerate(zip(scene_images, scene_durations, scenes)):
            _checkpoint(job_id)
            motion_desc = sc.get("motion_prompt", "cinematic camera movement")
            key = _asset_key(img_path.name, round(dur, 3), aspect, motion_mode,
                             ai_engine.scene_motion_type(i, motion_mode), motion_desc if motion_mode == "wan" else "")
            vid_path = work_dir / f"clip_{key}.mp4"
            progress = 72 + int((i / len(scenes)) * 20)
            if vid_path.exists():
                update_job_status(job_id, status="ANIMATING_VIDEO", progress=progress, current_step=f"Reusing camera motion for scene {i+1}/{len(scenes)}...")
            else:
                update_job_status(job_id, status="ANIMATING_VIDEO", progress=progress, current_step=f"Composing camera motion for scene {i+1}/{len(scenes)}...")
                tmp = work_dir / f"tmp_{vid_path.name}"
                await ai_engine.animate_scene(
                    image_path=img_path,
                    motion_prompt=motion_desc,
                    duration=dur,
                    aspect=aspect,
                    output_path=tmp,
                    fallback_idx=i,
                    motion_mode=motion_mode,
                    project_id=job_id
                )
                os.replace(tmp, vid_path)
            scene_videos.append(vid_path)

        # Step 5: Final Composition & Cinematic Soundtrack Mix
        _checkpoint(job_id)
        update_job_status(job_id, status="COMPOSING", progress=94, current_step=f"Mixing voiceover with background music ({music_file.stem})..." if music_file else "Mixing final voiceover...")
        final_mp4 = projects.new_output_path(job_id, "video", ".mp4")

        await asyncio.to_thread(
            ai_engine.assemble_final_video,
            scene_videos=scene_videos,
            scene_audios=scene_audios,
            output_path=final_mp4,
            aspect=aspect,
            music_file=music_file,
            music_volume=100 if job.get("music_volume") is None else int(job["music_volume"]),
            voice_volume=100 if job.get("voice_volume") is None else int(job["voice_volume"]),
            music_ducking=bool(job.get("music_ducking", 1)),
        )

        latest = get_job(job_id)
        if latest is None:
            raise ProjectDeleted(job_id)

        # A thumbnail designed in Thumbnail Studio survives re-renders; otherwise use the opening frame
        thumbnail_url = latest.get("thumbnail") or ""
        has_custom_thumb = bool(latest.get("thumbnail_design")) and projects.url_to_path(thumbnail_url) is not None
        if not has_custom_thumb and scene_images:
            thumb = projects.new_output_path(job_id, "thumb", scene_images[0].suffix)
            shutil.copy(scene_images[0], thumb)
            projects.remove_old_outputs(job_id, "thumb", keep=thumb)
            thumbnail_url = projects.output_url(job_id, thumb.name)

        projects.remove_old_outputs(job_id, "video", keep=final_mp4)
        _remove_unused_scene_assets(work_dir, {p.name for p in (*scene_audios, *scene_images, *scene_videos)})

        update_job_status(
            job_id,
            status="DONE",
            progress=100,
            current_step="Video complete and ready to watch!",
            output_video=projects.output_url(job_id, final_mp4.name),
            thumbnail=thumbnail_url,
            scenes_json=json.dumps(scenes, ensure_ascii=False)
        )
        logger.success(f"Job {job_id} successfully completed! Saved to {final_mp4}")

    except ProjectDeleted:
        logger.info(f"Project {job_id} was deleted mid-render; discarding its files")
        projects.purge_project_files(job_id)
    except Exception as e:
        if get_job(job_id) is None:
            projects.purge_project_files(job_id)
            return
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
