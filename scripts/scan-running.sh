#!/usr/bin/env bash
# CVE-Monitoring der LAUFENDEN Container: scannt jedes aktuell genutzte Image
# mit Trivy (gleicher gepinnter Digest wie in .github/workflows/ci.yml) und
# listet behebbare CRITICAL/HIGH-Funde mit Fix-Version.
#
# Aufruf:  scripts/scan-running.sh [--all] [--notify]
#   --all     alle Images aus docker-compose.yml + Supabase statt nur laufende
#   --notify  macOS-Benachrichtigung bei Funden (z.B. fuer Cron/launchd)
# Exit-Code: 0 = nichts Behebbares, 1 = behebbare Funde, 2 = Fehler.
#
# Hinweis: scannt per Docker-Socket (read-only) genau die lokal vorhandenen
# Images, also das, was wirklich laeuft - nicht, was die Registry aktuell hat.
set -euo pipefail

TRIVY_IMAGE="aquasec/trivy@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c"
SEVERITY="CRITICAL,HIGH"

all=false
notify=false
for arg in "$@"; do
  case "$arg" in
    --all) all=true ;;
    --notify) notify=true ;;
    *) echo "Unbekannte Option: $arg" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo "FEHLER: docker nicht gefunden." >&2; exit 2; }

if $all; then
  images=$(docker compose -p localai --profile auth --profile optional config --images 2>/dev/null | sort -u)
else
  images=$(docker ps --format '{{.Image}}' | sort -u)
fi
[[ -n "$images" ]] || { echo "FEHLER: keine Images gefunden." >&2; exit 2; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
chmod 777 "$tmp"

total_fixable=0
summary=()
while IFS= read -r image; do
  [[ -z "$image" ]] && continue
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    echo "uebersprungen (lokal nicht vorhanden): $image"
    continue
  fi
  safe=${image//[^A-Za-z0-9._-]/_}
  echo "Scanne $image ..."
  docker run --rm \
    --cap-drop=ALL --security-opt no-new-privileges:true \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v trivy-cache:/root/.cache \
    -v "$tmp:/out" \
    "$TRIVY_IMAGE" \
    image --quiet --format json --output "/out/$safe.json" \
    --severity "$SEVERITY" --ignore-unfixed "$image" >/dev/null
  count=$(python3 - "$tmp/$safe.json" "$image" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
rows = []
for res in report.get("Results") or []:
    for v in res.get("Vulnerabilities") or []:
        rows.append((v["Severity"], v["VulnerabilityID"], v["PkgName"],
                     v["InstalledVersion"], v.get("FixedVersion", "")))
for sev, cve, pkg, inst, fix in sorted(set(rows)):
    print(f"    {sev:8} {cve}  {pkg} {inst} -> {fix}", file=sys.stderr)
print(len(set(rows)))
PY
  )
  summary+=("$count|$image")
  total_fixable=$((total_fixable + count))
done <<< "$images"

echo
echo "=== Zusammenfassung (behebbare $SEVERITY) ==="
printf '%s\n' "${summary[@]}" | sort -t'|' -k1,1nr | awk -F'|' '{printf "%5d  %s\n", $1, $2}'
echo "Gesamt: $total_fixable"

if (( total_fixable > 0 )); then
  $notify && osascript -e "display notification \"$total_fixable behebbare CVEs in Containern - scripts/scan-running.sh\" with title \"CVE-Monitoring\"" || true
  exit 1
fi
