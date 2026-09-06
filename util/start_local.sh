#!/usr/bin/env bash
# start_local.sh — Start the Packman site locally for development/testing.
#
# Usage:
#   ./util/start_local.sh [OPTIONS]
#
# Options:
#   --port PORT              Port to run on (default: 8000)
#   --no-migrate             Skip running migrations
#   --no-install             Skip dependency install check
#   --base-workspace PATH    Reuse an already set-up checkout (e.g. the main
#                            worktree) at PATH: shares its uv virtualenv and
#                            symlinks node_modules/.env so a fresh worktree
#                            doesn't have to redownload everything. Defaults
#                            to $PACKMAN_BASE_WORKSPACE, or is auto-detected
#                            from `git worktree list` when this checkout is a
#                            worktree. Pass --base-workspace "" to disable.
#   -h, --help               Show this help message

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Defaults ──────────────────────────────────────────────────────────────────
PORT=8000
RUN_MIGRATE=true
RUN_INSTALL=true
BASE_WORKSPACE="${PACKMAN_BASE_WORKSPACE:-}"
BASE_WORKSPACE_SET=false

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)           PORT="$2"; shift 2 ;;
        --no-migrate)     RUN_MIGRATE=false; shift ;;
        --no-install)     RUN_INSTALL=false; shift ;;
        --base-workspace) BASE_WORKSPACE="$2"; BASE_WORKSPACE_SET=true; shift 2 ;;
        -h|--help)
            sed -n '/^# Usage:/,/^[^#]/{ /^[^#]/d; s/^# \{0,2\}//; p }' "$0"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo "  $*"; }
success() { echo "✅ $*"; }
warn()    { echo "⚠️  $*"; }
error()   { echo "❌ $*" >&2; exit 1; }
header()  { echo; echo "══════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════"; }

# ── Auto-detect a base workspace to reuse ────────────────────────────────────
# When running from a git worktree (e.g. a Copilot session checkout) and no
# --base-workspace/PACKMAN_BASE_WORKSPACE was given, reuse the main checkout
# so we don't redo a full uv sync / npm install on every fresh worktree.
if [ "$BASE_WORKSPACE_SET" = false ] && [ -z "$BASE_WORKSPACE" ] && command -v git &>/dev/null; then
    MAIN_WORKTREE="$(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2; exit}')"
    if [ -n "$MAIN_WORKTREE" ] && [ "$MAIN_WORKTREE" != "$PROJECT_ROOT" ]; then
        BASE_WORKSPACE="$MAIN_WORKTREE"
    fi
fi
if [ -n "$BASE_WORKSPACE" ]; then
    BASE_WORKSPACE="$(cd "$BASE_WORKSPACE" 2>/dev/null && pwd || echo "$BASE_WORKSPACE")"
    if [ "$BASE_WORKSPACE" = "$PROJECT_ROOT" ] || [ ! -d "$BASE_WORKSPACE" ]; then
        BASE_WORKSPACE=""
    fi
fi

header "Packman Local Development Server"

# ── Base workspace reuse ──────────────────────────────────────────────────────
if [ -n "$BASE_WORKSPACE" ]; then
    info "Reusing base workspace: $BASE_WORKSPACE"
fi

# ── .env setup ────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    if [ -n "$BASE_WORKSPACE" ] && [ -f "$BASE_WORKSPACE/.env" ]; then
        info "No .env file found — copying from base workspace"
        cp "$BASE_WORKSPACE/.env" .env
        success "Copied .env from base workspace"
    elif [ -f "env.example" ]; then
        warn "No .env file found — copying from env.example"
        cp env.example .env
        warn "Review .env before running (especially SECRET_KEY and DATABASE_URL)"
    else
        warn "No .env file found — using Django defaults (SQLite, DEBUG=True)"
    fi
else
    success ".env found"
fi

export DJANGO_SETTINGS_MODULE="packman.settings.local"

# ── Python environment ────────────────────────────────────────────────────────
if command -v uv &>/dev/null; then
    info "Using uv"
    PYTHON="uv run python"

    if [ -n "$BASE_WORKSPACE" ] && [ -d "$BASE_WORKSPACE/.venv" ] && [ ! -d ".venv" ]; then
        export UV_PROJECT_ENVIRONMENT="$BASE_WORKSPACE/.venv"
        success "Sharing .venv from base workspace ($UV_PROJECT_ENVIRONMENT)"
    fi

    if [ "$RUN_INSTALL" = true ]; then
        info "Syncing dependencies..."
        uv sync \
            && success "Dependencies up to date" \
            || error "uv sync failed — see output above for details"
    fi
else
    error "uv not found — install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# ── npm / static assets ───────────────────────────────────────────────────────
if [ "$RUN_INSTALL" = true ] && [ -f "package.json" ]; then
    if [ ! -e "node_modules" ] && [ -n "$BASE_WORKSPACE" ] && [ -d "$BASE_WORKSPACE/node_modules" ]; then
        ln -s "$BASE_WORKSPACE/node_modules" node_modules
        success "Linked node_modules from base workspace"
    fi

    if [ ! -d "node_modules" ]; then
        info "node_modules not found — running npm install..."
        npm install \
            && success "npm packages installed" \
            || warn "npm install had warnings — static assets may be incomplete"
    else
        success "node_modules present"
    fi
fi

# ── Verify Django is reachable ────────────────────────────────────────────────
$PYTHON -c "import django" 2>/dev/null \
    || error "Django not importable — check your environment"

# ── Migrations ────────────────────────────────────────────────────────────────
if [ "$RUN_MIGRATE" = true ]; then
    info "Checking for pending migrations..."
    PENDING=$($PYTHON manage.py showmigrations --plan 2>/dev/null | grep -c "^\[ \]" || true)
    if [ "$PENDING" -gt 0 ]; then
        info "Applying $PENDING pending migration(s)..."
        $PYTHON manage.py migrate
        success "Migrations applied"
    else
        success "Migrations up to date"
    fi
else
    warn "Skipping migrations (--no-migrate)"
fi

# ── Superuser hint ────────────────────────────────────────────────────────────
DB_URL="${DATABASE_URL:-sqlite:///db.sqlite3}"
if [[ "$DB_URL" == sqlite* ]]; then
    DB_FILE="${DB_URL#sqlite:///}"
    DB_FILE="${DB_FILE#sqlite://}"
    if [ ! -f "$DB_FILE" ] && [ ! -f "db.sqlite3" ]; then
        warn "Fresh database detected — you may want to create a superuser:"
        warn "  $PYTHON manage.py createsuperuser"
    fi
fi

# ── Start server ──────────────────────────────────────────────────────────────
header "Starting server on http://localhost:$PORT"
info "Press Ctrl+C to stop"
echo

$PYTHON manage.py runserver "0.0.0.0:$PORT"
