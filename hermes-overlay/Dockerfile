# Overlay ueber dem unveraenderten Hermes-Upstream-Build (Submodule hermes-agent/):
# hebt einzelne Python-Abhaengigkeiten mit behebbaren CVEs an, ohne das Submodule
# zu aendern. Pins bewusst exakt; bei einem Submodule-Bump pruefen, ob sie noch
# noetig sind (scripts/scan-running.sh).
FROM base
USER root
RUN uv pip install --python /opt/hermes/.venv/bin/python --no-cache-dir --no-deps \
        "Pillow==13.0.0" \
        "PyJWT==2.14.0" \
        "aiohttp==3.14.4" \
        "yarl==1.25.1" \
        "urllib3==2.8.0" \
        "tornado==6.5.9" \
        "certifi==2026.10.18" \
        "anyio==4.14.2" \
        "brotlicffi==1.2.1.0" \
        "httpcore2==2.12.0" \
        "httpx2==2.12.0"
RUN apt-get -o Acquire::Retries=3 update && \
    apt-get -o Acquire::Retries=3 upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
