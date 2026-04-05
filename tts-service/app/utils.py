import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Optional

import soundfile as sf


TEMP_DIR = Path("/data/temp")
OUTPUT_DIR = Path("/data/output")
VOICES_DIR = Path("/data/voices")

_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_SAFE_EXT_RE = re.compile(r"^\.[a-z0-9]{1,8}$")
_ALLOWED_AUDIO_EXT = frozenset({".wav", ".mp3", ".flac"})
_ALLOWED_VIDEO_EXT = frozenset({".mp4", ".mkv", ".mov", ".webm", ".avi"})


def _assert_safe_id(value: str, name: str = "ID") -> None:
    if not _SAFE_ID_RE.match(value):
        raise ValueError(f"Unsichere {name}: enthält ungültige Zeichen.")


def _safe_audio_ext(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in _ALLOWED_AUDIO_EXT else ".wav"


def _safe_video_ext(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in _ALLOWED_VIDEO_EXT else ".mp4"


def new_job_id() -> str:
    return str(uuid.uuid4())


def _safe_path(base: Path, *parts: str) -> Path:
    """Konstruiert einen Pfad und stellt sicher, dass er innerhalb von base bleibt."""
    candidate = base.joinpath(*parts).resolve()
    base_resolved = base.resolve()
    if not str(candidate).startswith(str(base_resolved) + os.sep):
        raise ValueError(f"Pfad außerhalb des erlaubten Verzeichnisses: {candidate}")
    return candidate


def job_dir(job_id: str) -> Path:
    if not _SAFE_ID_RE.match(job_id):
        raise ValueError("Ungültige job_id.")
    return _safe_path(TEMP_DIR, job_id)


def job_status_file(job_id: str) -> Path:
    if not _SAFE_ID_RE.match(job_id):
        raise ValueError("Ungültige job_id.")
    return _safe_path(TEMP_DIR, f"{job_id}.json")


def output_path(job_id: str, ext: str = "mp4") -> Path:
    if not _SAFE_ID_RE.match(job_id):
        raise ValueError("Ungültige job_id.")
    if not _SAFE_EXT_RE.match(f".{ext}"):
        raise ValueError(f"Ungültige Dateiendung: {ext}")
    return _safe_path(OUTPUT_DIR, f"{job_id}.{ext}")


def voice_path(voice_id: str) -> Optional[Path]:
    if not _SAFE_ID_RE.match(voice_id):
        raise ValueError("Ungültige voice_id.")
    for ext in ("wav", "mp3", "flac"):
        try:
            p = _safe_path(VOICES_DIR, f"{voice_id}.{ext}")
        except ValueError:
            continue
        if p.exists():
            return p
    return None


def audio_duration(path: Path) -> Optional[float]:
    try:
        info = sf.info(str(path))
        return info.duration
    except Exception:
        return None


def validate_audio_duration(path: Path, min_seconds: float = 3.0, max_seconds: float = 30.0) -> Optional[str]:
    duration = audio_duration(path)
    if duration is None:
        return "Audiodatei konnte nicht gelesen werden."
    if duration < min_seconds:
        return f"Referenz-Audio zu kurz ({duration:.1f}s). Mindestens {min_seconds}s nötig."
    if duration > max_seconds:
        return f"Referenz-Audio zu lang ({duration:.1f}s). Maximal {max_seconds}s erlaubt."
    return None


def cleanup_job(job_id: str) -> None:
    d = job_dir(job_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    status = job_status_file(job_id)
    if status.exists():
        status.unlink(missing_ok=True)


def disk_free_gb(path: str = "/data") -> float:
    stat = shutil.disk_usage(path)
    return round(stat.free / (1024**3), 2)
