# ADR 0008: Getrennte Container und zentrale Sicherheitsstandards

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

Custom Services werden nicht zu einem Universal-Container zusammengelegt.

Es werden wenige Base-Image-Familien gepflegt. Alle Custom Images müssen
non-root, reproduzierbar, gescannt, signiert, ressourcenbegrenzt und getestet
sein.

Trivy ist der zentrale Scanner. Critical und High blockieren Releases.

## Folgen

Updates bleiben servicebezogen. Berechtigungen, Ausfälle und Ressourcen werden
nicht unnötig gekoppelt.
