# 9. FAQ

### Wie lege ich den ersten Benutzer an?

Ein Signup-Formular gibt es nicht – der erste Benutzer wird per API angelegt:

```bash
ANON_KEY=$(grep "^ANON_KEY=" .env | cut -d= -f2 | tr -d ' ')

curl -s -X POST "https://supabase.brain.local/auth/v1/signup" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"deine@email.de","password":"sicherespasswort"}'
```

Danach `DISABLE_SIGNUP=true` in `.env` setzen.

---

### Wie setze ich ein vergessenes Passwort zurück?

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

---

### Wie richte ich 2FA ein?

1. Login unter `https://brain.local`
2. **„2FA einrichten"** im Header klicken
3. QR-Code mit Authenticator-App scannen (Google Authenticator, Authy etc.)
4. 6-stelligen Code eingeben und bestätigen
5. Ab sofort wird bei jedem Login der Code abgefragt

---

### Was bedeuten die verschiedenen `--profile`-Optionen?

| Profil | Beschreibung |
|---|---|
| `none` | Kein Ollama in Docker – Ollama läuft lokal (empfohlen für Mac) |
| `cpu` | Ollama läuft in Docker auf CPU |
| `gpu-nvidia` | Ollama in Docker mit Nvidia-GPU |
| `gpu-amd` | Ollama in Docker mit AMD-GPU (Linux) |

`--environment public` ist der Standard und muss nicht angegeben werden.

---

### Wie füge ich ein neues Ollama-Modell hinzu?

```bash
# Ollama lokal (Mac):
ollama pull llama3.2

# Ollama in Docker:
docker exec ollama ollama pull llama3.2
```

---

### Mindest-Systemanforderungen?

- **CPU-only:** 4+ Kerne, 16 GB RAM, SSD
- **GPU:** NVIDIA mit ≥8 GB VRAM (RTX 3060 oder besser)
- **Speicherplatz:** ≥50 GB für OS, Docker und Modelle

---

### Kann ich Services deaktivieren die ich nicht brauche?

Ja – in `docker-compose.yml` den entsprechenden Service-Block auskommentieren, dann `python3 start_services.py --profile <profil>` neu ausführen.

---

### Kann ich externe AI-Provider (OpenAI, Anthropic) nutzen?

Ja. In n8n und Flowise können API-Keys als Credentials hinterlegt werden. Open WebUI kann auf beliebige OpenAI-kompatible Endpunkte konfiguriert werden.

---

### Wie update ich auf die neueste Version?

```bash
docker compose -p localai down
git pull origin main
docker compose -p localai -f docker-compose.yml pull
python3 start_services.py --profile <dein-profil>
```

---

### Funktioniert das auf Apple Silicon (M1/M2/M3)?

Ja. Docker auf macOS unterstützt kein GPU-Passthrough, daher ist `--profile none` mit lokal installiertem Ollama die empfohlene Option für beste Performance.

---

### Wie exponiere ich Services im lokalen Netzwerk (ohne Auth)?

Im `private`-Modus (`--environment private`) in `docker-compose.override.private.yml` die Port-Bindung anpassen:

```yaml
services:
  n8n:
    ports:
      - "0.0.0.0:5678:5678"   # statt 127.0.0.1
```

> Für den Produktivbetrieb lieber `--environment public` (Standard) nutzen – dann läuft alles über Caddy mit Auth.
