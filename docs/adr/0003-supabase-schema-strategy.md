# ADR 0003: Eigene Intune-Schemas in Supabase/PostgreSQL

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

Die bestehende Datenbank bleibt erhalten. Intune-Daten werden in getrennten
Schemas gespeichert:

- `intune_raw`
- `intune_core`
- `intune_analysis`
- `intune_api`

Der Browser greift nicht direkt auf Raw- oder Core-Tabellen zu.

## Folgen

Die Daten bleiben logisch getrennt, ohne eine zweite Datenbankplattform
betreiben zu müssen. Migrationen werden versioniert und separat ausgeführt.
