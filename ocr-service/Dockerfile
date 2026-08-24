# --- Dependency-Build-Stage ---
# python:3.13-slim-bookworm statt bisher python:3.13-bullseye (Debian 11):
# Debian 12 hat aktuelle Security-Patches, bullseye ist deutlich aelter.
# Alle Python-Abhaengigkeiten installieren als vorgefertigte manylinux-Wheels
# (verifiziert) - kein Compiler/Build-Toolchain im Image noetig.
FROM python:3.13-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1 AS builder

ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt && \
    pip uninstall -y pip

# pip nach der letzten Paketinstallation entfernt, bevor das venv in die
# Runtime-Stage kopiert wird. Reines Build-/Installationswerkzeug, zur
# Laufzeit von app/ nicht importiert. Behebt (zusammen mit der
# System-pip-Entfernung in der Runtime-Stage, s.u.) zwei Trivy-Findings,
# die sich real gegen pips eigenes internes CycloneDX-SBOM (pip/_vendor/
# bom.cdx.json) richteten, nicht gegen echte Anwendungs-Abhaengigkeiten:
# msgpack (GHSA-6v7p-g79w-8964, hier gar nicht als eigenes Paket
# installiert) und setuptools/pkg_resources (CVE-2025-47273) sind in
# pip/_vendor/ als veraltete Kopien (1.1.2 bzw. 70.3.0) vorhanden,
# unabhaengig von der echten, bereits sicheren Installation
# setuptools==84.0.0 (Required-by torch), die unveraendert bestehen bleibt.

# --- Runtime-Stage ---
FROM python:3.13-slim-bookworm@sha256:00faa2debb87529f9f0764e9491d8ba400a3678976616c3bd7cb193745ac20d1

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Nur zur Laufzeit tatsaechlich benoetigte Libraries (kein wget/git/-dev-Header
# mehr - waren nur fuer den vormaligen Single-Stage-Build vorgehalten, hier
# nicht mehr noetig da Python-Pakete bereits als Wheels im venv liegen):
# curl fuer HEALTHCHECK, tesseract-ocr(-deu/-eng) + poppler-utils fuer OCR/PDF,
# libgl1/libglib2.0-0/libsm6/libxext6/libxrender1/libgomp1/libfontconfig1/
# libfreetype6 fuer opencv-python/Pillow, libopenblas0/liblapack3 (Runtime-
# statt -dev-Variante) fuer numpy/torch.
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    for i in $(seq 1 5); do \
        apt-get install -y --no-install-recommends \
        curl \
        tesseract-ocr \
        tesseract-ocr-deu \
        tesseract-ocr-eng \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        libfontconfig1 \
        libfreetype6 \
        libopenblas0 \
        liblapack3 \
        && break || sleep 10; \
    done && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# python:3.13-slim-bookworm bringt in der Runtime-Stage (frische FROM-Stufe,
# unabhaengig vom Builder) sein eigenes System-Python mit vorinstalliertem
# pip 26.2.1 mit - dessen internes CycloneDX-SBOM (pip/_vendor/bom.cdx.json)
# meldet ebenfalls die veralteten vendorten msgpack/setuptools-Kopien (real
# verifiziert, identischer Effekt wie bei tts-service: das Entfernen von
# pip im Builder-Venv allein reicht NICHT, dieses System-pip bleibt sonst
# unangetastet bestehen). Kein App-Code nutzt dieses System-Python (die
# Anwendung laeuft ausschliesslich ueber /opt/venv) - Entfernung ist sicher.
RUN python3 -m pip uninstall -y pip

RUN useradd --create-home --uid 1001 appuser

# Venv mit den Python-Abhaengigkeiten aus der Builder-Stage uebernehmen
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appuser app/ .

RUN mkdir -p /data/input /data/output /data/temp && \
    chown -R appuser:appuser /app /data

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]
