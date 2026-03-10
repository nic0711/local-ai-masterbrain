#!/bin/sh
# backup-daemon.sh – Läuft im backup-cron Container (alpine/busybox sh).
# Triggert Backups periodisch und auf Anforderung über eine Trigger-Datei.
# Unterstützt auch Restore-Trigger für Workflow-Wiederherstellung.
set -eu

TRIGGER_FILE="${TRIGGER_FILE:-/opt/backups/.trigger}"
BACKUP_INTERVAL_H="${BACKUP_INTERVAL_H:-24}"

BACKUP_DIR="$(dirname "$TRIGGER_FILE")"
STATUS_FILE="${BACKUP_DIR}/.backup_status"
RESTORE_TRIGGER="${BACKUP_DIR}/.restore"

log() {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

# Sicherstellen, dass das Backup-Verzeichnis existiert
mkdir -p "$BACKUP_DIR"

# Initialstatus schreiben
echo "idle:0" > "$STATUS_FILE"
log "Backup-Daemon gestartet. Trigger: $TRIGGER_FILE, Intervall: ${BACKUP_INTERVAL_H}h"

run_backup() {
    TS="$(date -u +%s)"
    echo "running:${TS}" > "$STATUS_FILE"
    log "Backup wird gestartet…"

    if /bin/sh /app/backup/backup.sh /app; then
        TS_DONE="$(date -u +%s)"
        echo "success:${TS_DONE}" > "$STATUS_FILE"
        log "Backup erfolgreich abgeschlossen."
    else
        TS_DONE="$(date -u +%s)"
        echo "failed:${TS_DONE}" > "$STATUS_FILE"
        log "Backup fehlgeschlagen!"
    fi
}

run_restore() {
    RESTORE_FILE="$1"
    log "Restore-Trigger erkannt: $RESTORE_FILE"

    # Restore-Datei lesen: erste Zeile = Backup-Name
    BACKUP_NAME=$(head -1 "$RESTORE_FILE")
    ARCHIVE="${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"

    if [ ! -f "$ARCHIVE" ]; then
        log "Fehler: Backup-Archiv nicht gefunden: $ARCHIVE"
        rm -f "$RESTORE_FILE"
        return 1
    fi

    log "Stelle Workflows wieder her aus: $ARCHIVE"

    # /opt/workflows-restore ist auf ./n8n/backup/workflows gemountet (rw)
    if [ -d "/opt/workflows-restore" ]; then
        # Nur .json Dateien aus n8n/backup/workflows/ extrahieren
        tar -tzf "$ARCHIVE" | grep '^n8n/backup/workflows/.*\.json$' | while IFS= read -r filepath; do
            FILENAME=$(basename "$filepath")
            # Datei in tmp-Pfad extrahieren und dann ins Zielverzeichnis kopieren
            mkdir -p "/tmp/$(dirname "$filepath")"
            tar -xzf "$ARCHIVE" -C /tmp "$filepath" 2>/dev/null || continue
            cp "/tmp/$filepath" "/opt/workflows-restore/$FILENAME"
            rm -f "/tmp/$filepath"
            log "Wiederhergestellt: $FILENAME"
        done
        log "Restore abgeschlossen."
    else
        log "Warnung: /opt/workflows-restore nicht gemountet – kein Restore möglich."
    fi

    rm -f "$RESTORE_FILE"
}

# Beim ersten Start: letzten Backup-Zeitpunkt auf jetzt setzen,
# damit kein sofortiges Backup beim Containerstart ausgeführt wird.
LAST_BACKUP="$(date -u +%s)"
INTERVAL_SEC="$((BACKUP_INTERVAL_H * 3600))"

while true; do
    sleep 30

    NOW="$(date -u +%s)"

    # Restore-Trigger prüfen (Priorität vor Backup)
    if [ -f "$RESTORE_TRIGGER" ]; then
        run_restore "$RESTORE_TRIGGER"
    elif [ -f "$TRIGGER_FILE" ]; then
        log "Trigger-Datei erkannt – manuelles Backup."
        rm -f "$TRIGGER_FILE"
        run_backup
        LAST_BACKUP="$(date -u +%s)"
    elif [ "$((NOW - LAST_BACKUP))" -ge "$INTERVAL_SEC" ]; then
        log "Intervall erreicht – automatisches Backup."
        run_backup
        LAST_BACKUP="$(date -u +%s)"
    fi
done
