# 2. Configuration (.env)

Make sure to copy `.env.example` to `.env` and fill in all required values.

### Required variables

```
############
# N8N Configuration
############
N8N_ENCRYPTION_KEY=
N8N_USER_MANAGEMENT_JWT_SECRET=

############
# Supabase Secrets
############
POSTGRES_PASSWORD=
JWT_SECRET=
ANON_KEY=
SERVICE_ROLE_KEY=
DASHBOARD_USERNAME=
DASHBOARD_PASSWORD=
POOLER_TENANT_ID=

############
# Neo4j Secrets
############   
NEO4J_AUTH=

############
# Langfuse credentials
############

CLICKHOUSE_PASSWORD=
MINIO_ROOT_PASSWORD=
LANGFUSE_SALT=
NEXTAUTH_SECRET=
ENCRYPTION_KEY=  

############
# Caddy Config
############

N8N_HOSTNAME=n8n.yourdomain.com
WEBUI_HOSTNAME=:openwebui.yourdomain.com
FLOWISE_HOSTNAME=:flowise.yourdomain.com
SUPABASE_HOSTNAME=:supabase.yourdomain.com
OLLAMA_HOSTNAME=:ollama.yourdomain.com
SEARXNG_HOSTNAME=searxng.yourdomain.com
NEO4J_HOSTNAME=neo4j.yourdomain.com
LETSENCRYPT_EMAIL=your-email-address

``
## Important

Make sure to generate secure random values for all secrets. Never use the example values in production.

For production deployment, set your domain names for each service:


