#!/usr/bin/env bash
# Idempotent: ensure collectibles_vault exists and apply db/schema.sql (safe on existing data).
set -euo pipefail

host="${PGHOST:-db}"
port="${PGPORT:-5432}"
user="${PGUSER:-postgres}"
dbname="${POSTGRES_TARGET_DB:-collectibles_vault}"

export PGPASSWORD="${PGPASSWORD:-postgres}"

until pg_isready -h "$host" -p "$port" -U "$user" >/dev/null 2>&1; do
  sleep 1
done

exists="$(psql -h "$host" -p "$port" -U "$user" -d postgres -Atc \
  "SELECT 1 FROM pg_database WHERE datname = '${dbname}'" || true)"
if [ -z "$exists" ]; then
  psql -h "$host" -p "$port" -U "$user" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE \"${dbname}\";"
fi

psql -h "$host" -p "$port" -U "$user" -d "$dbname" -v ON_ERROR_STOP=1 -f /schema.sql
