"""No-copyright background music library.

Tracks live in VidForge/No_Copyright_Music/<Category>/<file>. A track's id is its path
relative to the library root (POSIX style), which is what the UI sends back as `music_track`.
"""
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from ai_engine import BASE_DIR, FFPROBE

LIBRARY_DIR = BASE_DIR / "No_Copyright_Music"
LIBRARY_URL = "/music-library"
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

# Strip marketing noise from file names so titles read cleanly in the UI
_NOISE = re.compile(
    r"\[[^\]]*\]|\((?:no|copyright)[^)]*\)|\bno\s*copyright(?:\s*music)?\b|\bcopyright\s*free(?:\s*music)?\b|\bnocopyright\b",
    re.IGNORECASE,
)

_duration_cache: dict[tuple[str, float], float] = {}


def _clean_title(stem: str) -> str:
    title = _NOISE.sub(" ", stem)
    title = re.sub(r"\s{2,}", " ", title).strip(" -_,")
    return title or stem


def _duration(path: Path) -> float:
    key = (str(path), path.stat().st_mtime)
    if key not in _duration_cache:
        try:
            out = subprocess.run(
                [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                capture_output=True, text=True, timeout=15,
            )
            _duration_cache[key] = round(float(out.stdout.strip()), 1)
        except (ValueError, subprocess.SubprocessError, OSError):
            _duration_cache[key] = 0.0
    return _duration_cache[key]


def list_tracks() -> list[dict]:
    if not LIBRARY_DIR.is_dir():
        return []
    tracks = []
    for path in sorted(LIBRARY_DIR.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTS or path.name.startswith("."):
            continue
        rel = path.relative_to(LIBRARY_DIR).as_posix()
        category = rel.split("/")[0] if "/" in rel else "General"
        tracks.append({
            "id": rel,
            "title": _clean_title(path.stem),
            "category": category,
            "duration": _duration(path),
            "url": f"{LIBRARY_URL}/{quote(rel)}",
        })
    return tracks


def resolve_track(track_id: str) -> Path | None:
    """Maps a track id to a file inside the library, rejecting anything outside it."""
    if not track_id:
        return None
    root = LIBRARY_DIR.resolve()
    candidate = (root / track_id).resolve()
    if root not in candidate.parents or not candidate.is_file() or candidate.suffix.lower() not in AUDIO_EXTS:
        return None
    return candidate
