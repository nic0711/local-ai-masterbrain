#!/usr/bin/env bash
# Prueft docker-compose.yml auf neue (nicht in der Baseline gelistete) Images
# ohne festen Tag oder mit ":latest". Bestehende, bereits bekannte Funde sind
# in docs/planning/image-pinning-baseline.yml als Bestandsfindings dokumentiert
# und blockieren NICHT - nur neue Funde tun das.
set -euo pipefail

COMPOSE_FILE="docker-compose.yml"
BASELINE_FILE="docs/planning/image-pinning-baseline.yml"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "FEHLER: $COMPOSE_FILE nicht gefunden." >&2
  exit 2
fi
if [[ ! -f "$BASELINE_FILE" ]]; then
  echo "FEHLER: $BASELINE_FILE nicht gefunden." >&2
  exit 2
fi

# Extrahiere image: Werte ohne Tag oder mit :latest.
found_latest_or_untagged=$(grep -E '^\s*image:\s*' "$COMPOSE_FILE" \
  | sed -E 's/^\s*image:\s*"?([^"[:space:]]+)"?.*/\1/' \
  | grep -E ':latest$|^[^:]+$' || true)

new_findings=()
while IFS= read -r image; do
  [[ -z "$image" ]] && continue
  if ! grep -qF "$image" "$BASELINE_FILE"; then
    new_findings+=("$image")
  fi
done <<< "$found_latest_or_untagged"

if [[ ${#new_findings[@]} -gt 0 ]]; then
  echo "Neue, nicht in der Baseline dokumentierte latest/ungepinnte Images gefunden:"
  printf '  - %s\n' "${new_findings[@]}"
  echo "Bitte in $BASELINE_FILE aufnehmen (mit Vermerk/Owner) oder Image-Version pinnen."
  exit 1
fi

echo "Keine neuen latest/ungepinnten Images ausserhalb der Baseline gefunden."
exit 0
