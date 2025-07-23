#!/bin/sh

# This script dynamically generates the config.js file for the dashboard
# based on the environment (public or private).

# Default service URLs for local/private environment
N8N_LOCAL_URL="http://localhost:5678"
WEBUI_LOCAL_URL="http://localhost:8080"
SEARXNG_LOCAL_URL="http://localhost:8081"
FLOWISE_LOCAL_URL="http://localhost:3001"
SUPABASE_LOCAL_URL="http://localhost:8000"
LANGFUSE_LOCAL_URL="http://localhost:3000"
NEO4J_LOCAL_URL="http://localhost:7474"
QDRANT_LOCAL_URL="http://localhost:6333"
MINIO_LOCAL_URL="http://localhost:9011" # Console port
CRAWL4AI_LOCAL_URL="http://localhost:8082"
PYTHON_NLP_LOCAL_URL="http://localhost:5050"
CLICKHOUSE_URL="http://localhost:8123"

# Environment variables

# Check if running in a public environment
# The IS_PUBLIC_PROFILE variable is passed from the start_services.py script
if [ "${IS_PUBLIC_PROFILE}" = "true" ]; then
    # Public environment: Use domain-based hostnames from environment variables
    # The DOMAIN variable should be set in the .env file
    PROTOCOL="https"
    N8N_URL="${PROTOCOL}://${N8N_HOSTNAME}"
    WEBUI_URL="${PROTOCOL}://${WEBUI_HOSTNAME}"
    SEARXNG_URL="${PROTOCOL}://${SEARXNG_HOSTNAME}"
    FLOWISE_URL="${PROTOCOL}://${FLOWISE_HOSTNAME}"
    SUPABASE_URL="${PROTOCOL}://${SUPABASE_HOSTNAME}"
    LANGFUSE_URL="${PROTOCOL}://${LANGFUSE_HOSTNAME}"
    NEO4J_URL="${PROTOCOL}://${NEO4J_HOSTNAME}"
    QDRANT_URL="" # Typically not exposed publicly
    MINIO_URL=""    # Typically not exposed publicly
    CRAWL4AI_URL="${PROTOCOL}://${CRAWL4AI_HOSTNAME}"
    PYTHON_NLP_URL="${PROTOCOL}://${PYTHON_NLP_HOSTNAME}"
    SUPABASE_FINAL_URL="${PROTOCOL}://${SUPABASE_HOSTNAME}"
    CLICKHOUSE_URL
else
    # Private environment: Use local URLs
    N8N_URL="$N8N_LOCAL_URL"
    WEBUI_URL="$WEBUI_LOCAL_URL"
    SEARXNG_URL="$SEARXNG_LOCAL_URL"
    FLOWISE_URL="$FLOWISE_LOCAL_URL"
    SUPABASE_URL="$SUPABASE_LOCAL_URL"
    LANGFUSE_URL="$LANGFUSE_LOCAL_URL"
    NEO4J_URL="$NEO4J_LOCAL_URL"
    QDRANT_URL="$QDRANT_LOCAL_URL/dashboard"
    MINIO_URL="$MINIO_LOCAL_URL"
    CRAWL4AI_URL="$CRAWL4AI_LOCAL_URL"
    PYTHON_NLP_URL="$PYTHON_NLP_LOCAL_URL/health"
    SUPABASE_FINAL_URL="$SUPABASE_LOCAL_URL"
    CLICKHOUSE_URL="$CLICKHOUSE_URL"
fi

# Generate config.js with the determined URLs
cat <<EOF > /usr/share/nginx/html/config.js
window.APP_CONFIG = {
    n8nHostname: "${N8N_URL}",
    openWebuiHostname: "${WEBUI_URL}",
    searxngHostname: "${SEARXNG_URL}",
    flowiseHostname: "${FLOWISE_URL}",
    supabaseHostname: "${SUPABASE_URL}",
    langfuseHostname: "${LANGFUSE_URL}",
    neo4jHostname: "${NEO4J_URL}",
    qdrantHostname: "${QDRANT_URL}",
    minioHostname: "${MINIO_URL}",
    crawl4aiHostname: "${CRAWL4AI_URL}",
    pythonNlpHostname: "${PYTHON_NLP_URL}",
    clickhouseHostname: "${CLICKHOUSE_URL}",

    // Supabase specific config
    supabaseUrl: "${SUPABASE_FINAL_URL}",
    supabaseAnonKey: "${SUPABASE_ANON_KEY}",
    authEnabled: ${IS_PUBLIC_PROFILE:-false}
};
EOF

echo "Dashboard config.js generated successfully for environment: ${IS_PUBLIC_PROFILE}"

# Start Nginx in the foreground
exec nginx -g "daemon off;"
