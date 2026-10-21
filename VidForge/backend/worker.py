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
import narration
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
        resolution = int(job.get("resolution") or 1080)
        resolution = resolution if resolution in ai_engine.RESOLUTIONS else 1080
        fps = int(job.get("fps") or ai_engine.VIDEO_FPS)
        fps = fps if fps in ai_engine.FPS_OPTIONS else ai_engine.VIDEO_FPS
        music_file = music_library.resolve_track(job.get("music_track") or "")
        if job.get("music_track") and not music_file:
            logger.warning(f"Background music '{job['music_track']}' not found; continuing without music")

        # Step 1: Script & Scene Planning
        scenes = []
        narrator_style = job.get("narrator_style") or ""
        script_mode = job.get("script_mode", "ai_generate")
        if job.get("scenes_json") and job["scenes_json"] != "[]":
            try:
                scenes = json.loads(job["scenes_json"])
                logger.info(f"Using {len(scenes)} pre-planned scenes")
            except Exception:
                scenes = []

        if not scenes:
            raw_parsed = ai_engine.parse_direct_script_raw(job["story_prompt"])
            is_formatted_script = bool(
                raw_parsed and len(raw_parsed) > 1 and any(
                    re.search(r'Scene|দৃশ্য|Narration|ভয়েসওভার|Dialogue|সংবাদ', job["story_prompt"], re.I)
                )
            )
            if script_mode == "direct" or is_formatted_script:
                update_job_status(job_id, status="SCRIPTING", progress=10, current_step="Building visual scenes from exact script (Preserving full dialogue)...")
                scenes = await ai_engine.build_scenes_from_direct_script(
                    prompt=job["story_prompt"],
                    language=job["language"]
                )
                title = job.get("title") or "Direct Script Production"
            else:
                char_refs = []
                if job.get("character_references"):
                    try:
                        char_refs = json.loads(job["character_references"])
                    except Exception:
                        char_refs = []
                
                # If characters have an uploaded photo but no detailed look, extract facial likeness now
                if char_refs:
                    for cr in char_refs:
                        if isinstance(cr, dict) and cr.get("image_url") and not cr.get("look"):
                            rel = str(cr["image_url"]).lstrip("/").replace("jobs/", "", 1)
                            local_img = projects.JOBS_DIR / rel
                            if local_img.exists():
                                logger.info(f"Extracting facial features for character '{cr.get('name')}' from {local_img}...")
                                try:
                                    analysis = await ai_engine.extract_character_face_features(
                                        image_path=local_img,
                                        character_name=cr.get("name", "Protagonist"),
                                        video_type=video_type
                                    )
                                    if analysis.get("look"):
                                        cr["look"] = analysis["look"]
                                except Exception as e:
                                    logger.warning(f"Could not extract face features for {cr.get('name')}: {e}")

                step_title = f"Generating {video_type.title()} script with {len(char_refs)} custom character(s) (~{target_duration}s)..." if char_refs else f"Generating {video_type.title()} script (~{target_duration}s)..."
                update_job_status(job_id, status="SCRIPTING", progress=10, current_step=step_title)
                plan = await ai_engine.plan_script(
                    prompt=job["story_prompt"],
                    language=job["language"],
                    video_type=video_type,
                    target_duration=target_duration,
                    character_references=char_refs
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

        # Step 2: Voiceover generation (Audio-First continuous narration)
        voice_label = job.get("voice", "neural")
        update_job_status(job_id, status="VOICEOVER", progress=30, current_step=f"Generating voiceover using {voice_label}...")
        engine, voice_name = tts_engine.split_voice(job["voice"])

        def _pause(i: int, sc: dict) -> float:
            # Continuous human speech: 0.0s artificial silence padding between connected scenes.
            # Only hold slightly at the very end of the story.
            if i == len(scenes) - 1:
                return 0.5
            try:
                pause = float(sc.get("pause_after", 0.0))
            except (TypeError, ValueError):
                pause = 0.0
            return max(0.0, min(pause, 1.0))

        # Audio-First: voice the entire story in continuous master takes first
        continuous = True
        story_key = _asset_key([sc["narration"] for sc in scenes], narrator_style, job["voice"], job["language"])
        audio_paths = []
        for i, sc in enumerate(scenes):
            parts = [sc["narration"], sc.get("delivery", ""), narrator_style, job["voice"], job["language"], round(_pause(i, sc), 2)]
            if engine in tts_engine.BATCH_ENGINES:
                parts.append(tts_engine.get_local_tts_model())  # switching the local model re-voices the story
            key = _asset_key(*parts, story_key)
            audio_paths.append(work_dir / f"audio_{key}.mp3")

        async def _on_voice_status(msg: str, progress: int = 32):
            _checkpoint(job_id)
            update_job_status(job_id, status="VOICEOVER", progress=progress, current_step=msg)

        async def _finish_scene_audio(i: int, raw: Path, is_split_from_continuous: bool = True):
            if audio_paths[i].exists():
                raw.unlink(missing_ok=True)
                return
            if not raw.exists():
                logger.warning(f"Raw scene audio {raw} missing; skipping padding")
                return
            pause_sec = 0.0 if (is_split_from_continuous and i < len(scenes) - 1) else _pause(i, scenes[i])
            if pause_sec > 0.0:
                await asyncio.to_thread(ai_engine.pad_audio_with_silence, raw, pause_sec)
            await asyncio.to_thread(ai_engine.snap_audio_to_frames, raw, fps)
            await asyncio.to_thread(tts_engine.encode_scene_audio, raw, audio_paths[i])
            raw.unlink(missing_ok=True)

        missing = [i for i, p in enumerate(audio_paths) if not p.exists()]
        if missing:
            # Voice the entire story into a single master audio recording first
            texts = [sc["narration"] for sc in scenes]
            takes = narration.group_into_takes(texts)
            for t, idxs in enumerate(takes):
                _checkpoint(job_id)
                progress = 30 + int((t / len(takes)) * 14)
                label = f"part {t + 1}/{len(takes)}" if len(takes) > 1 else "master continuous audio"
                await _on_voice_status(f"Recording master continuous audio ({label})...", progress)
                take_path = work_dir / f"master_audio_take_{story_key}_{t}.wav"
                raws = [work_dir / f"tmp_scene_{story_key}_{i}.wav" for i in idxs]
                await tts_engine.generate_story_take(
                    [texts[i] for i in idxs], job["voice"], take_path,
                    narrator_style=narrator_style, deliveries=[scenes[i].get("delivery", "") for i in idxs],
                    on_status=lambda m: _on_voice_status(m, progress),
                    language=job.get("language", ""),
                )
                await asyncio.to_thread(narration.split_take, take_path, [texts[i] for i in idxs], raws)
                for i, raw in zip(idxs, raws):
                    await _finish_scene_audio(i, raw, is_split_from_continuous=True)
                master_story_file = work_dir / f"master_story_audio_{t}.wav"
                try:
                    if take_path.exists():
                        shutil.copy(take_path, master_story_file)
                except Exception:
                    pass
                take_path.unlink(missing_ok=True)

        voice_separately = [i for i, p in enumerate(audio_paths) if not p.exists()]
        if engine in tts_engine.BATCH_ENGINES and voice_separately:
            # Local cloning: one model load, one reference, one seed for every scene → one consistent voice
            # Deduplicate targets so identical narration lines are only voiced and processed once
            unique_indices = []
            seen_audio = set()
            for idx in voice_separately:
                p = audio_paths[idx]
                if p not in seen_audio and not p.exists():
                    seen_audio.add(p)
                    unique_indices.append(idx)

            raws = [work_dir / f"tmp_scene_{i}_{audio_paths[i].stem}.wav" for i in unique_indices]
            if raws:
                await _on_voice_status(f"Voicing {len(raws)} scenes with {tts_engine.LOCAL_TTS_MODELS[tts_engine.get_local_tts_model()]['label']}...", 31)
                await tts_engine.generate_local_batch(
                    [scenes[i]["narration"] for i in unique_indices], voice_name, raws,
                    language=job["language"], on_status=lambda m: _on_voice_status(m, 38),
                )
                for i, raw in zip(unique_indices, raws):
                    await _finish_scene_audio(i, raw)
            voice_separately = []

        stitch_ids: list[str] = []  # ElevenLabs request stitching keeps the delivery continuous
        for i in voice_separately:
            _checkpoint(job_id)
            progress = 30 + int((i / len(scenes)) * 14)
            await _on_voice_status(f"Voicing scene {i+1}/{len(scenes)}...", progress)
            sc = scenes[i]
            raw = work_dir / f"tmp_scene_{i}_{audio_paths[i].stem}.wav"
            await tts_engine.generate_voiceover(
                sc["narration"],
                job["voice"],
                raw,
                delivery=sc.get("delivery", ""),
                narrator_style=narrator_style,
                previous_text=scenes[i - 1]["narration"] if i > 0 else "",
                next_text=scenes[i + 1]["narration"] if i + 1 < len(scenes) else "",
                stitch_ids=stitch_ids,
                language=job["language"],
                on_status=lambda m: _on_voice_status(m, progress)
            )
            await _finish_scene_audio(i, raw)

        scene_audios = audio_paths
        scene_durations = []
        for i, (sc, audio_path) in enumerate(zip(scenes, audio_paths)):
            # Also snaps audio cached by older renders to the video frame grid (no-op when already snapped)
            duration = await asyncio.to_thread(ai_engine.snap_audio_to_frames, audio_path, fps)
            sc["duration"] = duration
            scene_durations.append(duration)
            logger.info(f"Scene {i+1} audio duration: {duration:.3f}s")

        update_job_status(job_id, status="VOICEOVER", progress=45, current_step="Voiceover complete. Starting AI image generation...", scenes_json=json.dumps(scenes, ensure_ascii=False))

        # Step 3: Visual Generation with ComfyUI Z-Image-Turbo
        update_job_status(job_id, status="GENERATING_IMAGES", progress=50, current_step="Rendering base visuals in ComfyUI...")
        scene_images = []
        for i, sc in enumerate(scenes):
            _checkpoint(job_id)
            image_prompt = ai_engine.compose_image_prompt(sc)
            img_path = work_dir / f"image_{_asset_key(image_prompt, aspect, job_id)}.png"
            progress = 50 + int((i / len(scenes)) * 20)
            if img_path.exists():
                update_job_status(job_id, status="GENERATING_IMAGES", progress=progress, current_step=f"Reusing image {i+1}/{len(scenes)}...")
            else:
                update_job_status(job_id, status="GENERATING_IMAGES", progress=progress, current_step=f"Generating image {i+1}/{len(scenes)}...")
                tmp = work_dir / f"tmp_{img_path.name}"
                await ai_engine.generate_scene_image(image_prompt, aspect, tmp, project_id=job_id)
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
            key = _asset_key(img_path.name, round(dur, 3), aspect, motion_mode, fps, resolution,
                             ai_engine.scene_motion_type(i, motion_mode),
                             (motion_desc, ai_engine.WAN_QUALITY, ai_engine.pick_wan_model()) if motion_mode == "wan" else "")
            vid_path = work_dir / f"clip_{key}.mp4"
            progress = 72 + int((i / len(scenes)) * 20)
            if vid_path.exists():
                update_job_status(job_id, status="ANIMATING_VIDEO", progress=progress, current_step=f"Reusing camera motion for scene {i+1}/{len(scenes)}...")
            else:
                step_text = f"Generating Wan 2.1 AI neural video for scene {i+1}/{len(scenes)} (ComfyUI)..." if motion_mode == "wan" else f"Composing camera motion for scene {i+1}/{len(scenes)}..."
                update_job_status(job_id, status="ANIMATING_VIDEO", progress=progress, current_step=step_text)
                tmp = work_dir / f"tmp_{vid_path.name}"
                await ai_engine.animate_scene(
                    image_path=img_path,
                    motion_prompt=motion_desc,
                    duration=dur,
                    aspect=aspect,
                    output_path=tmp,
                    fallback_idx=i,
                    motion_mode=motion_mode,
                    project_id=job_id,
                    resolution=resolution,
                    fps=fps,
                )
                os.replace(tmp, vid_path)
            scene_videos.append(vid_path)

        # Step 5: Final Composition & Cinematic Soundtrack Mix
        _checkpoint(job_id)
        update_job_status(job_id, status="COMPOSING", progress=94, current_step=f"Mixing voiceover with background music ({music_file.stem})..." if music_file else "Mixing final voiceover...")
        final_mp4 = projects.new_output_path(job_id, "video", ".mp4")

        # Subtitle processing
        enable_subtitles = bool(job.get("enable_subtitles", 1))
        ass_path = work_dir / "subtitles.ass"
        srt_path = work_dir / "subtitles.srt"
        if enable_subtitles:
            ai_engine.generate_ass_subtitles(scenes, scene_durations, aspect, ass_path)
            ai_engine.generate_srt_subtitles(scenes, scene_durations, srt_path)
            try:
                out_srt = projects.new_output_path(job_id, "subtitles", ".srt")
                shutil.copy(srt_path, out_srt)
            except Exception as e:
                logger.warning(f"Could not copy sidecar srt: {e}")

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
            enable_subtitles=enable_subtitles,
            subtitles_file=ass_path if enable_subtitles else None,
            music_levels=[sc.get("music_level", "medium") for sc in scenes],
            resolution=resolution,
            fps=fps,
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
