#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -euo pipefail

# --- Configuration ---
# The script automatically determines the project directory.
# You can override it by passing a path as the first argument.
PROJECT_DIR_PARAM="${1:-}"
if [[ -n "$PROJECT_DIR_PARAM" ]]; then
    PROJECT_DIR=$(realpath "$PROJECT_DIR_PARAM")
else
    PROJECT_DIR=$(dirname "$(realpath "$0")")
fi

# Root directory for all backups
BACKUP_BASE_DIR="/opt/backups"
# Timestamp for the current backup folder
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
# Full path for the current backup
BACKUP_DIR="${BACKUP_BASE_DIR}/${TIMESTAMP}"
# Number of days to keep backups
RETENTION_DAYS=7
# Docker Compose command (use 'docker compose' for v2)
DOCKER_COMPOSE_CMD="docker-compose"

# --- Preparation ---
echo "Starting backup..."
echo "Project Directory: ${PROJECT_DIR}"
echo "Backup Directory: ${BACKUP_DIR}"

# Create the backup directory
mkdir -p "$BACKUP_DIR"

# --- Docker Volume Backup ---
echo "Backing up Docker Volumes..."

# Get the project name prefix from Docker Compose
# This is crucial as Docker prepends it to volume names.
COMPOSE_PROJECT_NAME=$(${DOCKER_COMPOSE_CMD} -f "${PROJECT_DIR}/docker-compose.yml" ps -q | head -n 1 | xargs docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' | tr -d '\r')

if [[ -z "$COMPOSE_PROJECT_NAME" ]]; then
    echo "ERROR: Could not determine Docker Compose project name. Are the containers running?"
    exit 1
fi
echo "Docker Compose project name (prefix): ${COMPOSE_PROJECT_NAME}"

VOLUMES_TO_BACKUP=(
    "n8n_storage"
    "ollama_storage"
    "qdrant_storage"
    "open-webui"
    "flowise"
    "caddy-data"
    "caddy-config"
    "valkey-data"
    "langfuse_postgres_data"
    "langfuse_clickhouse_data"
    "langfuse_clickhouse_logs"
    "langfuse_minio_data"
    "supabase_db"
    "supabase_storage"
)

for volume in "${VOLUMES_TO_BACKUP[@]}"; do
    # Docker Compose v2 uses '-' as a separator, v1 uses '_'
    FULL_VOLUME_NAME_V2="${COMPOSE_PROJECT_NAME}-${volume}"
    FULL_VOLUME_NAME_V1="${COMPOSE_PROJECT_NAME}_${volume}"

    if docker volume inspect "$FULL_VOLUME_NAME_V2" &>/dev/null; then
        FULL_VOLUME_NAME=$FULL_VOLUME_NAME_V2
    elif docker volume inspect "$FULL_VOLUME_NAME_V1" &>/dev/null; then
        FULL_VOLUME_NAME=$FULL_VOLUME_NAME_V1
    else
        echo "WARNING: Volume for '${volume}' with prefix '${COMPOSE_PROJECT_NAME}' not found. Skipping."
        continue
    fi

    echo "  - Backing up volume: ${FULL_VOLUME_NAME}"
    docker run --rm \
        -v "${FULL_VOLUME_NAME}:/data:ro" \
        -v "${BACKUP_DIR}:/backup" \
        alpine \
        tar czf "/backup/volume_${volume}.tar.gz" -C /data .
done

# --- Bind Mount Backup ---
echo "Backing up local directories (Bind Mounts)..."

BIND_MOUNTS_TO_BACKUP=(
    "neo4j"
    "Caddyfile"
    "caddy-addon"
    "n8n/backup"
    "shared"
    "searxng"
    "crawl4ai-data"
    "dashboard"
)

for mount in "${BIND_MOUNTS_TO_BACKUP[@]}"; do
    SOURCE_PATH="${PROJECT_DIR}/${mount}"
    if [[ -e "$SOURCE_PATH" ]]; then
        echo "  - Backing up: ${mount}"
        DEST_ARCHIVE_PATH="bind_mount_$(echo "$mount" | tr '/' '_').tar.gz"
        tar czf "${BACKUP_DIR}/${DEST_ARCHIVE_PATH}" -C "$(dirname "$SOURCE_PATH")" "$(basename "$SOURCE_PATH")"
    else
        echo "WARNING: Path ${SOURCE_PATH} not found. Skipping."
    fi
done

# --- Special Case: ~/.flowise ---
# This path is user-dependent.
FLOWISE_HOME_DIR="${HOME}/.flowise"
if [[ -d "$FLOWISE_HOME_DIR" ]]; then
    echo "Backing up ~/.flowise..."
    tar czf "${BACKUP_DIR}/flowise_home_config.tar.gz" -C "$(dirname "$FLOWISE_HOME_DIR")" "$(basename "$FLOWISE_HOME_DIR")"
else
    echo "INFO: Directory ~/.flowise not found. Skipping."
fi

# --- .env Backup (enthält Secrets – restriktive Berechtigungen) ---
echo "Backing up .env configuration..."
ENV_FILE="${PROJECT_DIR}/.env"
if [[ -f "$ENV_FILE" ]]; then
    echo "  - Backing up .env (contains secrets – keep secure!)"
    cp "${ENV_FILE}" "${BACKUP_DIR}/.env"
    chmod 600 "${BACKUP_DIR}/.env"
else
    echo "INFO: .env file not found at ${ENV_FILE}. Skipping."
fi

# --- Cleanup Old Backups ---
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_BASE_DIR}" -type d -mtime +${RETENTION_DAYS} -exec echo "  - Deleting old backup: {}" \; -exec rm -rf {} \;

echo "Backup finished successfully!"
echo "Saved to: ${BACKUP_DIR}"