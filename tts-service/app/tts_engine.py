import asyncio
import io
import logging
import os
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)

VOICES_DIR = Path("/data/voices")


def _resolve_device() -> str:
    requested = os.getenv("TTS_DEVICE", "metal").lower()
    if requested == "metal" and torch.backends.mps.is_available():
        return "mps"
    if requested == "cuda" and torch.cuda.is_available():
        return "cuda"
    return "cpu"


class TTSEngine:
    def __init__(self) -> None:
        self._model = None
        self.device = _resolve_device()
        logger.info("TTS device: %s", self.device)

    def load(self) -> None:
        if self._model is not None:
            return
        # F5-TTS lazy import – Modell wird beim ersten Load von HuggingFace gecacht
        from f5_tts.api import F5TTS  # type: ignore
        logger.info("Lade F5-TTS Modell (einmalig, kann einige Minuten dauern)...")
        self._model = F5TTS(device=self.device)
        logger.info("F5-TTS bereit.")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    # ------------------------------------------------------------------ #
    # Synthesize: Text → WAV-Bytes                                        #
    # ------------------------------------------------------------------ #
    def _synthesize_sync(
        self,
        text: str,
        ref_audio_path: Optional[str],
        ref_text: Optional[str],
    ) -> bytes:
        wav, sr, _ = self._model.infer(
            ref_file=ref_audio_path,
            ref_text=ref_text or "",
            gen_text=text,
            speed=1.0,
        )
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, wav, sr, format="WAV")
        return buf.getvalue()

    async def synthesize(
        self,
        text: str,
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
    ) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._synthesize_sync,
            text,
            ref_audio_path,
            ref_text,
        )

    # ------------------------------------------------------------------ #
    # Clone: Text + Referenz-Audio → WAV-Bytes                            #
    # ------------------------------------------------------------------ #
    async def clone_voice(
        self,
        text: str,
        ref_audio_path: str,
        ref_text: Optional[str] = None,
        save_as: Optional[str] = None,
    ) -> bytes:
        wav_bytes = await self.synthesize(text, ref_audio_path, ref_text)

        if save_as:
            dest = VOICES_DIR / f"{save_as}.wav"
            import shutil
            shutil.copy2(ref_audio_path, dest)
            logger.info("Referenzstimme gespeichert als: %s", dest)

        return wav_bytes


# Singleton
_engine: Optional[TTSEngine] = None


def get_engine() -> TTSEngine:
    global _engine
    if _engine is None:
        _engine = TTSEngine()
    return _engine
