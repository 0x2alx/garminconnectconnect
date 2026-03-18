#!/bin/bash
set -euo pipefail

# Generates a .env file with random credentials for all services.
# Preserves GARMIN_EMAIL and GARMIN_PASSWORD if they exist in the current .env.

ENV_FILE="${1:-.env}"

# Generate random credentials
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)
MONGO_ROOT_USER="garmin"
MONGO_ROOT_PASSWORD=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)
GRAFANA_PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 24)
MCP_API_KEY=$(openssl rand -hex 24)

# Preserve existing Garmin credentials if present
GARMIN_EMAIL="your@email.com"
GARMIN_PASSWORD="your_password"
if [ -f "$ENV_FILE" ]; then
    existing_email=$(grep -E '^GARMIN_EMAIL=' "$ENV_FILE" | cut -d= -f2- || true)
    existing_password=$(grep -E '^GARMIN_PASSWORD=' "$ENV_FILE" | cut -d= -f2- || true)
    [ -n "$existing_email" ] && GARMIN_EMAIL="$existing_email"
    [ -n "$existing_password" ] && GARMIN_PASSWORD="$existing_password"
fi

cat > "$ENV_FILE" <<EOF
# Garmin Connect Credentials
GARMIN_EMAIL=${GARMIN_EMAIL}
GARMIN_PASSWORD=${GARMIN_PASSWORD}

# PostgreSQL / TimescaleDB
POSTGRES_HOST=timescaledb
POSTGRES_PORT=5432
POSTGRES_DB=garmin
POSTGRES_USER=garmin
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# MongoDB
MONGO_HOST=mongodb
MONGO_PORT=27017
MONGO_DB=garmin_raw
MONGO_ROOT_USER=${MONGO_ROOT_USER}
MONGO_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}

# Polling
POLL_INTERVAL_MINUTES=10
BACKFILL_DAYS=30

# Grafana
GRAFANA_PASSWORD=${GRAFANA_PASSWORD}
GRAFANA_PORT=3001

# MCP
MCP_TRANSPORT=sse
MCP_API_KEY=${MCP_API_KEY}
EOF

echo "Generated credentials in ${ENV_FILE}"
echo "  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}"
echo "  MONGO_ROOT_PASSWORD: ${MONGO_ROOT_PASSWORD}"
echo "  GRAFANA_PASSWORD: ${GRAFANA_PASSWORD}"
echo "  MCP_API_KEY: ${MCP_API_KEY}"
