# ADR 0005: Authentifizierung, Graph-Apps und Rollen

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

Browserzugriffe verwenden Supabase JWTs, die FastAPI selbst vollständig prüft.
n8n verwendet kurzlebige asymmetrisch signierte Service-JWTs.

Für Graph werden getrennte Entra-Apps verwendet:

- Intune Policy Reader
- Directory Reader

Authentifizierung erfolgt mit Zertifikaten, nicht mit Client Secrets.

Rollen:

- Viewer
- Analyst
- Policy Owner
- Hub Administrator
- Security Approver
- Documentation Owner

## Folgen

Graph-Berechtigungen und private Schlüssel bleiben getrennt. Proxy-Header sind
kein alleiniger Identitätsnachweis.
