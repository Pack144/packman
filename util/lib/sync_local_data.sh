#!/usr/bin/env bash
# sync_local_data.sh — Refresh local dev data from a beta or production
# Packman server.
#
# Connects over SSH to dump the remote PostgreSQL database with pg_dump,
# converts it to SQLite with util/pg_to_sqlite.py, and replaces db.sqlite3
# in this checkout. Also rsyncs any new or changed files from the remote
# media directory into the local media directory (existing local-only
# files are left alone — this only fills in what's missing/changed).
# Skips the documents, doc_backups, and mail folders, which are large and
# not generally needed for local dev.
#
# Run from a base workspace checkout to refresh its local dev database and
# media from beta or production.
#
# Internal helper for `packman.sh dev sync`; sync environment is its only
# argument. SSH/media/password settings come from the Packman .env file.

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"

PROJECT_ROOT="$PWD"
DB_ENV="${1:?Usage: sync_local_data.sh SYNC_ENV}"

# ── Helpers ───────────────────────────────────────────────────────────────────
require_cmd() {
    command -v "$1" &>/dev/null || error "Required command '$1' not found on PATH"
}

# Read KEY="value" or KEY=value from .env, stripping surrounding quotes.
env_value() {
    [ -f ".env" ] || return 0
    grep -E "^$1=" .env | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true
}

# Resolve the local sqlite3 path Django will use, from DATABASE_URL in .env
# (django-environ: sqlite:///relative/path.sqlite3 or sqlite:////abs/path.sqlite3).
# Falls back to db.sqlite3 in the project root if DATABASE_URL is unset
# (matching Django's own default); errors if it's set to a non-sqlite URL,
# since this script only knows how to write a sqlite3 file.
sqlite_db_path() {
    local db_url db_path
    db_url="$(env_value DATABASE_URL)"
    if [ -z "$db_url" ]; then
        echo "$PROJECT_ROOT/db.sqlite3"
    elif [[ "$db_url" == sqlite://* ]]; then
        db_path="${db_url#sqlite://}"
        db_path="${db_path#/}"
        if [[ "$db_path" == /* ]]; then
            echo "$db_path"
        else
            echo "$PROJECT_ROOT/$db_path"
        fi
    else
        error "DATABASE_URL in .env is not a sqlite URL ('$db_url') — sync_local_data.sh only supports syncing to a sqlite3 database"
    fi
}

# ── Defaults ──────────────────────────────────────────────────────────────────
SSH_HOST="$(env_value SYNC_SSH_HOST)"
REMOTE_MEDIA_DIR="$(env_value SYNC_REMOTE_MEDIA_DIR)"

case "$DB_ENV" in
    beta) DB_USER="django-beta"; DB_NAME="django-beta" ;;
    prod) DB_USER="django";      DB_NAME="django" ;;
    *) error "--sync-env must be 'beta' or 'prod' (got '$DB_ENV')" ;;
esac

[ -n "$SSH_HOST" ] || error "No SSH host given — pass --ssh-host USER@HOST or set SYNC_SSH_HOST in .env"
require_cmd ssh
require_cmd uv

header "Sync local data from $DB_ENV ($SSH_HOST)"

# ── Database ──────────────────────────────────────────────────────────────────
DUMP_FILE="$(mktemp -t packman_sync_db.XXXXXX)"
DUMP_FILE="${DUMP_FILE}.sql.gz"
cleanup_dump() { rm -f "$DUMP_FILE"; }
trap cleanup_dump EXIT

header "Dumping $DB_NAME from $SSH_HOST"
ssh "$SSH_HOST" "/bin/pg_dump -b -Fp -U $DB_USER $DB_NAME | gzip" > "$DUMP_FILE" \
    || error "Remote pg_dump failed — see output above"
success "Dump written to $DUMP_FILE"

header "Converting dump to SQLite"
DB_OUTPUT="$(sqlite_db_path)"
mkdir -p "$(dirname "$DB_OUTPUT")"
rm -f "$DB_OUTPUT"
uv run python util/pg_to_sqlite.py "$DUMP_FILE" --output "$DB_OUTPUT" --django
success "Replaced $DB_OUTPUT with a fresh copy of $DB_ENV"

if [ -n "$(env_value SYNC_RESET_PW_EMAIL)" ]; then
    header "Resetting local password (if configured)"
    uv run python util/lib/reset_local_password.py \
        || warn "Password reset failed — see output above"
else
    warn "Skipping password reset (--no-reset-password)"
fi

# ── Media ─────────────────────────────────────────────────────────────────────
if [ -n "$REMOTE_MEDIA_DIR" ]; then
    require_cmd rsync

    LOCAL_MEDIA_DIR="$(env_value DJANGO_MEDIA_ROOT)"
    LOCAL_MEDIA_DIR="${LOCAL_MEDIA_DIR:-$PROJECT_ROOT/media}"
    mkdir -p "$LOCAL_MEDIA_DIR"

    header "Syncing media from $SSH_HOST:$REMOTE_MEDIA_DIR"
    rsync -az \
        --exclude=documents \
        --exclude=doc_backups \
        --exclude=mail \
        "$SSH_HOST:${REMOTE_MEDIA_DIR%/}/" "${LOCAL_MEDIA_DIR%/}/" \
        || error "rsync failed — see output above"
    success "Media directory up to date ($LOCAL_MEDIA_DIR)"
else
    warn "No remote media directory given — pass SYNC_REMOTE_MEDIA_DIR in .env; skipping media sync"
fi

header "Done"
