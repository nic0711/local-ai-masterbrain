# --- Build Stage ---
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Virtual environment erstellen und Abhängigkeiten installieren
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Runtime Stage ---
FROM python:3.12-slim-bookworm

WORKDIR /app

# System-Updates und curl für HEALTHCHECK
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user anlegen
RUN useradd --create-home --uid 1002 appuser

# Venv aus dem Builder-Stage übernehmen
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# App-Code kopieren
COPY --chown=appuser:appuser app.py .

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "30", "app:app"]
