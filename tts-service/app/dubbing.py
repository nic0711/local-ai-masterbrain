"""
Dubbing-Pipeline: Video -> Transkription -> Uebersetzung -> TTS -> Zusammenbau
"""
import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

import httpx
import soundfile as sf
import numpy as np

from utils import TEMP_DIR, OUTPUT_DIR, job_dir, job_status_file, output_path, voice_path

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "medium")


# ------------------------------------------------------------------ #
# Job-Status                                                           #
# ------------------------------------------------------------------ #

def _write_status(job_id: str, status: str, progress: float, error: str = None, download_url: str = None) -> None:
    data = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "error": error,
        "download_url": download_url,
    }
    job_status_file(job_id).write_text(json.dumps(data))


def read_status(job_id: str) -> Optional[dict]:
    f = job_status_file(job_id)
    if not f.exists():
        return None
    return json.loads(f.read_text())


# ------------------------------------------------------------------ #
# Schritt 1: Audio-Extraktion via ffmpeg                              #
# Sicher: Argumente als Liste, kein shell=True                        #
# ------------------------------------------------------------------ #

async def _extract_audio(video_path: Path, out_dir: Path) -> Path:
    audio_out = out_dir / "audio.wav"
    args = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn", "-ac", "1", "-ar", "16000",
        str(audio_out),
    ]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg Audio-Extraktion fehlgeschlagen: {stderr.decode()}")
    return audio_out


# ------------------------------------------------------------------ #
# Schritt 2: Transkription via faster-whisper                         #
# ------------------------------------------------------------------ #

async def _transcribe(audio_path: Path, source_language: Optional[str]) -> list[dict]:
    loop = asyncio.get_event_loop()

    def _run():
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(
            str(audio_path),
            language=source_language,
            beam_size=5,
            word_timestamps=False,
        )
        return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]

    return await loop.run_in_executor(None, _run)


# ------------------------------------------------------------------ #
# Schritt 3: Uebersetzung via Ollama                                  #
# ------------------------------------------------------------------ #

async def translate_segment(text: str, target_language: str) -> str:
    """
    Uebersetzt ein Transkriptions-Segment via Ollama.

    TODO (User-Beitrag): Anpasse den Prompt nach deiner bevorzugten Strategie.

    Variante A (Laengen-erhaltend, besser fuer Timing):
        "Translate to {lang}. Keep similar sentence length as the original.
         Return only the translation."

    Variante B (Natuerlich, aktiver Default):
        "Translate to {lang}. Return only the translation, no explanation."
    """
    lang_names = {"de": "German", "en": "English", "fr": "French", "es": "Spanish", "it": "Italian"}
    lang_name = lang_names.get(target_language, target_language)

    prompt = (
        f"Translate the following text to {lang_name}. "
        f"Return only the translation, no explanation.\n\n{text}"
    )

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()


# ------------------------------------------------------------------ #
# Schritt 4+5: TTS pro Segment                                        #
# ------------------------------------------------------------------ #

async def _synthesize_segments(
    segments: list[dict],
    tts_engine,
    ref_audio_path: Optional[str],
    work_dir: Path,
    job_id: str,
    progress_start: float,
    progress_end: float,
) -> list[Path]:
    clips = []
    total = len(segments)
    for i, seg in enumerate(segments):
        clip_path = work_dir / f"seg_{i:04d}.wav"
        wav_bytes = await tts_engine.synthesize(seg["translated"], ref_audio_path)
        clip_path.write_bytes(wav_bytes)
        clips.append(clip_path)

        progress = progress_start + (i + 1) / total * (progress_end - progress_start)
        _write_status(job_id, "synthesizing", round(progress, 3))

    return clips


# ------------------------------------------------------------------ #
# Schritt 6: Audio-Track mit Timing-Anpassung aufbauen               #
# ------------------------------------------------------------------ #

def _build_audio_track(segments: list[dict], clips: list[Path], sample_rate: int = 24000) -> np.ndarray:
    if not segments:
        return np.zeros(sample_rate, dtype=np.float32)

    total_duration = segments[-1]["end"] + 0.5
    output = np.zeros(int(total_duration * sample_rate), dtype=np.float32)

    for seg, clip_path in zip(segments, clips):
        original_duration = seg["end"] - seg["start"]
        if original_duration <= 0:
            continue

        data, sr = sf.read(str(clip_path), dtype="float32")
        if sr != sample_rate:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=sample_rate)

        tts_duration = len(data) / sample_rate
        if tts_duration <= 0:
            continue

        factor = tts_duration / original_duration
        # Strecken/Stauchen wenn Abweichung > 15%
        if abs(factor - 1.0) > 0.15:
            import librosa
            rate = float(np.clip(factor, 0.5, 2.0))
            data = librosa.effects.time_stretch(data, rate=rate)

        start_sample = int(seg["start"] * sample_rate)
        end_sample = start_sample + len(data)
        if end_sample > len(output):
            data = data[:len(output) - start_sample]
            end_sample = len(output)
        output[start_sample:end_sample] += data

    return output


# ------------------------------------------------------------------ #
# Schritt 7: Video-Merge via ffmpeg                                   #
# ------------------------------------------------------------------ #

async def _merge_video_audio(
    video_path: Path,
    audio_path: Path,
    out_path: Path,
    keep_original: bool,
) -> None:
    if keep_original:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex", "[1:a]volume=-20dB[orig];[0:a][orig]amix=inputs=2[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy",
            str(out_path),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy",
            str(out_path),
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg Video-Merge fehlgeschlagen: {stderr.decode()}")


# ------------------------------------------------------------------ #
# Haupt-Pipeline                                                       #
# ------------------------------------------------------------------ #

async def run_dubbing_job(
    job_id: str,
    video_path: Path,
    target_language: str,
    source_language: Optional[str],
    voice_id: Optional[str],
    keep_original_audio: bool,
    tts_engine,
) -> None:
    work_dir = job_dir(job_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_path(job_id, "mp4")

    try:
        _write_status(job_id, "extracting", 0.05)
        audio_path = await _extract_audio(video_path, work_dir)

        _write_status(job_id, "transcribing", 0.15)
        segments = await _transcribe(audio_path, source_language)
        if not segments:
            raise RuntimeError("Keine Transkriptions-Segmente gefunden.")

        _write_status(job_id, "translating", 0.30)
        for i, seg in enumerate(segments):
            seg["translated"] = await translate_segment(seg["text"], target_language)
            progress = 0.30 + (i + 1) / len(segments) * 0.20
            _write_status(job_id, "translating", round(progress, 3))

        ref_audio = str(voice_path(voice_id)) if voice_id and voice_path(voice_id) else None
        clips = await _synthesize_segments(
            segments, tts_engine, ref_audio, work_dir, job_id,
            progress_start=0.50, progress_end=0.80,
        )

        _write_status(job_id, "merging", 0.85)
        audio_track = _build_audio_track(segments, clips)
        dubbed_audio = work_dir / "dubbed_audio.wav"
        sf.write(str(dubbed_audio), audio_track, 24000)

        await _merge_video_audio(video_path, dubbed_audio, out_path, keep_original_audio)

        _write_status(job_id, "done", 1.0, download_url=f"/dub/download/{job_id}")
        logger.info("Dubbing-Job %s abgeschlossen: %s", job_id, out_path)

    except Exception as exc:
        logger.exception("Dubbing-Job %s fehlgeschlagen", job_id)
        _write_status(job_id, "error", 0.0, error=str(exc))
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
