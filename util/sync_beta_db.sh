#!/usr/bin/env bash
# sync_beta_db.sh — Wipe the beta PostgreSQL database and replace it with a
# fresh copy of the production database.
#
# Connects as the "django" user to dump the production ("django") database,
# and as the "django-beta" user to wipe/restore the beta ("django-beta")
# database. Passwords are not handled here — they're expected to come from
# the invoking user's ~/.pgpass file (see `man pgpass`).

set -euo pipefail

SRC_USER="django"
SRC_DB="django"
TGT_USER="django-beta"
TGT_DB="django-beta"

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

header "Sync beta database from production"

PGPASSFILE="${PGPASSFILE:-$HOME/.pgpass}"
[[ -f "$PGPASSFILE" ]] || error "No .pgpass file found at $PGPASSFILE — see 'man pgpass'"

info "Source (production): $SRC_USER/$SRC_DB (host/port from ~/.pgpass)"
info "Target (beta):       $TGT_USER/$TGT_DB (host/port from ~/.pgpass)"

DUMP_FILE="$(mktemp -t django_beta_sync.XXXXXX.dump)"
cleanup() { rm -f "$DUMP_FILE"; }
trap cleanup EXIT

header "Dumping $SRC_DB"
pg_dump \
    -U "$SRC_USER" \
    --format=custom --no-owner --no-privileges \
    --file="$DUMP_FILE" "$SRC_DB"
success "Dump written to $DUMP_FILE"

header "Recreating $TGT_DB"
info "Terminating existing connections to $TGT_DB..."
psql -U "$TGT_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TGT_DB' AND pid <> pg_backend_pid();" \
    >/dev/null

info "Dropping database $TGT_DB..."
psql -U "$TGT_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS \"$TGT_DB\";"

info "Creating database $TGT_DB..."
psql -U "$TGT_USER" -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE \"$TGT_DB\" OWNER \"$TGT_USER\";"
success "$TGT_DB recreated"

header "Restoring dump into $TGT_DB"
pg_restore \
    -U "$TGT_USER" \
    --no-owner --no-privileges --dbname="$TGT_DB" \
    "$DUMP_FILE"
success "Beta database now matches production"

warn "Remember: beta will run its own migrations on next deploy (see util/deploy.sh)."
