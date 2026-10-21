import sqlite3
import json
import time
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "jobs" / "vidforge.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

RUNNING_STATUSES = ("SCRIPTING", "VOICEOVER", "GENERATING_IMAGES", "ANIMATING_VIDEO", "COMPOSING")
# Fields the API may change directly on a project
EDITABLE_FIELDS = {"title", "thumbnail", "thumbnail_design"}

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT,
                story_prompt TEXT NOT NULL,
                language TEXT NOT NULL,
                voice TEXT NOT NULL,
                aspect_ratio TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                current_step TEXT DEFAULT '',
                scenes_json TEXT DEFAULT '[]',
                error_message TEXT DEFAULT '',
                output_video TEXT DEFAULT '',
                thumbnail TEXT DEFAULT '',
                video_type TEXT DEFAULT 'story',
                target_duration INTEGER DEFAULT 60,
                motion_mode TEXT DEFAULT 'kenburns',
                music_theme TEXT DEFAULT 'cinematic_epic',
                narrator_style TEXT DEFAULT '',
                music_track TEXT DEFAULT '',
                music_volume INTEGER DEFAULT 100,
                voice_volume INTEGER DEFAULT 100,
                music_ducking INTEGER DEFAULT 1,
                enable_subtitles INTEGER DEFAULT 1,
                resolution INTEGER DEFAULT 1080,
                fps INTEGER DEFAULT 30,
                thumbnail_design TEXT DEFAULT '',
                refine_instruction TEXT DEFAULT '',
                revision INTEGER DEFAULT 1,
                character_references TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        # Safe migration for existing databases
        for col, col_type in [
            ("video_type", "TEXT DEFAULT 'story'"),
            ("target_duration", "INTEGER DEFAULT 60"),
            ("motion_mode", "TEXT DEFAULT 'kenburns'"),
            ("music_theme", "TEXT DEFAULT 'cinematic_epic'"),
            ("narrator_style", "TEXT DEFAULT ''"),
            ("music_track", "TEXT DEFAULT ''"),
            ("music_volume", "INTEGER DEFAULT 100"),
            ("voice_volume", "INTEGER DEFAULT 100"),
            ("music_ducking", "INTEGER DEFAULT 1"),
            ("enable_subtitles", "INTEGER DEFAULT 1"),
            ("resolution", "INTEGER DEFAULT 1080"),
            ("fps", "INTEGER DEFAULT 30"),
            ("thumbnail_design", "TEXT DEFAULT ''"),
            ("refine_instruction", "TEXT DEFAULT ''"),
            ("revision", "INTEGER DEFAULT 1"),
            ("script_mode", "TEXT DEFAULT 'ai_generate'"),
            ("character_references", "TEXT DEFAULT '[]'")
        ]:
            try:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
        # A render cut off by a server restart can never finish; surface it so it can be regenerated
        conn.execute(
            f"UPDATE jobs SET status = 'FAILED', error_message = 'Interrupted by a server restart', "
            f"current_step = 'Interrupted' WHERE status IN ({','.join('?' * len(RUNNING_STATUSES))})",
            RUNNING_STATUSES
        )
        conn.commit()

def add_job(job_id: str, title: str, story_prompt: str, language: str, voice: str, aspect_ratio: str, 
            scenes_json: str = "[]", video_type: str = "story", target_duration: int = 60, 
            motion_mode: str = "kenburns", music_theme: str = "cinematic_epic", narrator_style: str = "",
            music_track: str = "", music_volume: int = 100, voice_volume: int = 100, music_ducking: bool = True,
            enable_subtitles: bool = True, resolution: int = 1080, fps: int = 30, script_mode: str = "ai_generate",
            character_references: str = "[]"):
    now = time.time()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO jobs (id, title, story_prompt, language, voice, aspect_ratio, status, progress, current_step, scenes_json, video_type, target_duration, motion_mode, music_theme, narrator_style, music_track, music_volume, voice_volume, music_ducking, enable_subtitles, resolution, fps, script_mode, character_references, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', 0, 'Waiting in queue', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_id, title, story_prompt, language, voice, aspect_ratio, scenes_json, video_type, target_duration, motion_mode, music_theme, narrator_style,
              music_track, music_volume, voice_volume, int(music_ducking), int(enable_subtitles), int(resolution), int(fps), script_mode, character_references, now, now))
        conn.commit()

def get_next_queued_job():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT * FROM jobs WHERE status = 'QUEUED' ORDER BY created_at ASC LIMIT 1
        """).fetchone()
        return dict(row) if row else None

def update_job_status(job_id: str, status: str, progress: int = None, current_step: str = None, 
                      scenes_json: str = None, error_message: str = None, 
                      output_video: str = None, thumbnail: str = None):
    now = time.time()
    updates = ["status = ?", "updated_at = ?"]
    params = [status, now]

    if progress is not None:
        updates.append("progress = ?")
        params.append(progress)
    if current_step is not None:
        updates.append("current_step = ?")
        params.append(current_step)
    if scenes_json is not None:
        updates.append("scenes_json = ?")
        params.append(scenes_json)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    if output_video is not None:
        updates.append("output_video = ?")
        params.append(output_video)
    if thumbnail is not None:
        updates.append("thumbnail = ?")
        params.append(thumbnail)

    params.append(job_id)
    query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"

    with get_connection() as conn:
        conn.execute(query, params)
        conn.commit()

def get_all_jobs():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        jobs = []
        for r in rows:
            d = dict(r)
            try:
                d["scenes"] = json.loads(d["scenes_json"])
            except Exception:
                d["scenes"] = []
            jobs.append(d)
        return jobs

def get_job(job_id: str):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["scenes"] = json.loads(d["scenes_json"])
        except Exception:
            d["scenes"] = []
        return d

def delete_job(job_id: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()

def delete_all_jobs():
    with get_connection() as conn:
        conn.execute("DELETE FROM jobs")
        conn.commit()


def update_job_fields(job_id: str, **fields):
    unknown = set(fields) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"Not editable: {', '.join(sorted(unknown))}")
    if not fields:
        return
    with get_connection() as conn:
        conn.execute(
            f"UPDATE jobs SET {', '.join(f'{k} = ?' for k in fields)}, updated_at = ? WHERE id = ?",
            [*fields.values(), time.time(), job_id]
        )
        conn.commit()

def requeue_job(job_id: str, step: str, scenes_json: str | None = None, refine_instruction: str = ""):
    """Puts an existing project back in the queue for a new revision; its current video stays available."""
    updates = ["status = 'QUEUED'", "progress = 0", "current_step = ?", "error_message = ''",
               "refine_instruction = ?", "revision = revision + 1", "updated_at = ?"]
    params: list = [step, refine_instruction, time.time()]
    if scenes_json is not None:
        updates.append("scenes_json = ?")
        params.append(scenes_json)
    params.append(job_id)
    with get_connection() as conn:
        conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

def clear_refine_instruction(job_id: str):
    with get_connection() as conn:
        conn.execute("UPDATE jobs SET refine_instruction = '' WHERE id = ?", (job_id,))
        conn.commit()
