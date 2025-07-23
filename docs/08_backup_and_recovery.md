# 8. Backup & Recovery

A robust backup and recovery strategy is critical for protecting your data against loss and for facilitating server migrations. This guide provides a comprehensive script to back up all persistent data from the stack and a corresponding script to restore it.

## Understanding What Is Backed Up

This stack stores persistent data in two ways:
1.  **Docker Volumes:** Managed by Docker, these store data for services like databases (Supabase, Langfuse), vector stores (Qdrant), and application data (n8n, Ollama models).
2.  **Bind Mounts:** These are local directories or files from your project folder that are mounted into containers (e.g., `./neo4j/data`, `./Caddyfile`).

The provided scripts are designed to find and archive **all** of these locations as defined in your `docker-compose.yml` files. Any data stored inside a container but *not* in a volume or bind mount is considered ephemeral and is not designed to be persisted.

---

## The Backup Process

### 1. The Backup Script (`backup.sh`)

This script automates the backup of all volumes and bind mounts.

```bash
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

# --- Cleanup Old Backups ---
echo "Cleaning up old backups (older than ${RETENTION_DAYS} days)..."
find "${BACKUP_BASE_DIR}" -type d -mtime +${RETENTION_DAYS} -exec echo "  - Deleting old backup: {}" \; -exec rm -rf {} \;

echo "Backup finished successfully!"
echo "Saved to: ${BACKUP_DIR}"
```

### 2. How to Use the Backup Script

1.  **Save the Script:** Save the code above into a file named `backup.sh` in the root of your project directory.

2.  **Make it Executable:**
    ```sh
    chmod +x backup.sh
    ```

3.  **Run a Manual Test:**
    ```sh
    ./backup.sh
    ```
    Verify that a new timestamped directory is created in `/opt/backups` (or your configured `BACKUP_BASE_DIR`) and that it contains `.tar.gz` files.

4.  **Schedule with Cron:**
    Edit your crontab file:
    ```sh
    crontab -e
    ```
    Add the following line to run the backup every day at 2:00 AM. This example assumes your project is located at `/path/to/your/project`.

    ```crontab
    # m h  dom mon dow   command
    0 2 * * * /path/to/your/project/backup.sh > /tmp/backup.log 2>&1
    ```
    **Note:** The cron job should run as the user who manages the Docker stack to ensure it has the correct permissions and that `${HOME}` resolves correctly for `~/.flowise`.

---

## The Recovery Process

Use this process to restore your data to a fresh installation on a new server.

### 1. The Recovery Script (`restore.sh`)

This script stops the services, restores all data from a backup archive, and prepares the stack to be started again.

```bash
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
```

### 2. How to Restore From a Backup

1.  **Prepare the New Server:**
    *   Clone the project repository: `git clone ...`
    *   Install Docker and Docker Compose.
    *   Copy your `.env` file with all the necessary secrets to the project's root directory.

2.  **Transfer Your Backup:**
    *   Copy your latest backup folder (e.g., `20250723_103000`) to the new server (e.g., into `/opt/backups`).

3.  **Save the Restore Script:**
    *   Save the code above into a file named `restore.sh` in the root of your project directory.

4.  **Make it Executable:**
    ```sh
    chmod +x restore.sh
    ```

5.  **Run the Restore:**
    *   Execute the script, passing the full path to the specific backup directory you want to restore.

    ```sh
    # Example:
    ./restore.sh /opt/backups/20250723_103000
    ```
    The script will stop any running containers, create the necessary Docker volumes if they don't exist, and unpack all the data into the correct volumes and local directories.

6.  **Start the Stack:**
    *   Once the script is finished, start all services.
    ```sh
    docker-compose up -d
    ```
    Verify that your applications (n8n, Supabase, etc.) are running and that all your data has been restored correctly.