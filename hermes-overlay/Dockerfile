# Overlay ueber dem unveraenderten Hermes-Upstream-Build (Submodule hermes-agent/):
# hebt einzelne Python-Abhaengigkeiten mit behebbaren CVEs an, ohne das Submodule
# zu aendern. Pins bewusst exakt; bei einem Submodule-Bump pruefen, ob sie noch
# noetig sind (scripts/scan-running.sh).
FROM base
USER root
RUN uv pip install --python /opt/hermes/.venv/bin/python --no-cache-dir --no-deps \
        "Pillow==13.0.0" \
        "PyJWT==2.14.0"
