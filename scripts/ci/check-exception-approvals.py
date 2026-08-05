#!/usr/bin/env python3
"""Prueft echte GitHub-PR-Reviews gegen den aktuellen head_sha, um
Security-Ausnahmen (docs/planning/security-exceptions/*.yml) freizugeben.

Ersetzt das fruehere Modell mit einem `github_approval_ref`-Feld in der
Ausnahmedatei selbst: das erzeugte einen Deadlock, weil das Eintragen der
Referenz per Commit unter aktiver Branch-Protection ("Dismiss stale
approvals on new commits") die soeben erteilte Freigabe wieder ungueltig
gemacht haette. Diese Pruefung liest stattdessen live die PR-Reviews via
GitHub REST API - nichts wird in die Ausnahmedatei zurueckgeschrieben.

Regeln:
  - Ausnahme mit severity=high braucht 1 genehmigenden Review.
  - Ausnahme mit severity=critical braucht 2 genehmigende Reviews.
  - Ein Review zaehlt nur, wenn state=APPROVED, der Review sich auf den
    AKTUELLEN head_sha bezieht (commit_id == head_sha - defensiver
    Zusatzschutz, unabhaengig davon ob Branch-Protection-Stale-Dismissal
    serverseitig aktiv ist), und der Reviewer weder der PR-Autor noch die in
    requested_by genannte Person ist.

Ausgabe: approved-exceptions.json (Liste der `id`-Werte freigegebener
Ausnahmen) im aktuellen Verzeichnis, fuer nachgelagerte Jobs (trivy-image).

Ohne PR-Kontext (z.B. push-Event nach Merge, workflow_dispatch) gibt es keine
PR-Reviews zu pruefen - das Skript schreibt dann eine leere Freigabeliste und
beendet sich mit Exit 0 (informativ, kein Fehler).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import urllib.error
import urllib.request

try:
    import yaml
except ImportError:
    print("FEHLER: PyYAML ist nicht installiert (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

REQUIRED_APPROVALS = {"critical": 2, "high": 1}
EXCEPTIONS_GLOB = "docs/planning/security-exceptions/*.yml"


def _strip_at(login: str) -> str:
    return login.lstrip("@").strip().lower()


def fetch_reviews(repo: str, pr_number: int, token: str) -> list[dict]:
    """Liest alle Reviews eines PR (mit Pagination) via GitHub REST API."""
    reviews: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews?per_page=100&page={page}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            print(f"FEHLER: GitHub-API-Aufruf fehlgeschlagen ({e.code}): {e.reason}", file=sys.stderr)
            sys.exit(2)
        if not batch:
            break
        reviews.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return reviews


def fetch_pr_author(repo: str, pr_number: int, token: str) -> str:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"FEHLER: GitHub-API-Aufruf fehlgeschlagen ({e.code}): {e.reason}", file=sys.stderr)
        sys.exit(2)
    return data.get("user", {}).get("login", "")


def qualifying_approvers(
    reviews: list[dict], head_sha: str, pr_author: str, requested_by: str
) -> set[str]:
    excluded = {_strip_at(pr_author), _strip_at(requested_by)}
    # Nur die JEWEILS LETZTE Review-Entscheidung pro Reviewer zaehlt (GitHub
    # erlaubt mehrere Reviews derselben Person, z.B. request-changes gefolgt
    # von approve, oder umgekehrt).
    latest_by_user: dict[str, dict] = {}
    for r in reviews:
        login = r.get("user", {}).get("login", "")
        if not login:
            continue
        submitted_at = r.get("submitted_at", "")
        prev = latest_by_user.get(login)
        if prev is None or submitted_at >= prev.get("submitted_at", ""):
            latest_by_user[login] = r

    qualifying: set[str] = set()
    for login, review in latest_by_user.items():
        if review.get("state") != "APPROVED":
            continue
        if review.get("commit_id") != head_sha:
            continue
        if _strip_at(login) in excluded:
            continue
        qualifying.add(login)
    return qualifying


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--pr-number", type=int, default=int(os.environ.get("PR_NUMBER") or 0) or None)
    parser.add_argument("--head-sha", default=os.environ.get("HEAD_SHA", ""))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument("--output", default="approved-exceptions.json")
    args = parser.parse_args()

    exception_files = sorted(glob.glob(EXCEPTIONS_GLOB))
    exceptions = []
    for path in exception_files:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        data["_source_file"] = path
        exceptions.append(data)

    if not exceptions:
        print(f"Keine Ausnahmedateien unter {EXCEPTIONS_GLOB} - nichts zu pruefen.")
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump([], fh)
        return 0

    if not args.pr_number or not args.head_sha:
        print(
            "Kein PR-Kontext (z.B. push-Event nach Merge oder workflow_dispatch) - "
            "PR-Reviews koennen nicht geprueft werden. Keine Ausnahme gilt als freigegeben."
        )
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump([], fh)
        return 0

    if not args.token:
        print("FEHLER: kein GITHUB_TOKEN uebergeben.", file=sys.stderr)
        return 2

    pr_author = fetch_pr_author(args.repo, args.pr_number, args.token)
    reviews = fetch_reviews(args.repo, args.pr_number, args.token)

    approved_ids: list[str] = []
    print(f"PR #{args.pr_number} ({args.repo}), head_sha={args.head_sha}, Autor={pr_author}")
    for exc in exceptions:
        severity = str(exc.get("severity", "")).lower()
        required = REQUIRED_APPROVALS.get(severity)
        exc_id = exc.get("id", exc["_source_file"])
        requested_by = exc.get("requested_by", "")

        if required is None:
            print(f"  - {exc_id}: ungueltige severity '{exc.get('severity')}' - uebersprungen")
            continue

        qualifying = qualifying_approvers(reviews, args.head_sha, pr_author, requested_by)
        status = "FREIGEGEBEN" if len(qualifying) >= required else "NICHT freigegeben"
        print(
            f"  - {exc_id} (severity={severity}, benoetigt={required}): "
            f"{len(qualifying)} qualifizierende Freigabe(n) {sorted(qualifying)} -> {status}"
        )
        if len(qualifying) < required:
            print(
                "    Hinweis: PR-Autor und requested_by zaehlen nicht. Reviews muessen sich "
                "auf den aktuellen head_sha beziehen (kein veralteter Review)."
            )
        if len(qualifying) >= required:
            approved_ids.append(exc_id)

    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(approved_ids, fh, indent=2)
    print(f"\n{len(approved_ids)} von {len(exceptions)} Ausnahme(n) freigegeben -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
