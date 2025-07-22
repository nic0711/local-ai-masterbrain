# Stage 1: Builder - Installiert Abhängigkeiten und lädt Modelle
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Systemabhängigkeiten für den Fall, dass Pakete kompiliert werden müssen
# Update system packages to patch vulnerabilities
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

# requirements.txt kopieren und Abhängigkeiten installieren
# Dies wird gecached, solange sich die requirements.txt nicht ändert
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --upgrade -r requirements.txt

# SpaCy-Modell herunterladen
RUN python -m spacy download de_core_news_sm

# Stage 2: Runner - Das eigentliche, schlanke Image
FROM python:3.11-slim-bookworm

# Update system packages to patch vulnerabilities
RUN apt-get update && apt-get upgrade -y --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Einen non-root user erstellen und verwenden für mehr Sicherheit
RUN useradd --create-home appuser
USER appuser

# Abhängigkeiten und SpaCy-Modell aus dem Builder-Stage kopieren
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# App-Code kopieren
COPY --chown=appuser:appuser . .

# Entrypoint-Skript kopieren und ausführbar machen
COPY --chown=appuser:appuser entrypoint.sh .

# Port freigeben, auf dem Gunicorn lauschen wird
EXPOSE 5000

# Umgebungsvariablen für Gunicorn mit Standardwerten
ENV WORKERS=2
ENV THREADS=4
ENV TIMEOUT=120

# Den Service mit Gunicorn starten
ENTRYPOINT ["/app/entrypoint.sh"]
