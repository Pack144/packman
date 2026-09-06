#!/usr/bin/env bash
# sync_local_data.sh — Refresh local dev data from a beta or production
# Packman server.
#
# Connects over SSH to dump the remote PostgreSQL database with pg_dump,
# converts it to SQLite with util/pg_to_sqlite.py, and replaces db.sqlite3
# in this checkout. Also rsyncs any new or changed files from the remote
# media directory into the local media directory (existing local-only
# files are left alone — this only fills in what's missing/changed).
#
# Meant to be run from a base workspace checkout (the one other worktrees
# share via start_local.sh --base-workspace) so every worktree benefits
# from the refreshed data.
#
# Usage:
#   ./util/sync_local_data.sh [OPTIONS]
#
# Options:
#   --env beta|prod          Remote environment to pull from (default: beta)
#   --ssh-host USER@HOST     SSH destination for the remote server. Falls
#                            back to SYNC_SSH_HOST in .env.
#   --remote-media-dir DIR   Remote media directory to rsync from. Falls
#                            back to SYNC_REMOTE_MEDIA_DIR in .env.
#   --no-db                  Skip the database sync
#   --no-media               Skip the media sync
#   -h, --help                Show this help message

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo "  $*"; }
success() { echo "✅ $*"; }
warn()    { echo "⚠️  $*"; }
error()   { echo "❌ $*" >&2; exit 1; }
header()  { echo; echo "══════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════"; }

require_cmd() {
    command -v "$1" &>/dev/null || error "Required command '$1' not found on PATH"
}

# Read KEY="value" or KEY=value from .env, stripping surrounding quotes.
env_value() {
    [ -f ".env" ] || return 0
    grep -E "^$1=" .env | tail -n1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true
}

# ── Defaults ──────────────────────────────────────────────────────────────────
DB_ENV="beta"
SSH_HOST="$(env_value SYNC_SSH_HOST)"
REMOTE_MEDIA_DIR="$(env_value SYNC_REMOTE_MEDIA_DIR)"
RUN_DB=true
RUN_MEDIA=true

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)              DB_ENV="$2"; shift 2 ;;
        --ssh-host)         SSH_HOST="$2"; shift 2 ;;
        --remote-media-dir) REMOTE_MEDIA_DIR="$2"; shift 2 ;;
        --no-db)            RUN_DB=false; shift ;;
        --no-media)         RUN_MEDIA=false; shift ;;
        -h|--help)
            sed -n '/^# Usage:/,/^[^#]/{ /^[^#]/d; s/^# \{0,2\}//; p }' "$0"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

case "$DB_ENV" in
    beta) DB_USER="django-beta"; DB_NAME="django-beta" ;;
    prod) DB_USER="django";      DB_NAME="django" ;;
    *) error "--env must be 'beta' or 'prod' (got '$DB_ENV')" ;;
esac

[ -n "$SSH_HOST" ] || error "No SSH host given — pass --ssh-host USER@HOST or set SYNC_SSH_HOST in .env"
require_cmd ssh
require_cmd uv

header "Sync local data from $DB_ENV ($SSH_HOST)"

# ── Database ──────────────────────────────────────────────────────────────────
if [ "$RUN_DB" = true ]; then
    DUMP_FILE="$(mktemp -t packman_sync_db.XXXXXX)"
    DUMP_FILE="${DUMP_FILE}.sql.gz"
    cleanup_dump() { rm -f "$DUMP_FILE"; }
    trap cleanup_dump EXIT

    header "Dumping $DB_NAME from $SSH_HOST"
    ssh "$SSH_HOST" "/bin/pg_dump -b -Fp -U $DB_USER $DB_NAME | gzip" > "$DUMP_FILE" \
        || error "Remote pg_dump failed — see output above"
    success "Dump written to $DUMP_FILE"

    header "Converting dump to SQLite"
    DB_OUTPUT="$PROJECT_ROOT/db.sqlite3"
    DB_TMP_OUTPUT="${DB_OUTPUT}.new"
    rm -f "$DB_TMP_OUTPUT"
    uv run python util/pg_to_sqlite.py "$DUMP_FILE" --output "$DB_TMP_OUTPUT" --django
    mv -f "$DB_TMP_OUTPUT" "$DB_OUTPUT"
    success "Replaced $DB_OUTPUT with a fresh copy of $DB_ENV"
else
    warn "Skipping database sync (--no-db)"
fi

# ── Media ─────────────────────────────────────────────────────────────────────
if [ "$RUN_MEDIA" = true ]; then
    if [ -z "$REMOTE_MEDIA_DIR" ]; then
        warn "No remote media directory given — pass --remote-media-dir DIR or set SYNC_REMOTE_MEDIA_DIR in .env; skipping media sync"
    else
        require_cmd rsync

        LOCAL_MEDIA_DIR="$(env_value DJANGO_MEDIA_ROOT)"
        LOCAL_MEDIA_DIR="${LOCAL_MEDIA_DIR:-$PROJECT_ROOT/media}"
        mkdir -p "$LOCAL_MEDIA_DIR"

        header "Syncing media from $SSH_HOST:$REMOTE_MEDIA_DIR"
        rsync -az "$SSH_HOST:${REMOTE_MEDIA_DIR%/}/" "${LOCAL_MEDIA_DIR%/}/" \
            || error "rsync failed — see output above"
        success "Media directory up to date ($LOCAL_MEDIA_DIR)"
    fi
else
    warn "Skipping media sync (--no-media)"
fi

header "Done"
