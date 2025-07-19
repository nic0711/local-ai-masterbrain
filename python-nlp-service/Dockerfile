# Stage 1: Builder - Installiert Abhängigkeiten und lädt Modelle
FROM python:3.11-slim as builder

WORKDIR /app

# Systemabhängigkeiten für den Fall, dass Pakete kompiliert werden müssen
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

# requirements.txt kopieren und Abhängigkeiten installieren
# Dies wird gecached, solange sich die requirements.txt nicht ändert
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# SpaCy-Modell herunterladen
RUN python -m spacy download de_core_news_sm

# Stage 2: Runner - Das eigentliche, schlanke Image
FROM python:3.11-slim

WORKDIR /app

# Einen non-root user erstellen und verwenden für mehr Sicherheit
RUN useradd --create-home appuser
USER appuser

# Abhängigkeiten und SpaCy-Modell aus dem Builder-Stage kopieren
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# App-Code kopieren
COPY --chown=appuser:appuser . .

# Port freigeben, auf dem Gunicorn lauschen wird
EXPOSE 5000

# Den Service mit Gunicorn starten
# Der Name 'app' vor dem Doppelpunkt muss dem Dateinamen app.py entsprechen.
# Der Name 'app' nach dem Doppelpunkt muss dem Flask-App-Objekt (app = Flask(__name__)) entsprechen.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--worker-class", "gthread", "app:app"]