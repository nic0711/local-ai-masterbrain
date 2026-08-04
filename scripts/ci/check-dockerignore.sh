#!/usr/bin/env bash
# Prueft, dass die Root-.dockerignore alle in Korrektur 4 (Phase 2A)
# geforderten Pflicht-Ausschlussmuster tatsaechlich enthaelt.
set -euo pipefail

FILE=".dockerignore"

if [[ ! -f "$FILE" ]]; then
  echo "FEHLER: $FILE nicht gefunden." >&2
  exit 2
fi

required_patterns=(
  ".env"
  ".handoff/"
  "*.pem"
  "*.key"
  "*.crt"
  "ocr_storage/"
  "tts_storage/"
  "shared/"
  "backups/"
  "neo4j/"
  "hermes_data/"
  "volumes/"
  "node_modules/"
  "__pycache__/"
  ".git/"
)

missing=()
for pattern in "${required_patterns[@]}"; do
  if ! grep -qF "$pattern" "$FILE"; then
    missing+=("$pattern")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "Pflicht-Ausschlussmuster fehlen in $FILE:"
  printf '  - %s\n' "${missing[@]}"
  exit 1
fi

echo "Alle Pflicht-Ausschlussmuster in $FILE vorhanden."
exit 0
