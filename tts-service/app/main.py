import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import aiofiles
import httpx
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse

from dubbing import read_status, run_dubbing_job
from models import DubbingRequest, DubbingStatus, HealthResponse, SynthesizeRequest, VoiceInfo, _SAFE_ID_RE
from tts_engine import get_engine
from utils import (
    TEMP_DIR, OUTPUT_DIR, VOICES_DIR,
    audio_duration, cleanup_job, disk_free_gb,
    new_job_id, output_path, validate_audio_duration, voice_path,
    _safe_audio_ext, _safe_video_ext, _assert_safe_id,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verzeichnisse sicherstellen
    for d in (TEMP_DIR, OUTPUT_DIR, VOICES_DIR):
        d.mkdir(parents=True, exist_ok=True)

    # TTS-Engine im Hintergrund laden (blockiert nicht den Start)
    engine = get_engine()
    asyncio.get_event_loop().run_in_executor(None, engine.load)
    logger.info("TTS-Engine wird im Hintergrund geladen...")
    yield


app = FastAPI(
    title="TTS Service",
    description="Text-to-Speech, Voice Cloning und Video-Dubbing",
    version="1.0.0",
    lifespan=lifespan,
)


# ------------------------------------------------------------------ #
# Health & Info                                                        #
# ------------------------------------------------------------------ #

@app.get("/health", response_model=HealthResponse)
async def health():
    engine = get_engine()

    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass

    return HealthResponse(
        status="healthy",
        service="tts-service",
        tts_engine_loaded=engine.is_loaded,
        whisper_ready=True,
        ollama_reachable=ollama_ok,
        device=engine.device,
        disk_free_gb=disk_free_gb(),
    )


@app.get("/voices", response_model=list[VoiceInfo])
async def list_voices():
    voices = []
    for p in sorted(VOICES_DIR.iterdir()):
        if p.suffix in (".wav", ".mp3", ".flac"):
            voices.append(VoiceInfo(
                voice_id=p.stem,
                filename=p.name,
                duration_seconds=audio_duration(p),
            ))
    return voices


# ------------------------------------------------------------------ #
# TTS: Text -> Audio                                                   #
# ------------------------------------------------------------------ #

@app.post("/tts/synthesize")
async def synthesize(req: SynthesizeRequest):
    engine = get_engine()
    if not engine.is_loaded:
        raise HTTPException(503, "TTS-Engine noch nicht bereit. Bitte kurz warten.")

    ref_path: Optional[str] = None
    if req.voice_id:
        p = voice_path(req.voice_id)
        if p is None:
            raise HTTPException(404, f"Stimme '{req.voice_id}' nicht gefunden.")
        ref_path = str(p)

    wav_bytes = await engine.synthesize(req.text, ref_path)

    if req.output_format == "mp3":
        from pydub import AudioSegment
        import io
        seg = AudioSegment.from_wav(io.BytesIO(wav_bytes))
        buf = io.BytesIO()
        seg.export(buf, format="mp3")
        return StreamingResponse(iter([buf.getvalue()]), media_type="audio/mpeg")

    return StreamingResponse(iter([wav_bytes]), media_type="audio/wav")


# ------------------------------------------------------------------ #
# TTS: Voice Cloning                                                   #
# ------------------------------------------------------------------ #

@app.post("/tts/clone")
async def clone_voice(
    text: str = Form(...),
    language: str = Form(default="de"),
    save_as: Optional[str] = Form(default=None),
    reference_audio: UploadFile = File(...),
):
    engine = get_engine()
    if not engine.is_loaded:
        raise HTTPException(503, "TTS-Engine noch nicht bereit. Bitte kurz warten.")

    # Referenz-Audio temporaer speichern (Dateiendung aus Originalname, sanitiert)
    safe_ext = _safe_audio_ext(reference_audio.filename or "")
    tmp = TEMP_DIR / f"ref_{new_job_id()}{safe_ext}"
    try:
        async with aiofiles.open(tmp, "wb") as f:
            await f.write(await reference_audio.read())

        error = validate_audio_duration(tmp)
        if error:
            raise HTTPException(422, error)

        if save_as is not None and not _SAFE_ID_RE.match(save_as):
            raise HTTPException(422, "save_as darf nur Buchstaben, Zahlen, - und _ enthalten.")
        wav_bytes = await engine.clone_voice(text, str(tmp), save_as=save_as)
    finally:
        tmp.unlink(missing_ok=True)

    return StreamingResponse(iter([wav_bytes]), media_type="audio/wav")


# ------------------------------------------------------------------ #
# Dubbing: Video-Upload oder YouTube-URL                              #
# ------------------------------------------------------------------ #

@app.post("/dub/video", response_model=DubbingStatus)
async def dub_video(
    background_tasks: BackgroundTasks,
    req: Optional[DubbingRequest] = None,
    video: Optional[UploadFile] = File(default=None),
):
    if req is None:
        req = DubbingRequest()

    if video is None and not req.youtube_url:
        raise HTTPException(422, "Entweder 'video' (Upload) oder 'youtube_url' erforderlich.")

    engine = get_engine()
    job_id = new_job_id()
    work_dir = TEMP_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    if req.youtube_url:
        video_path = work_dir / "input.mp4"
        # yt-dlp als sicherer Subprocess (Argumente als Liste, kein shell=True)
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            "--max-filesize", "500M",
            "-f", "bestvideo[ext=mp4]+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", str(video_path),
            req.youtube_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.warning("yt-dlp fehlgeschlagen (job %s): %s", job_id, stderr.decode()[:500])
            raise HTTPException(422, "YouTube-Download fehlgeschlagen. Bitte URL prüfen.")
    else:
        safe_ext = _safe_video_ext(video.filename or "")
        video_path = work_dir / f"input{safe_ext}"
        async with aiofiles.open(video_path, "wb") as f:
            await f.write(await video.read())

    background_tasks.add_task(
        run_dubbing_job,
        job_id=job_id,
        video_path=video_path,
        target_language=req.target_language,
        source_language=req.source_language,
        voice_id=req.voice_id,
        keep_original_audio=req.keep_original_audio,
        tts_engine=engine,
    )

    return DubbingStatus(job_id=job_id, status="pending", progress=0.0)


@app.get("/dub/status/{job_id}", response_model=DubbingStatus)
async def dub_status(job_id: str):
    try:
        _assert_safe_id(job_id, "job_id")
    except ValueError:
        raise HTTPException(400, "Ungültige job_id.")
    data = read_status(job_id)
    if data is None:
        raise HTTPException(404, "Job nicht gefunden.")
    return DubbingStatus(**data)


@app.get("/dub/download/{job_id}")
async def dub_download(job_id: str):
    try:
        _assert_safe_id(job_id, "job_id")
    except ValueError:
        raise HTTPException(400, "Ungültige job_id.")
    out = output_path(job_id, "mp4")
    if not out.exists():
        status = read_status(job_id)
        if status and status["status"] == "error":
            raise HTTPException(500, "Job fehlgeschlagen.")
        raise HTTPException(404, "Video noch nicht bereit.")
    return FileResponse(str(out), media_type="video/mp4", filename=f"dubbed_{job_id}.mp4")
