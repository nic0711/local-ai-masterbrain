#!/bin/sh
# backup.sh – Erstellt ein Archiv der wichtigsten Konfigurationsdateien und Workflows.
# Wird aufgerufen von backup-daemon.sh als: /bin/sh /app/backup/backup.sh /app
# Container: docker:cli (alpine-basiert) – nur /bin/sh, kein bash, kein jq.
set -eu

APP_DIR="${1:-/app}"
BACKUP_DIR="/opt/backups"
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
NAME="backup_${TIMESTAMP}"
ARCHIVE="${BACKUP_DIR}/${NAME}.tar.gz"
META="${BACKUP_DIR}/${NAME}.meta.json"

mkdir -p "$BACKUP_DIR"

# Archiv erstellen: Workflows + Konfigurationsdateien aus /app
# 2>/dev/null || true: fehlende Dateien werden ignoriert
tar -czf "$ARCHIVE" \
    -C "$APP_DIR" \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    n8n/backup/workflows \
    docker-compose.yml \
    Caddyfile \
    .env.example \
    auth-gateway/app.py \
    auth-gateway/requirements.txt \
    dashboard/index.html \
    dashboard/style.css \
    dashboard/auth.js \
    dashboard/health.js \
    dashboard/admin.js \
    backup/backup-daemon.sh \
    backup/backup.sh \
    2>/dev/null || true

# Statistiken berechnen (POSIX-kompatibel, kein bc, kein awk)
SIZE=$(wc -c < "$ARCHIVE" 2>/dev/null || echo 0)
# wc -l gibt "  3 " zurück – Whitespace entfernen
FILES=$(tar -tzf "$ARCHIVE" 2>/dev/null | grep -v '/$' | wc -l)
FILES=$(printf '%s' "$FILES" | tr -d ' \t')
SIZE=$(printf '%s' "$SIZE" | tr -d ' \t')
TS=$(date -u +%s)

# Meta-JSON schreiben (ohne jq, manuell mit printf)
printf '{"name":"%s","timestamp":%s,"size":%s,"files":%s}\n' \
    "$NAME" "$TS" "$SIZE" "$FILES" > "$META"

# Cleanup: nur die letzten 10 Backups behalten
cd "$BACKUP_DIR"
COUNT=0
ls -t backup_*.tar.gz 2>/dev/null | while IFS= read -r old; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -gt 10 ]; then
        rm -f "$old" "${old%.tar.gz}.meta.json"
    fi
done

echo "Backup abgeschlossen: $ARCHIVE (${FILES} Dateien, ${SIZE} Bytes)"
