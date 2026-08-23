#!/usr/bin/env bash
# sync_beta_db.sh — Wipe the beta PostgreSQL database and replace it with a
# fresh copy of the production database.
#
# Connects as the "django" user to dump the production ("django") database,
# and as the "django-beta" user to load it into the beta ("django-beta")
# database. pg_dump --clean --if-exists embeds DROP commands for each object
# directly in the (plain-text) dump, so the objects are cleaned out as the
# dump is loaded and the database itself never needs to be dropped/recreated.
# Passwords are not handled here — they're expected to come from the
# invoking user's ~/.pgpass file (see `man pgpass`).

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
require_cmd psql

header "Sync beta database from production"

PGPASSFILE="${PGPASSFILE:-$HOME/.pgpass}"
[[ -f "$PGPASSFILE" ]] || error "No .pgpass file found at $PGPASSFILE — see 'man pgpass'"

info "Source (production): $SRC_USER/$SRC_DB (host/port from ~/.pgpass)"
info "Target (beta):       $TGT_USER/$TGT_DB (host/port from ~/.pgpass)"

DUMP_FILE="$(mktemp -t django_beta_sync.XXXXXX.sql)"
cleanup() { rm -f "$DUMP_FILE"; }
trap cleanup EXIT

header "Dumping $SRC_DB"
pg_dump \
    -U "$SRC_USER" \
    --clean --if-exists --no-owner --no-privileges \
    --file="$DUMP_FILE" "$SRC_DB"
success "Dump written to $DUMP_FILE"

header "Loading dump into $TGT_DB"
psql -U "$TGT_USER" -d "$TGT_DB" -v ON_ERROR_STOP=1 -f "$DUMP_FILE"
success "Beta database now matches production"

warn "Remember: beta will run its own migrations on next deploy (see util/deploy.sh)."
