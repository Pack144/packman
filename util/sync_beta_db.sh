#!/usr/bin/env bash
# sync_beta_db.sh — Wipe the beta PostgreSQL database and replace it with a
# fresh copy of the production database.
#
# Only reads the beta deployment's DATABASE_URL. The production database name
# is derived by stripping "-beta" from the beta database name, and the same
# connection credentials are reused — the beta database user has read-only
# access to the production database, which is all pg_dump needs.

set -euo pipefail

TARGET_DIR="$HOME/apps/django-beta"
TARGET_ENV="$TARGET_DIR/packman/.env"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo "  $*"; }
success() { echo "✅ $*"; }
warn()    { echo "⚠️  $*"; }
error()   { echo "❌ $*" >&2; exit 1; }
header()  { echo; echo "══════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════"; }

require_cmd() {
    command -v "$1" &>/dev/null || error "Required command '$1' not found on PATH"
}

require_cmd pg_dump
require_cmd pg_restore
require_cmd psql
require_cmd python3

header "Sync beta database from production"

[[ -f "$TARGET_ENV" ]] || error "No .env file found at $TARGET_ENV"

DATABASE_URL_LINE="$(grep -E '^DATABASE_URL=' "$TARGET_ENV" | tail -n1 || true)"
[[ -n "$DATABASE_URL_LINE" ]] || error "DATABASE_URL not set in $TARGET_ENV"
DATABASE_URL_LINE="${DATABASE_URL_LINE#DATABASE_URL=}"
# Strip a single layer of surrounding quotes, if present.
DATABASE_URL_LINE="${DATABASE_URL_LINE%\"}"; DATABASE_URL_LINE="${DATABASE_URL_LINE#\"}"
DATABASE_URL_LINE="${DATABASE_URL_LINE%\'}"; DATABASE_URL_LINE="${DATABASE_URL_LINE#\'}"

# Parse the psql:// URL into "host|port|user|password|dbname".
PARSED="$(python3 - "$DATABASE_URL_LINE" <<'PYEOF'
import sys
from urllib.parse import urlsplit, unquote

url = sys.argv[1]
parts = urlsplit(url)
if parts.scheme not in ("psql", "postgres", "postgresql"):
    sys.exit(f"Not a PostgreSQL DATABASE_URL (scheme={parts.scheme!r})")

host = parts.hostname or "localhost"
port = parts.port or 5432
user = unquote(parts.username) if parts.username else ""
password = unquote(parts.password) if parts.password else ""
dbname = parts.path.lstrip("/")
print(f"{host}|{port}|{user}|{password}|{dbname}")
PYEOF
)"

IFS='|' read -r PGHOST PGPORT PGUSER PGPASSWORD TGT_DB <<<"$PARSED"

[[ "$TGT_DB" == *-beta ]] || error "Beta database name '$TGT_DB' doesn't end with '-beta' — refusing to run, this doesn't look like the beta database"
[[ "$PGUSER" == *-beta ]] || error "Beta database user '$PGUSER' doesn't end with '-beta' — refusing to run, this doesn't look like the beta database user"
SRC_DB="${TGT_DB%-beta}"

info "Source (production): $PGUSER@$PGHOST:$PGPORT/$SRC_DB"
info "Target (beta):       $PGUSER@$PGHOST:$PGPORT/$TGT_DB"

export PGPASSWORD

DUMP_FILE="$(mktemp -t django_beta_sync.XXXXXX.dump)"
cleanup() { rm -f "$DUMP_FILE"; }
trap cleanup EXIT

header "Dumping $SRC_DB"
pg_dump \
    -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
    --format=custom --no-owner --no-privileges \
    --file="$DUMP_FILE" "$SRC_DB"
success "Dump written to $DUMP_FILE"

header "Recreating $TGT_DB"
info "Terminating existing connections to $TGT_DB..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TGT_DB' AND pid <> pg_backend_pid();" \
    >/dev/null

info "Dropping database $TGT_DB..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS \"$TGT_DB\";"

info "Creating database $TGT_DB..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE \"$TGT_DB\" OWNER \"$PGUSER\";"
success "$TGT_DB recreated"

header "Restoring dump into $TGT_DB"
pg_restore \
    -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" \
    --no-owner --no-privileges --dbname="$TGT_DB" \
    "$DUMP_FILE"
success "Beta database now matches production"

warn "Remember: beta will run its own migrations on next deploy (see util/deploy.sh)."
