# Build-Context ist der Repo-Root (siehe docker-compose.yml, Service
# auth-gateway), damit packages/python/masterbrain-common/ erreichbar ist.
# Siehe /.dockerignore fuer die verpflichtenden Build-Context-Ausschluesse.

# --- Dependency-Build-Stage (Drittanbieter, hash-verifiziert) ---
FROM python:3.14-slim-bookworm@sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52 AS builder

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY auth-gateway/requirements.lock.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --require-hashes -r requirements.lock.txt

# --- Wheel-Build-Stage (masterbrain-common) ---
FROM python:3.14-slim-bookworm@sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52 AS wheel-builder

WORKDIR /build
RUN pip install --no-cache-dir build==1.3.0

COPY packages/python/masterbrain-common/ .
RUN python -m build --wheel --outdir /wheels && \
    sha256sum /wheels/*.whl > /wheels/checksum.sha256

# --- Runtime-Stage ---
FROM python:3.14-slim-bookworm@sha256:23c59390fc717bf09f9336908199a0ae75d9c4264bf296123f94ad772fea3b52

ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}

WORKDIR /app

# System-Updates, curl für HEALTHCHECK und Docker CLI für Service-Control
# (subprocess-Aufrufe fuer `docker compose up` bei optionalen Services;
# der Docker-SDK-Zugriff selbst laeuft ueber das pip-Paket "docker", nicht
# ueber diese CLI - beide bleiben unabhaengig voneinander noetig)
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    . /etc/os-release && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# Non-root user anlegen
RUN useradd --create-home --uid 1002 appuser

# Venv mit hash-verifizierten Drittanbieter-Abhaengigkeiten uebernehmen
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# masterbrain-common-Wheel: Checksumme pruefen, dann OHNE erneute
# Abhaengigkeitsaufloesung installieren (--no-deps) - seine Laufzeit-Deps
# (PyJWT, python-json-logger) sind bereits ueber requirements.lock.txt
# hash-verifiziert installiert.
COPY --from=wheel-builder /wheels/ /wheels/
RUN cd /wheels && sha256sum -c checksum.sha256 && \
    pip install --no-cache-dir --no-deps /wheels/*.whl && \
    cd /app && rm -rf /wheels && \
    pip uninstall -y pip && \
    /usr/local/bin/python -m pip uninstall -y pip

# Sowohl das Venv-pip (Zeile darueber, via PATH=/opt/venv/bin) als auch
# das globale Base-Image-pip unter /usr/local (separate Installation,
# von PATH unabhaengig) werden nach der letzten Paketinstallation
# entfernt: reines Build-/Installationswerkzeug, zur Laufzeit von
# app.py/masterbrain_common nicht importiert. Ohne den zweiten,
# expliziten Aufruf bliebe das globale pip unangetastet und wuerde seine
# vendorten Abhaengigkeiten weiterhin fuer Trivy sichtbar machen.
#
# Behebt zugleich zwei Trivy-Findings, die sich real gegen pips eigenes
# internes CycloneDX-SBOM (pip/_vendor/bom.cdx.json) und nicht gegen
# echte Anwendungs-Abhaengigkeiten richteten: msgpack 1.1.2
# (GHSA-6v7p-g79w-8964) und setuptools/pkg_resources 70.3.0
# (CVE-2025-47273) sind beide nur als von pip vendorte Kopien vorhanden,
# nicht als eigenstaendig installierte Pakete (verifiziert: importlib.metadata
# fand vor diesem Fix weder msgpack noch setuptools als installierte
# Runtime-Pakete - die Vendored-Kopien blieben unabhaengig davon fuer
# Trivy sichtbar, solange irgendeine pip-Installation im Image vorhanden war).

# App-Code kopieren
COPY --chown=appuser:appuser auth-gateway/app.py .

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

EXPOSE 5001

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--worker-class", "gthread", "--threads", "16", "--timeout", "30", "app:app"]
