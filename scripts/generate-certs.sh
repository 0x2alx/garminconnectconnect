#!/bin/bash
set -euo pipefail

# Generates self-signed TLS certificates for the garmin-connect reverse proxy.
# Certificates are valid for 10 years with the host IP as CN/SAN.
# Usage: sudo ./generate-certs.sh [HOST_IP]

SSL_DIR="/etc/nginx/ssl"
HOST_IP="${1:?Usage: $0 <HOST_IP>  (e.g., $0 192.168.1.100)}"

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root (writes to /etc/nginx/ssl)."
    exit 1
fi

mkdir -p "$SSL_DIR"

openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout "${SSL_DIR}/garmin-connect.key" \
    -out "${SSL_DIR}/garmin-connect.crt" \
    -subj "/CN=${HOST_IP}" \
    -addext "subjectAltName=IP:${HOST_IP}"

chmod 600 "${SSL_DIR}/garmin-connect.key"
chmod 644 "${SSL_DIR}/garmin-connect.crt"

echo "Generated TLS certificates in ${SSL_DIR}:"
echo "  Certificate: ${SSL_DIR}/garmin-connect.crt"
echo "  Private key: ${SSL_DIR}/garmin-connect.key"
