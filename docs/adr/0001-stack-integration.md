# ADR 0001: Integration in den bestehenden Masterbrain-Stack

- Status: Akzeptiert
- Datum: 2026-08-03

## Kontext

Der Intune Policy Hub soll bestehende Authentifizierung, Supabase, n8n,
Monitoring, Caddy und Service-Control verwenden.

## Entscheidung

Der Hub wird in `local-ai-masterbrain` integriert. Es entsteht kein separater
Parallel-Stack. Der Betrieb bleibt Docker Compose auf einem Host.

## Folgen

- gemeinsame Governance und Releases
- keine doppelte Infrastruktur
- Stack-Basis muss vor der Intune-Entwicklung gehärtet werden
- Kubernetes ist nicht Bestandteil der aktuellen Architektur
