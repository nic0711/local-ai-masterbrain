# Stage 1: Builder - Abhängigkeiten installieren und Modelle laden
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Systemabhängigkeiten nur für den Build (kompilieren von Paketen)
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Virtual Environment erstellen - sauberer als direktes Kopieren von site-packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# requirements.txt kopieren und Abhängigkeiten installieren
# (gecached solange sich requirements.txt nicht ändert)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# SpaCy-Modell: de_core_news_md = bestes RAM/Leistungs-Verhältnis ohne GPU
# sm: ~13 MB (zu ungenau), md: ~43 MB (gutes Gleichgewicht), lg: ~542 MB, trf: GPU nötig
RUN python -m spacy download de_core_news_md


# Stage 2: Runner - Schlankes Laufzeit-Image
FROM python:3.12-slim-bookworm

# curl für HEALTHCHECK - kein build-essential benötigt
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Non-root user mit fixer UID für Reproduzierbarkeit
RUN useradd --create-home --uid 1001 appuser

# Virtual Environment aus Builder übernehmen (nur Runtime-Abhängigkeiten, kein pip/build-tools)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# App-Code kopieren und Rechte setzen
COPY --chown=appuser:appuser . .
RUN chmod +x /app/entrypoint.sh

USER appuser

# Docker-nativer Health Check (nutzt /health Endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Port freigeben, auf dem Gunicorn lauscht
EXPOSE 5000

# Umgebungsvariablen für Gunicorn mit Standardwerten
ENV WORKERS=2
ENV THREADS=4
ENV TIMEOUT=120

# Den Service mit Gunicorn starten
ENTRYPOINT ["/app/entrypoint.sh"]
