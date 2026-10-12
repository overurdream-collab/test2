#!/usr/bin/env bash
set -euo pipefail

: "${MCIAS_DATABASE_URL:?MCIAS_DATABASE_URL is required (setup account)}"
: "${MCIAS_RUNTIME_USER:=laptop_runtime}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
SQL_FILE="${SCRIPT_DIR}/setup_rbac_permissions.sql"

if [[ ! -f "${SQL_FILE}" ]]; then
    echo "ERROR: SQL file not found: ${SQL_FILE}" >&2
    exit 1
fi
if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: psql is required; install the PostgreSQL client." >&2
    exit 1
fi

case "${MCIAS_DATABASE_URL}" in
    postgresql+psycopg://*)
        connection_url="postgresql://${MCIAS_DATABASE_URL#postgresql+psycopg://}"
        ;;
    postgresql://*|postgres://*)
        connection_url="${MCIAS_DATABASE_URL}"
        ;;
    *)
        echo "ERROR: use a postgresql://, postgres:// or postgresql+psycopg:// URL." >&2
        exit 1
        ;;
esac

printf 'Runtime user: %q\n' "${MCIAS_RUNTIME_USER}"
echo "Applying RBAC permission setup..."
# Do not print the connection URL.
# -X ignores local psqlrc files; -w fails instead of prompting for a password.
psql --dbname="${connection_url}" -X -w \
    --set=ON_ERROR_STOP=1 \
    --set="runtime_user=${MCIAS_RUNTIME_USER}" \
    --file="${SQL_FILE}"

echo "Done. Check the GRANT result or missing-role warning above."
