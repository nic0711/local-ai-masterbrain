#!/bin/bash
set -euo pipefail

# --- Configuration ---
if [[ $# -eq 0 ]] ; then
    echo "Usage: $0 /path/to/backup_directory"
    echo "Example: $0 /opt/backups/20250723_103000"
    exit 1
fi

BACKUP_DIR=$(realpath "$1")
PROJECT_DIR=$(dirname "$(realpath "$0")")
DOCKER_COMPOSE_CMD="docker-compose"

if [[ ! -d "$BACKUP_DIR" ]]; then
    echo "ERROR: Backup directory not found at ${BACKUP_DIR}"
    exit 1
fi

# --- Preparation ---
echo "Starting recovery..."
echo "Project Directory: ${PROJECT_DIR}"
echo "Restoring from: ${BACKUP_DIR}"

echo "Stopping services before recovery..."
cd "$PROJECT_DIR"
${DOCKER_COMPOSE_CMD} down

# --- Docker Volume Restore ---
echo "Restoring Docker Volumes..."
COMPOSE_PROJECT_NAME=$(${DOCKER_COMPOSE_CMD} ps -q | head -n 1 | xargs docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' | tr -d '\r' || true)

if [[ -z "$COMPOSE_PROJECT_NAME" ]]; then
    # Fallback: try to guess from directory name if containers are not running
    COMPOSE_PROJECT_NAME=$(basename "$PROJECT_DIR")
    echo "Could not detect project name from running containers. Falling back to directory name: ${COMPOSE_PROJECT_NAME}"
fi

for archive in "$BACKUP_DIR"/volume_*.tar.gz; do
    if [[ ! -f "$archive" ]]; then continue; fi
    
    filename=$(basename "$archive")
    volume_name_part=$(echo "$filename" | sed -e 's/volume_//' -e 's/.tar.gz//')

    # Find the full volume name
    FULL_VOLUME_NAME_V2="${COMPOSE_PROJECT_NAME}-${volume_name_part}"
    FULL_VOLUME_NAME_V1="${COMPOSE_PROJECT_NAME}_${volume_name_part}"

    if docker volume inspect "$FULL_VOLUME_NAME_V2" &>/dev/null; then
        FULL_VOLUME_NAME=$FULL_VOLUME_NAME_V2
    elif docker volume inspect "$FULL_VOLUME_NAME_V1" &>/dev/null; then
        FULL_VOLUME_NAME=$FULL_VOLUME_NAME_V1
    else
        # If volume doesn't exist, create it before restoring
        echo "Volume for '${volume_name_part}' not found, creating it as ${FULL_VOLUME_NAME_V2}"
        docker volume create "$FULL_VOLUME_NAME_V2"
        FULL_VOLUME_NAME=$FULL_VOLUME_NAME_V2
    fi
    
    echo "  - Restoring volume: ${FULL_VOLUME_NAME} from ${filename}"
    docker run --rm \
        -v "${FULL_VOLUME_NAME}:/data" \
        -v "${BACKUP_DIR}:/backup" \
        alpine \
        sh -c "rm -rf /data/* /data/.[!.]* && tar xzf /backup/${filename} -C /data"
done

# --- Bind Mount Restore ---
echo "Restoring local directories (Bind Mounts)..."
for archive in "$BACKUP_DIR"/bind_mount_*.tar.gz; do
    if [[ ! -f "$archive" ]]; then continue; fi
    
    filename=$(basename "$archive")
    original_path=$(echo "$filename" | sed -e 's/bind_mount_//' -e 's/.tar.gz//' | tr '_' '/')
    
    echo "  - Restoring: ${original_path} from ${filename}"
    # Ensure parent directory exists
    mkdir -p "$(dirname "${PROJECT_DIR}/${original_path}")"
    tar xzf "$archive" -C "$(dirname "${PROJECT_DIR}/${original_path}")"
done

# --- Special Case: ~/.flowise ---
FLOWISE_ARCHIVE="${BACKUP_DIR}/flowise_home_config.tar.gz"
if [[ -f "$FLOWISE_ARCHIVE" ]]; then
    echo "Restoring ~/.flowise..."
    tar xzf "$FLOWISE_ARCHIVE" -C "$HOME"
else
    echo "INFO: Backup for ~/.flowise not found. Skipping."
fi

echo "Recovery finished successfully!"
echo "You can now start your services with: docker-compose up -d"
