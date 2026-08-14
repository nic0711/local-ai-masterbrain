# --- Dependency-Build-Stage ---
# python:3.13-slim-bookworm statt bisher python:3.13-bullseye (Debian 11):
# Debian 12 hat aktuelle Security-Patches, bullseye ist deutlich aelter.
# Kompatibilitaet real geprueft (torch, torchaudio, omnivoice, faster-whisper,
# librosa, soundfile) - alle Python-Abhaengigkeiten installieren als
# vorgefertigte manylinux-Wheels, kein Compiler/Build-Toolchain im Image noetig.
FROM python:3.13-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1 AS builder

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt

# --- Runtime-Stage ---
FROM python:3.13-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Nur zur Laufzeit tatsaechlich benoetigte Libraries (kein wget/git/-dev-Header
# mehr - Python-Pakete liegen bereits als Wheels im venv, soundfile bringt
# seine eigene libsndfile mit): curl fuer HEALTHCHECK, ffmpeg fuer
# Audio/Video-Verarbeitung (Dubbing), libsndfile1 als Systemlib-Fallback,
# libgl1/libglib2.0-0/libsm6/libxext6/libxrender1/libgomp1 fuer die
# Bildverarbeitungs-Abhaengigkeiten von librosa/scikit-learn/numba.
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    for i in $(seq 1 5); do \
        apt-get install -y --no-install-recommends \
        curl \
        ffmpeg \
        libsndfile1 \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        && break || sleep 10; \
    done && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1001 appuser

# Venv mit den Python-Abhaengigkeiten aus der Builder-Stage uebernehmen
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appuser app/ .

RUN mkdir -p /data/input /data/output /data/temp /data/models /data/voices && \
    chown -R appuser:appuser /app /data

USER appuser

HEALTHCHECK --interval=30s --timeout=15s --start-period=180s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

EXPOSE 8003

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "1"]
