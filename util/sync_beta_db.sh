#!/usr/bin/env bash
# sync_beta_db.sh — Wipe the beta PostgreSQL database and replace it with a
# fresh copy of the production database.
#
# Connects as the "django" user to dump the production ("django") database,
# and as the "django-beta" user to restore into the beta ("django-beta")
# database. Before restoring, every table, view, and sequence in django-beta
# is explicitly dropped, so the database itself never needs to be
# dropped/recreated. Passwords are not handled here — they're expected to
# come from the invoking user's ~/.pgpass file (see `man pgpass`).

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

[[ "$TGT_DB" == *-beta ]] || error "TGT_DB '$TGT_DB' doesn't end with '-beta' — refusing to run, this doesn't look like the beta database"
[[ "$TGT_USER" == *-beta ]] || error "TGT_USER '$TGT_USER' doesn't end with '-beta' — refusing to run, this doesn't look like the beta database user"

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

header "Restoring dump into $TGT_DB"
info "Dropping all tables, views, and sequences in $TGT_DB..."
psql -U "$TGT_USER" -d "$TGT_DB" -v ON_ERROR_STOP=1 <<'SQL'
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT schemaname, viewname FROM pg_views WHERE schemaname = 'public') LOOP
        EXECUTE format('DROP VIEW IF EXISTS %I.%I CASCADE', r.schemaname, r.viewname);
    END LOOP;
    FOR r IN (SELECT schemaname, tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE format('DROP TABLE IF EXISTS %I.%I CASCADE', r.schemaname, r.tablename);
    END LOOP;
    FOR r IN (SELECT schemaname, sequencename FROM pg_sequences WHERE schemaname = 'public') LOOP
        EXECUTE format('DROP SEQUENCE IF EXISTS %I.%I CASCADE', r.schemaname, r.sequencename);
    END LOOP;
END $$;
SQL

pg_restore \
    -U "$TGT_USER" \
    --no-owner --no-privileges --dbname="$TGT_DB" \
    "$DUMP_FILE"
success "Beta database now matches production"

warn "Remember: beta will run its own migrations on next deploy (see util/deploy.sh)."
