import asyncio
import io
import logging
import os
import re
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger(__name__)

VOICES_DIR = Path("/data/voices")
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _resolve_device() -> str:
    requested = os.getenv("TTS_DEVICE", "metal").lower()
    if requested in ("metal", "mps") and torch.backends.mps.is_available():
        return "mps"
    if requested == "cuda" and torch.cuda.is_available():
        return "cuda:0"
    return "cpu"


class TTSEngine:
    def __init__(self) -> None:
        self._model = None
        self.device = _resolve_device()
        logger.info("TTS device: %s", self.device)

    def load(self) -> None:
        if self._model is not None:
            return
        from omnivoice import OmniVoice  # type: ignore
        logger.info("Lade OmniVoice Modell (einmalig, kann einige Minuten dauern)...")
        self._model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=self.device)
        logger.info("OmniVoice bereit.")

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
        import soundfile as sf
        kwargs: dict = {"text": text}
        if ref_audio_path:
            kwargs["ref_audio"] = ref_audio_path
            if ref_text:
                kwargs["ref_text"] = ref_text
            # ref_text optional – OmniVoice transkribiert intern via Whisper
        audio_list = self._model.generate(**kwargs)
        wav = audio_list[0].squeeze().cpu().numpy()
        buf = io.BytesIO()
        sf.write(buf, wav, 24000, format="WAV")
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
            if not _SAFE_ID_RE.match(save_as):
                raise ValueError("Ungültiger save_as Name.")
            dest = (VOICES_DIR / f"{save_as}.wav").resolve()
            voices_resolved = VOICES_DIR.resolve()
            try:
                dest.relative_to(voices_resolved)
            except ValueError:
                raise ValueError("Ungültiger Zieldateipfad.")
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
