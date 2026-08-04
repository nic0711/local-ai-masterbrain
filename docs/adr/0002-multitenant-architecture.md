# ADR 0002: Technisch mandantenfähige Architektur

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

Alle neuen Intune-Komponenten werden technisch mandantenfähig. Im MVP wird ein
produktiver Tenant betrieben.

Jede relevante Business-Tabelle enthält `tenant_id`. Autorisierung, Jobs,
Graph-Credentials, Findings, Konfiguration und Benachrichtigungen werden
tenantbezogen getrennt.

## Folgen

Ein späterer zweiter Tenant benötigt keine grundlegende Neustrukturierung.
Ein Tenant-Switcher ist nicht Teil des MVP.
