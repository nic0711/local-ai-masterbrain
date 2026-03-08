# 7. Troubleshooting

Erste Maßnahme bei jedem Problem: **Logs prüfen**

```bash
docker logs <container-name>          # z.B. docker logs n8n
docker logs caddy 2>&1 | tail -30
docker logs auth-gateway
```

---

## Auth & Login

**Problem: Login-Formular lädt, aber Anmeldung schlägt fehl ("Invalid login credentials")**

- Passwort zurücksetzen:
  ```bash
  USER_ID=$(docker exec supabase-db psql -U postgres -d postgres -tAc \
    "SELECT id FROM auth.users WHERE email='user@example.com';" | tr -d ' ')
  SERVICE_KEY=$(grep "^SERVICE_ROLE_KEY=" .env | cut -d= -f2 | tr -d ' ')
  curl -s -X PUT "http://localhost:8000/auth/v1/admin/users/$USER_ID" \
    -H "apikey: $SERVICE_KEY" \
    -H "Authorization: Bearer $SERVICE_KEY" \
    -H "Content-Type: application/json" \
    -d '{"password":"neuespasswort"}'
  ```

**Problem: Seite bleibt weiß / leere Seite nach Login**

- `https://supabase.brain.local` im Browser öffnen und das Self-Signed-Zertifikat akzeptieren
- Browser-Konsole (F12) auf Fehler prüfen
- `docker logs dashboard-ui` prüfen

**Problem: Redirect-Loop (immer wieder zu login.html)**

- Cookie wird nicht gesetzt: Browser-DevTools → Application → Cookies → prüfen ob `sb-access-token` auf `.brain.local` vorhanden
- `docker logs auth-gateway` prüfen – auth-gateway muss laufen
- Stack mit korrekten Compose-Dateien gestartet?
  ```bash
  python3 start_services.py --profile none   # startet auth-gateway automatisch
  ```

**Problem: n8n/Flowise etc. zeigt 502**

- auth-gateway läuft nicht:
  ```bash
  docker ps | grep auth-gateway
  # Falls nicht: Stack komplett neu starten
  python3 start_services.py --profile none
  ```

**Problem: `auth-gateway` zeigt "invalid number of segments"**

- Cookie hat falsche oder fehlende Domain – Cookie wird nicht cross-subdomain gesendet
- Prüfen: `DOMAIN=brain.local` in `.env` (nicht `DOMAIN=local`)
- Dashboard-Container neu starten: `docker compose -p localai restart dashboard`

---

## Netzwerk & Docker

**Problem: Port bereits belegt**

```bash
sudo lsof -i :<port>   # z.B. sudo lsof -i :443
```

Konfliktierenden Prozess stoppen oder Port in `docker-compose.override.private.yml` ändern.

**Problem: Container starten nach Neustart nicht**

```bash
sudo systemctl enable docker
docker compose -p localai up -d
```

**Problem: `PG_META_CRYPTO_KEY` Warnung beim Start**

Harmlose Warnung von Supabase Meta – kein Handlungsbedarf.

---

## Supabase

**Problem: Supabase-Container starten nicht nach Passwort-Änderung**

1. Stack stoppen: `docker compose -p localai down`
2. DB-Volume löschen (⚠️ löscht alle Daten!): `sudo rm -rf ./supabase/docker/volumes/db/data`
3. Stack neu starten

**Problem: `supabase-pooler` im Restart-Loop**

Bekanntes Supabase-Problem: [GitHub Issue #30210](https://github.com/supabase/supabase/issues/30210#issuecomment-2456955578)

**Problem: Services können nicht auf Supabase-DB zugreifen**

- `@`-Zeichen im `POSTGRES_PASSWORD` vermeiden
- Host in den Credentials muss `db` sein (Docker-Servicename), nicht `localhost`

---

## Ollama & Modelle

**Problem: Ollama-Container crasht oder Modelle laden nicht**

```bash
df -h           # Speicherplatz prüfen
docker logs ollama
docker exec ollama ollama list
```

**Problem: Ollama nicht erreichbar von n8n aus**

- Mac (Ollama lokal): `OLLAMA_HOST=http://host.docker.internal:11434` in `.env`
- Server (Ollama in Docker): `OLLAMA_HOST=http://ollama:11434` in `.env`

---

## Python NLP Service

**Problem: OCR schlägt fehl ("Ollama nicht erreichbar")**

```bash
docker exec python-nlp-service env | grep OLLAMA
ollama list | grep glm-ocr   # Modell vorhanden?
ollama pull glm-ocr
```

**Problem: `/health` gibt `503 starting` zurück**

SpaCy-Modelle laden beim ersten Start 30–60s. Warten und `docker logs python-nlp-service` beobachten.

---

## Migration / Upstream-Update

**Problem: `LANGFUSE_ENCRYPTION_KEY` fehlt nach Update**

In `.env` umbenennen: `LANGFUSE_ENCRYPTION_KEY` → `ENCRYPTION_KEY`

**Problem: Workflows nach Update verschwunden**

n8n-Import-Service wurde entfernt. Manuell importieren:
n8n → **Settings → Import workflow** → JSON aus `n8n/backup/workflows/`

**Problem: `storage-api` startet nicht**

Fehlende Variablen aus `.env.example` kopieren:
`GLOBAL_S3_BUCKET=stub`, `REGION=stub`, `STORAGE_TENANT_ID=stub`
