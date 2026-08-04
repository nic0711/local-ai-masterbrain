# ADR 0004: FastAPI, PostgreSQL-Jobtabelle und separater Worker

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

FastAPI stellt die API bereit. Lange Arbeiten laufen über eine PostgreSQL-
Jobtabelle und einen separaten Worker.

API und Worker verwenden dasselbe Image mit unterschiedlichen Startbefehlen.
Der Worker startet bedarfsgesteuert und beendet sich nach standardmäßig
600 Sekunden Inaktivität.

## Folgen

Keine langen Graph-Synchronisationen in HTTP-Requests. Reservation, Heartbeat,
Retry, Reclaim und Tenant-Sperren müssen transaktional umgesetzt werden.
