#!/usr/bin/env bash
#
# Wendet die projekteigenen Supabase/Postgres-Migrationen unter
# infra/supabase/migrations/ auf den laufenden `db`-Service an.
#
# Ersetzt bewusst KEINEN docker-entrypoint-initdb.d-Hook: der griffe nur bei
# einem brandneuen, leeren Volume und wuerde eine bereits bestehende
# Installation nie erreichen. Stattdessen manueller Aufruf durch den
# Betreiber, siehe docs/29_supabase_migrations.md.
#
# Usage (aus dem Repo-Root oder von ueberall, das Skript findet den
# Repo-Root selbst):
#   infra/supabase/apply-migrations.sh apply
#   infra/supabase/apply-migrations.sh baseline 01_shared_functions.sql 02_rag_schema.sql ...
#   infra/supabase/apply-migrations.sh status
#
# Voraussetzung: `docker compose up -d db` laeuft bereits.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations"
TRACKING_TABLE="public._project_migrations"

usage() {
    echo "Usage: $0 apply | baseline <datei.sql> [<datei.sql> ...] | status" >&2
    exit 1
}

checksum_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

# Fuehrt psql gegen den db-Service aus. Liest das SQL-Skript von stdin.
# -1 (--single-transaction): das gesamte Stdin-Skript laeuft in EINER
# Transaktion - schlaegt ein Statement fehl (ON_ERROR_STOP=1 macht Fehler
# fatal statt nur eine Fehlermeldung zu drucken), wird alles zurueckgerollt.
run_psql() {
    (cd "$REPO_ROOT" && docker compose exec -T db psql -U postgres -v ON_ERROR_STOP=1 -1)
}

# Wie run_psql, aber ohne -1 (fuer reine SELECT-Statusabfragen, bei denen
# eine implizite Transaktion irrelevant ist).
run_psql_query() {
    (cd "$REPO_ROOT" && docker compose exec -T db psql -U postgres -v ON_ERROR_STOP=1 -t -A -F'|')
}

ensure_tracking_table() {
    echo "CREATE TABLE IF NOT EXISTS $TRACKING_TABLE (
        version TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        checksum TEXT NOT NULL,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        baseline BOOLEAN NOT NULL DEFAULT FALSE
    );" | run_psql
}

# Zerlegt einen Dateinamen wie '02_rag_schema.sql' in Version ('02') und
# Name ('rag_schema').
parse_filename() {
    local base
    base="$(basename "$1" .sql)"
    if [[ ! "$base" =~ ^([0-9]+)_(.+)$ ]]; then
        echo "Fehler: Migrationsdateiname '$1' folgt nicht dem Muster NN_name.sql" >&2
        exit 1
    fi
    echo "${BASH_REMATCH[1]}|${BASH_REMATCH[2]}"
}

tracked_checksum() {
    local version="$1"
    run_psql_query <<SQL
SELECT checksum FROM $TRACKING_TABLE WHERE version = '$version';
SQL
}

cmd_apply() {
    ensure_tracking_table
    local file version name parsed existing checksum
    for file in "$MIGRATIONS_DIR"/*.sql; do
        [ -e "$file" ] || continue
        parsed="$(parse_filename "$file")"
        version="${parsed%%|*}"
        name="${parsed#*|}"
        checksum="$(checksum_of "$file")"
        existing="$(tracked_checksum "$version" | tr -d '[:space:]')"

        if [ -z "$existing" ]; then
            echo "==> $version ($name): wende an ..."
            {
                cat "$file"
                echo
                echo "INSERT INTO $TRACKING_TABLE (version, name, checksum, baseline) VALUES ('$version', '$name', '$checksum', FALSE);"
            } | run_psql
            echo "    angewendet."
        elif [ "$existing" = "$checksum" ]; then
            echo "==> $version ($name): bereits angewendet (Checksumme identisch), uebersprungen."
        else
            echo "FEHLER: $version ($name) ist bereits mit einer ANDEREN Checksumme getrackt." >&2
            echo "        Eine einmal angewendete Migration wird nie im Nachhinein veraendert." >&2
            echo "        Aenderungen brauchen eine neue Migrationsdatei mit neuer Versionsnummer." >&2
            exit 1
        fi
    done
}

cmd_baseline() {
    if [ "$#" -eq 0 ]; then
        echo "Fehler: baseline benoetigt mindestens eine Datei (explizite Liste, kein 'alle')." >&2
        usage
    fi
    ensure_tracking_table
    local arg file version name parsed existing checksum
    for arg in "$@"; do
        file="$MIGRATIONS_DIR/$(basename "$arg")"
        if [ ! -e "$file" ]; then
            echo "Fehler: $file existiert nicht." >&2
            exit 1
        fi
        parsed="$(parse_filename "$file")"
        version="${parsed%%|*}"
        name="${parsed#*|}"
        checksum="$(checksum_of "$file")"
        existing="$(tracked_checksum "$version" | tr -d '[:space:]')"

        if [ -n "$existing" ]; then
            echo "FEHLER: $version ($name) ist bereits getrackt (baseline oder angewendet) - kann nicht erneut baselined werden." >&2
            exit 1
        fi

        echo "==> $version ($name): als Baseline uebernommen (NICHT ausgefuehrt, nur getrackt)."
        echo "INSERT INTO $TRACKING_TABLE (version, name, checksum, baseline) VALUES ('$version', '$name', '$checksum', TRUE);" | run_psql
    done
}

cmd_status() {
    ensure_tracking_table
    echo "SELECT version, name, checksum, applied_at, baseline FROM $TRACKING_TABLE ORDER BY version;" | \
        (cd "$REPO_ROOT" && docker compose exec -T db psql -U postgres -v ON_ERROR_STOP=1)
}

case "${1:-}" in
    apply)
        cmd_apply
        ;;
    baseline)
        shift
        cmd_baseline "$@"
        ;;
    status)
        cmd_status
        ;;
    *)
        usage
        ;;
esac
