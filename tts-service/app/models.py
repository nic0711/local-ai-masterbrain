from typing import Optional
from pydantic import BaseModel, Field


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="de")
    voice_id: Optional[str] = Field(default=None, description="ID einer gespeicherten Referenzstimme")
    output_format: str = Field(default="wav", pattern="^(wav|mp3)$")


class DubbingRequest(BaseModel):
    youtube_url: Optional[str] = Field(default=None, description="YouTube-URL des Videos")
    target_language: str = Field(default="de", description="Zielsprache (de, en, fr, es, ...)")
    source_language: Optional[str] = Field(default=None, description="Quellsprache (auto-detect wenn None)")
    voice_id: Optional[str] = Field(default=None, description="Referenzstimme für TTS (None = Standard)")
    keep_original_audio: bool = Field(default=False, description="Original-Tonspur leise als Hintergrund")
    whisper_model: Optional[str] = Field(default=None, description="Whisper-Modell-Override (tiny/base/small/medium/large-v3)")


class DubbingStatus(BaseModel):
    job_id: str
    status: str = Field(description="pending|extracting|transcribing|translating|synthesizing|merging|done|error")
    progress: float = Field(ge=0.0, le=1.0)
    download_url: Optional[str] = None
    error: Optional[str] = None


class VoiceInfo(BaseModel):
    voice_id: str
    filename: str
    duration_seconds: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    tts_engine_loaded: bool
    whisper_ready: bool
    ollama_reachable: bool
    device: str
    disk_free_gb: float
