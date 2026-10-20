"""Project storage layout.

Every generated video is a project identified by its job id. All of its files live in
exactly two folders, so deleting a project can remove every asset it ever produced:

    jobs/<id>/     working files: scene audio, images, clips, thumbnail backgrounds
    output/<id>/   deliverables: the final video and the thumbnail
"""
import re
import shutil
import time
from pathlib import Path
from loguru import logger
import ai_engine

BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "jobs"
OUTPUT_DIR = BASE_DIR / "output"

PROJECT_ID_RE = re.compile(r"^job_[0-9a-f]{8}$")


def is_valid_id(project_id: str) -> bool:
    return bool(PROJECT_ID_RE.match(project_id or ""))


def work_dir(project_id: str) -> Path:
    return JOBS_DIR / project_id


def output_dir(project_id: str) -> Path:
    return OUTPUT_DIR / project_id


def work_url(project_id: str, filename: str) -> str:
    return f"/jobs/{project_id}/{filename}"


def output_url(project_id: str, filename: str) -> str:
    return f"/output/{project_id}/{filename}"


def url_to_path(url: str) -> Path | None:
    """Maps a /output/... or /jobs/... URL stored in the DB back to a file on disk."""
    url = (url or "").split("?", 1)[0]
    for prefix, root in (("/output/", OUTPUT_DIR), ("/jobs/", JOBS_DIR)):
        if url.startswith(prefix):
            path = (root / url[len(prefix):]).resolve()
            if path.is_relative_to(root.resolve()) and path.is_file():
                return path
    return None


def new_output_path(project_id: str, kind: str, suffix: str) -> Path:
    """A fresh, versioned file name so browsers never show a cached older render."""
    out = output_dir(project_id)
    out.mkdir(parents=True, exist_ok=True)
    return out / f"{kind}_{int(time.time() * 1000)}{suffix}"


def remove_old_outputs(project_id: str, kind: str, keep: Path):
    for f in output_dir(project_id).glob(f"{kind}_*"):
        if f != keep:
            f.unlink(missing_ok=True)


def download_name(title: str, suffix: str) -> str:
    # Strip only characters file systems reject, so Bengali/Hindi titles keep their vowel signs
    stem = re.sub(r'[\\/:*?"<>|\x00-\x1f.]+', "", title or "").strip().replace(" ", "_")[:60]
    return f"{stem or 'vidforge'}{suffix}"


def purge_project_files(project_id: str):
    """Deletes every file the project produced, including ComfyUI intermediates."""
    if not is_valid_id(project_id):
        raise ValueError(f"Invalid project id: {project_id}")

    targets: list[Path] = [
        work_dir(project_id),
        output_dir(project_id),
        # Layout used before projects had their own output folder
        OUTPUT_DIR / f"{project_id}.mp4",
        OUTPUT_DIR / f"{project_id}_thumb.png",
        ai_engine.COMFYUI_OUTPUT / ai_engine.comfy_subfolder(project_id),
    ]
    if ai_engine.COMFYUI_INPUT.exists():
        targets += list(ai_engine.COMFYUI_INPUT.glob(f"wan_in_{project_id}_*"))

    for t in targets:
        try:
            if t.is_dir():
                shutil.rmtree(t, ignore_errors=True)
            elif t.exists():
                t.unlink()
        except OSError as e:
            logger.warning(f"Could not remove {t}: {e}")
    logger.info(f"Purged all assets for project {project_id}")
