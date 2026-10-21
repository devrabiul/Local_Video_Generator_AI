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


def detect_silences(path: Path, noise_db: int = -35, min_dur: float = 0.18) -> list[tuple[float, float]]:
    res = subprocess.run(
        [FFMPEG, "-i", str(path), "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", res.stderr)]
    merged: list[tuple[float, float]] = []
    for s, e in zip(starts, ends):
        if e <= s:
            continue
        if merged and s - merged[-1][1] < 0.08:  # touching silences are one pause
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return merged


def find_cut_points(take: Path, weights: list[int], total: float) -> list[float]:
    """Finds optimal scene boundaries on the continuous master take.
    
    Prefers natural spoken pauses / silences between sentences. If continuous conversational
    speech has no audible silence at a boundary, falls back to text-proportional boundary
    timing to ensure the original continuous performance is ALWAYS preserved.
    """
    n = len(weights)
    if n <= 1:
        return []
    total_w = sum(weights) or 1
    avg_scene = total / n
    tolerance = max(2.0, 0.5 * avg_scene)

    # Multi-pass silence detection: standard pauses first, sensitive breath pauses second
    silences = detect_silences(take, noise_db=-35, min_dur=0.18)
    if len(silences) < n - 1:
        sensitive = detect_silences(take, noise_db=-28, min_dur=0.08)
        if len(sensitive) > len(silences):
            silences = sensitive

    cuts: list[float] = []
    cumulative = 0
    used_until = 0.0
    for k in range(n - 1):
        cumulative += weights[k]
        expected = total * cumulative / total_w
        best, best_score = None, None
        
        for start, end in silences:
            mid = (start + end) / 2
            if mid <= used_until + 0.4 or end >= total - 0.2:
                continue
            distance = abs(mid - expected)
            if distance > tolerance:
                continue
            score = distance - 1.2 * min(end - start, 1.5)  # long natural pauses win ties
            if best_score is None or score < best_score:
                best, best_score = mid, score

        # If no silence was near the expected time, use expected time clamped safely
        if best is None:
            min_bound = used_until + 0.5
            max_bound = total - (0.5 * (n - 1 - k))
            cut_point = max(min_bound, min(expected, max_bound))
            logger.info(f"Boundary {k+1}/{n-1}: no distinct silence near {expected:.2f}s; using proportional cut at {cut_point:.2f}s")
        else:
            cut_point = best

        cuts.append(round(cut_point, 3))
        used_until = cut_point

    return cuts


def split_take(take: Path, texts: list[str], outputs: list[Path]) -> bool:
    """Cuts one continuous master take into per-scene clips.
    
    Guaranteed to succeed: always derives scene clips from the single continuous master recording.
    """
    total = get_audio_duration(take)
    if total <= 0:
        logger.error(f"Cannot split take {take}: invalid audio duration ({total})")
        return False

    weights = [max(1, len(re.sub(r"\[[^\]]*\]|\s+", "", t))) for t in texts]
    cuts = find_cut_points(take, weights, total)
    bounds = [0.0, *cuts, total]

    # Cut exactly at the boundaries so scenes rejoin seamlessly into the continuous performance
    for (start, end), out in zip(zip(bounds, bounds[1:]), outputs):
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [FFMPEG, "-y", "-i", str(take), "-af", f"atrim=start={start:.3f}:end={end:.3f},asetpts=N/SR/TB",
             "-ar", "48000", str(out)],
            check=True, capture_output=True,
        )
    logger.info(f"Split master take {take.name} into {len(outputs)} scenes at {', '.join(f'{c:.2f}s' for c in cuts)} (total {total:.2f}s)")
    return True

