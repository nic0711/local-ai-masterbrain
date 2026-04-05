import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, AnyHttpUrl

# Erlaubte Zeichen für IDs und Namen (kein Pfad-Traversal möglich)
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
_SAFE_LANG_RE = re.compile(r"^[a-z]{2,8}$")
_ALLOWED_AUDIO_EXT = {".wav", ".mp3", ".flac"}
_ALLOWED_VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
_ALLOWED_YT_HOSTS = {"youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"}


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="de")
    voice_id: Optional[str] = Field(default=None, description="ID einer gespeicherten Referenzstimme")
    output_format: str = Field(default="wav", pattern="^(wav|mp3)$")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if not _SAFE_LANG_RE.match(v):
            raise ValueError("Ungültige Sprachkennung.")
        return v

    @field_validator("voice_id")
    @classmethod
    def validate_voice_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _SAFE_ID_RE.match(v):
            raise ValueError("voice_id darf nur Buchstaben, Zahlen, - und _ enthalten.")
        return v


class DubbingRequest(BaseModel):
    youtube_url: Optional[str] = Field(default=None, description="YouTube-URL des Videos")
    target_language: str = Field(default="de", description="Zielsprache (de, en, fr, es, ...)")
    source_language: Optional[str] = Field(default=None, description="Quellsprache (auto-detect wenn None)")
    voice_id: Optional[str] = Field(default=None, description="Referenzstimme für TTS (None = Standard)")
    keep_original_audio: bool = Field(default=False, description="Original-Tonspur leise als Hintergrund")
    whisper_model: Optional[str] = Field(default=None, description="Whisper-Modell-Override (tiny/base/small/medium/large-v3)")

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from urllib.parse import urlparse
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Nur HTTP/HTTPS URLs erlaubt.")
        if parsed.netloc not in _ALLOWED_YT_HOSTS:
            raise ValueError("Nur YouTube-URLs erlaubt.")
        return v

    @field_validator("target_language", "source_language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _SAFE_LANG_RE.match(v):
            raise ValueError("Ungültige Sprachkennung.")
        return v

    @field_validator("voice_id")
    @classmethod
    def validate_voice_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _SAFE_ID_RE.match(v):
            raise ValueError("voice_id darf nur Buchstaben, Zahlen, - und _ enthalten.")
        return v

    @field_validator("whisper_model")
    @classmethod
    def validate_whisper_model(cls, v: Optional[str]) -> Optional[str]:
        allowed = {None, "tiny", "base", "small", "medium", "large-v2", "large-v3"}
        if v not in allowed:
            raise ValueError(f"Ungültiges Whisper-Modell. Erlaubt: {allowed - {None}}")
        return v


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
