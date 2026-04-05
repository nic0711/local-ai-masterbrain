# 18. TTS Service – Voice Cloning & Video Dubbing

Der `tts-service` ist ein FastAPI-Container für lokales Text-to-Speech, Voice Cloning und Video-Dubbing.
Er basiert auf [OmniVoice](https://github.com/k2-fsa/OmniVoice) (k2-fsa) mit 600+ Sprachen und RTF 0.025.

---

## Architektur

```
n8n / Dashboard / Extern
    │
    ▼
tts-service:8003  (FastAPI, Python 3.11)
    ├── OmniVoice Engine   – k2-fsa/OmniVoice  (Hugging Face, ~2 GB)
    ├── faster-whisper     – Transkription mit Timestamps (Dubbing)
    ├── Ollama             – Übersetzung via qwen2.5:7b (bereits im Stack)
    └── ffmpeg             – Audio-Extraktion + Video-Merge
    │
    ▼
/data/voices  – Referenz-Stimmen (persistent, mounted: tts_storage/voices)
/data/output  – Fertige Videos   (mounted: tts_storage/output)
/data/temp    – Job-Dateien      (mounted: tts_storage/temp)
/data/models  – HF-Modell-Cache  (persistent, mounted: tts_storage/models)
```

---

## Setup

### 1. Verzeichnisse anlegen

```bash
mkdir -p tts_storage/{input,output,temp,models,voices}
```

### 2. .env ergänzen (optional)

```env
TTS_DEVICE=metal          # metal (Apple Silicon MPS) | cpu | cuda
TTS_HOSTNAME=tts.brain.local
WHISPER_MODEL=medium      # tiny/base/small/medium/large-v3
OLLAMA_TRANSLATE_MODEL=qwen2.5:7b-instruct-q4_K_M
```

### 3. Stack starten

```bash
docker compose up tts-service -d
```

> Beim ersten Start lädt OmniVoice das Modell (~2 GB) von HuggingFace.
> Der `start_period: 180s` im Healthcheck gibt dafür genug Zeit.

---

## Endpunkte

### GET `/health`

```json
{
  "status": "ok",
  "engine": "loaded",
  "device": "mps",
  "voices": ["meine_stimme", "sprecher2"],
  "disk_free_gb": 42.1
}
```

---

### GET `/voices`

Listet alle gespeicherten Referenz-Stimmen aus `/data/voices`.

```json
{ "voices": ["meine_stimme", "sprecher2"] }
```

---

### POST `/tts/synthesize`

Text → WAV (direkt, ohne Referenz-Audio).

```json
// Request
{
  "text": "Hallo Welt, dies ist ein Test.",
  "language": "de",
  "voice_id": "meine_stimme"   // optional – gespeicherte Referenzstimme
}

// Response: audio/wav (binary)
```

```bash
curl -X POST http://localhost:8003/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Hallo Welt", "language": "de"}' \
  --output test.wav
```

**Voice Design** (ohne Referenz-Audio, nur Attributbeschreibung):

```json
{ "text": "Hello world", "instruct": "female, british accent" }
```

---

### POST `/tts/clone`

Text + Referenz-Audio → WAV mit geklonter Stimme.

```
// Request: multipart/form-data
text          = "Dies ist meine geklonte Stimme"
reference_audio = <WAV/MP3/FLAC, 3–30 Sekunden>
ref_text        = "Transkription des Referenz-Audios"  // optional
save_as         = "meine_stimme"                        // optional – dauerhaft speichern
```

```bash
curl -X POST http://localhost:8003/tts/clone \
  -F "text=Dies ist meine geklonte Stimme" \
  -F "reference_audio=@stimme.wav" \
  -F "save_as=meine_stimme" \
  --output clone.wav
```

> `ref_text` ist optional – OmniVoice transkribiert das Referenz-Audio intern via Whisper.
> Bei `save_as` wird das Referenz-Audio dauerhaft in `/data/voices/` gespeichert.

---

### POST `/dub/video`

Video auf eine andere Sprache dubben (async Job).

```json
// Request – Option A: Datei-Upload (multipart/form-data)
video       = <MP4/MKV/MOV/...>
target_language  = "de"           // Zielsprache (de/en/fr/es/it/...)
source_language  = "en"           // optional – auto-detect wenn leer
voice_id         = "meine_stimme" // optional – Referenzstimme aus /data/voices
keep_original_audio = false        // original Tonspur als leise Hintergrundspur behalten

// Request – Option B: YouTube-URL (JSON)
{
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "target_language": "de",
  "voice_id": "meine_stimme"
}

// Response
{ "job_id": "3f8a2b1c-..." }
```

```bash
# Datei hochladen
curl -X POST http://localhost:8003/dub/video \
  -F "video=@vortrag_en.mp4" \
  -F "target_language=de" \
  -F "voice_id=meine_stimme"

# YouTube-URL
curl -X POST http://localhost:8003/dub/video \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://youtu.be/...", "target_language": "de"}'
```

---

### GET `/dub/status/{job_id}`

Dubbing-Fortschritt abfragen.

```json
{
  "job_id": "3f8a2b1c-...",
  "status": "synthesizing",   // extracting | transcribing | translating | synthesizing | merging | done | error
  "progress": 0.65,
  "error": null,
  "download_url": null        // gesetzt wenn status == "done"
}
```

---

### GET `/dub/download/{job_id}`

Fertiges Video herunterladen (`video/mp4`).

```bash
curl http://localhost:8003/dub/download/3f8a2b1c-... --output dubbed.mp4
```

---

## Dubbing-Pipeline

```
1. Audio-Extraktion    ffmpeg → audio.wav (16kHz, mono)
2. Transkription       faster-whisper → [(start, end, text), ...]
3. Übersetzung         Ollama qwen2.5:7b: Segment für Segment → Zielsprache
4. TTS pro Segment     OmniVoice mit Referenzstimme → audio_clips[]
5. Timing-Anpassung    librosa time_stretch wenn |factor - 1| > 15%
6. Audio-Aufbau        Clips an korrekten Zeitstempeln zusammensetzen → dubbed_audio.wav
7. Video-Merge         ffmpeg: Originalbild + neue Tonspur → output.mp4
```

---

## Unterstützte Sprachen (Auswahl)

OmniVoice unterstützt 600+ Sprachen. Für Dubbing/Übersetzung via Ollama sind alle Sprachen möglich, die das konfigurierte Modell beherrscht.

| Code | Sprache |
|------|---------|
| `de` | Deutsch |
| `en` | Englisch |
| `fr` | Französisch |
| `es` | Spanisch |
| `it` | Italienisch |
| `zh` | Chinesisch |
| `ja` | Japanisch |
| `pt` | Portugiesisch |

Vollständige Liste: [k2-fsa/OmniVoice/docs/languages.md](https://github.com/k2-fsa/OmniVoice/blob/master/docs/languages.md)

---

## Referenz-Audio Anforderungen

| Parameter | Wert |
|-----------|------|
| Dauer | 3–30 Sekunden |
| Format | WAV, MP3, FLAC |
| Empfehlung | 5–15s saubere Sprache, kein Hintergrundrauschen |
| `ref_text` | Optional – OmniVoice transkribiert intern |

---

## Device-Konfiguration

| `TTS_DEVICE` | Wirkung |
|---|---|
| `metal` (Default) | Apple Silicon MPS – deutlich schneller als CPU |
| `cpu` | CPU-Inference – universell |
| `cuda` | NVIDIA GPU – nur mit `--profile gpu-nvidia` |

---

## Speicher-Volumes

| Volume | Pfad im Container | Beschreibung |
|--------|-------------------|--------------|
| `tts_storage/voices` | `/data/voices` | Gespeicherte Referenzstimmen (persistent) |
| `tts_storage/models` | `/data/models` | OmniVoice + Whisper Modell-Cache (persistent) |
| `tts_storage/output` | `/data/output` | Fertige Dubbing-Videos |
| `tts_storage/temp` | `/data/temp` | Temporäre Job-Dateien (werden nach Download gelöscht) |
