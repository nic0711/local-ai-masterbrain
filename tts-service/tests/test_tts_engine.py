"""Regressionstests fuer TTSEngine._synthesize_sync (siehe Issue #142).

Kein echtes OmniVoice-Modell noetig: TTSEngine._model wird durch ein
Fake-Objekt mit kontrollierten generate()-Rueckgaben ersetzt. Deckt den
Konvertierungspfad audio_list[0] -> numpy.ndarray ab, der zuvor bei
numpy.ndarray-Rueckgaben mit AttributeError ('numpy.ndarray' object has
no attribute 'cpu') fehlschlug.

Lauf lokal: PYTHONPATH=../app python3 -m unittest discover -s . (aus
tts-service/tests/) bzw. wie in ci.yml/Dockerfile-Testjob mit
PYTHONPATH=/app im fertigen Runtime-Image.
"""

import io
import unittest

import numpy as np
import soundfile as sf
import torch

from tts_engine import TTSEngine


class _FakeModel:
    """Ersetzt OmniVoice.generate() durch eine feste, kontrollierte Rueckgabe."""

    def __init__(self, audio):
        self._audio = audio

    def generate(self, **kwargs):
        return [self._audio]


def _make_engine(audio) -> TTSEngine:
    engine = TTSEngine()
    engine._model = _FakeModel(audio)
    return engine


def _assert_valid_wav(test_case: unittest.TestCase, wav_bytes: bytes) -> None:
    test_case.assertGreater(len(wav_bytes), 0)
    data, samplerate = sf.read(io.BytesIO(wav_bytes))
    test_case.assertEqual(samplerate, 24000)
    test_case.assertGreater(len(data), 0)


class NumpyArrayOutputTests(unittest.TestCase):
    """Aktuell installierte omnivoice-Version (0.2.1) liefert numpy.ndarray
    (list[np.ndarray] laut Typannotation, real gegen das gebaute Image
    verifiziert - siehe Issue #142)."""

    def test_numpy_ndarray_produces_valid_wav(self):
        audio = np.sin(np.linspace(0.0, 2 * np.pi, 2400)).astype(np.float32)
        engine = _make_engine(audio)

        wav_bytes = engine._synthesize_sync("Test", None, None)

        _assert_valid_wav(self, wav_bytes)

    def test_ndarray_with_extra_dims_is_squeezed(self):
        # OmniVoice liefert je nach Pfad ggf. eine (1, N)-Form.
        audio = np.sin(np.linspace(0.0, 2 * np.pi, 2400)).astype(np.float32).reshape(1, -1)
        engine = _make_engine(audio)

        wav_bytes = engine._synthesize_sync("Test", None, None)

        _assert_valid_wav(self, wav_bytes)


class TorchTensorOutputTests(unittest.TestCase):
    """Rueckwaertskompatibilitaet: eine kuenftige omnivoice-Version, die
    wieder torch.Tensor liefert, darf nicht erneut brechen."""

    def test_torch_tensor_produces_valid_wav(self):
        audio = torch.sin(torch.linspace(0.0, 2 * 3.14159, 2400))
        engine = _make_engine(audio)

        wav_bytes = engine._synthesize_sync("Test", None, None)

        _assert_valid_wav(self, wav_bytes)


class UnexpectedOutputTests(unittest.TestCase):
    def test_unknown_type_raises_type_error(self):
        engine = _make_engine(audio=["nicht", "numerisch"])

        with self.assertRaises(TypeError):
            engine._synthesize_sync("Test", None, None)

    def test_empty_array_raises_value_error(self):
        engine = _make_engine(audio=np.array([], dtype=np.float32))

        with self.assertRaises(ValueError):
            engine._synthesize_sync("Test", None, None)


if __name__ == "__main__":
    unittest.main()
