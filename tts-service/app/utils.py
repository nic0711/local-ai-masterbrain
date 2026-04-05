import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

import soundfile as sf


TEMP_DIR = Path("/data/temp")
OUTPUT_DIR = Path("/data/output")
VOICES_DIR = Path("/data/voices")


def new_job_id() -> str:
    return str(uuid.uuid4())


def job_dir(job_id: str) -> Path:
    return TEMP_DIR / job_id


def job_status_file(job_id: str) -> Path:
    return TEMP_DIR / f"{job_id}.json"


def output_path(job_id: str, ext: str = "mp4") -> Path:
    return OUTPUT_DIR / f"{job_id}.{ext}"


def voice_path(voice_id: str) -> Optional[Path]:
    for ext in ("wav", "mp3", "flac"):
        p = VOICES_DIR / f"{voice_id}.{ext}"
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
