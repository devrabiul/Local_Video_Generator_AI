"""Continuous narration: voice a whole story (or long stretches of it) in one take, then cut it
back into per-scene clips.

Voicing each scene separately lets the voice's emotion, pace and tone drift from scene to scene.
One take keeps a single continuous performance; the cut points are the pauses placed between
scenes, matched to where each scene should end based on its share of the text.
"""
import re
import subprocess
from pathlib import Path

from loguru import logger

from ai_engine import FFMPEG, get_audio_duration

TAKE_MAX_CHARS = 2400   # one request stays well inside the TTS input limit
SILENCE_DB = -38        # quieter than this counts as a pause
SILENCE_MIN = 0.28      # seconds


def group_into_takes(texts: list[str], max_chars: int = TAKE_MAX_CHARS) -> list[list[int]]:
    """Consecutive scene indexes, grouped so each take stays under max_chars."""
    takes, current, size = [], [], 0
    for i, text in enumerate(texts):
        if current and size + len(text) > max_chars:
            takes.append(current)
            current, size = [], 0
        current.append(i)
        size += len(text)
    if current:
        takes.append(current)
    return takes


def detect_silences(path: Path) -> list[tuple[float, float]]:
    res = subprocess.run(
        [FFMPEG, "-i", str(path), "-af", f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", res.stderr)]
    merged: list[tuple[float, float]] = []
    for s, e in zip(starts, ends):
        if e <= s:
            continue
        if merged and s - merged[-1][1] < 0.06:  # touching silences are one pause
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def find_cut_points(silences: list[tuple[float, float]], weights: list[int], total: float) -> list[float] | None:
    """One cut per scene boundary: the pause nearest each boundary's expected time.

    Expected times come from each scene's share of the text. Longer pauses are preferred, since
    the take places a long pause between scenes. Returns None if any boundary has no
    convincing pause nearby, so the caller can fall back to voicing scenes separately.
    """
    n = len(weights)
    if n == 1:
        return []
    total_w = sum(weights) or 1
    avg_scene = total / n
    tolerance = max(1.5, 0.45 * avg_scene)
    cuts: list[float] = []
    cumulative = 0
    used_until = 0.0
    for k in range(n - 1):
        cumulative += weights[k]
        expected = total * cumulative / total_w
        best, best_score = None, None
        for start, end in silences:
            mid = (start + end) / 2
            if mid <= used_until + 0.5 or end >= total - 0.2:
                continue
            distance = abs(mid - expected)
            if distance > tolerance:
                continue
            score = distance - 1.5 * min(end - start, 1.5)  # long pauses win ties
            if best_score is None or score < best_score:
                best, best_score = mid, score
        if best is None:
            return None
        cuts.append(best)
        used_until = best
    return cuts


def split_take(take: Path, texts: list[str], outputs: list[Path]) -> bool:
    """Cuts one take into per-scene clips. Returns False if the cut points can't be found."""
    total = get_audio_duration(take)
    weights = [max(1, len(re.sub(r"\[[^\]]*\]|\s+", "", t))) for t in texts]
    cuts = find_cut_points(detect_silences(take), weights, total)
    if cuts is None:
        logger.warning(f"Could not find {len(texts) - 1} scene pauses in {take.name}; voicing these scenes separately")
        return False
    bounds = [0.0, *cuts, total]
    # Cut exactly at the natural sentence pauses so the scenes rejoin seamlessly into the continuous performance
    for (start, end), out in zip(zip(bounds, bounds[1:]), outputs):
        subprocess.run(
            [FFMPEG, "-y", "-i", str(take), "-af", f"atrim=start={start:.3f}:end={end:.3f},asetpts=N/SR/TB",
             "-ar", "48000", str(out)],
            check=True, capture_output=True,
        )
    logger.info(f"Split {take.name} into {len(outputs)} scenes at {', '.join(f'{c:.2f}s' for c in cuts)}")
    return True
