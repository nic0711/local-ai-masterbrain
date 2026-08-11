# Build-Context ist der Repo-Root (siehe docker-compose.yml, Service
# python-nlp-service), damit packages/python/masterbrain-common/ erreichbar
# ist. Siehe /.dockerignore fuer die verpflichtenden Build-Context-Ausschluesse.

# --- Dependency-Build-Stage (Drittanbieter, hash-verifiziert) ---
FROM python:3.14-slim-bookworm@sha256:4c92ffcde4dd6f1ff72a24518f49fd4990b27134987dfa31a733badde66df9f8 AS builder

WORKDIR /app

# Systemabhaengigkeiten nur fuer den Build (kompilieren von Paketen)
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY python-nlp-service/requirements.lock.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --require-hashes -r requirements.lock.txt

# SpaCy-Modelle: md = bestes RAM/Leistungs-Verhaeltnis ohne GPU
# sm: ~13 MB (zu ungenau), md: ~43 MB (gutes Gleichgewicht), lg: ~542 MB, trf: GPU noetig
RUN python -m spacy download de_core_news_md && \
    python -m spacy download en_core_web_md

# --- Wheel-Build-Stage (masterbrain-common) ---
FROM python:3.14-slim-bookworm@sha256:4c92ffcde4dd6f1ff72a24518f49fd4990b27134987dfa31a733badde66df9f8 AS wheel-builder

WORKDIR /build
RUN pip install --no-cache-dir build==1.3.0

COPY packages/python/masterbrain-common/ .
RUN python -m build --wheel --outdir /wheels && \
    sha256sum /wheels/*.whl > /wheels/checksum.sha256

# --- Runtime-Stage ---
FROM python:3.14-slim-bookworm@sha256:4c92ffcde4dd6f1ff72a24518f49fd4990b27134987dfa31a733badde66df9f8

ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}

WORKDIR /app

# curl fuer HEALTHCHECK - kein build-essential benoetigt
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user mit fixer UID fuer Reproduzierbarkeit (unveraendert aus der
# bisherigen 2-Stage-Version uebernommen)
RUN useradd --create-home --uid 1001 appuser

# Venv mit hash-verifizierten Drittanbieter-Abhaengigkeiten + spaCy-Modellen uebernehmen
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# masterbrain-common-Wheel: Checksumme pruefen, dann OHNE erneute
# Abhaengigkeitsaufloesung installieren (--no-deps) - seine Laufzeit-Deps
# (python-json-logger) sind bereits ueber requirements.lock.txt hash-verifiziert
# installiert.
COPY --from=wheel-builder /wheels/ /wheels/
RUN cd /wheels && sha256sum -c checksum.sha256 && \
    pip install --no-cache-dir --no-deps /wheels/*.whl && \
    rm -rf /wheels

# App-Code kopieren und Rechte setzen
COPY --chown=appuser:appuser python-nlp-service/app.py python-nlp-service/entrypoint.sh .
RUN chmod +x /app/entrypoint.sh

USER appuser

# Docker-nativer Health Check (nutzt /health Endpoint). Laengere Timings als
# beim auth-gateway wegen spaCy-Modell-Ladezeit beim Start.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

# Umgebungsvariablen fuer Gunicorn mit Standardwerten
ENV WORKERS=2
ENV THREADS=4
ENV TIMEOUT=120

ENTRYPOINT ["/app/entrypoint.sh"]
