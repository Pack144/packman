#!/usr/bin/env bash
# start_local.sh — Start the Packman site locally for development/testing.
#
# Usage:
#   ./util/start_local.sh [OPTIONS]
#
# Options:
#   --port PORT       Port to run on (default: 8000)
#   --no-migrate      Skip running migrations
#   --no-install      Skip dependency install check
#   -h, --help        Show this help message

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# ── Defaults ──────────────────────────────────────────────────────────────────
PORT=8000
RUN_MIGRATE=true
RUN_INSTALL=true

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)       PORT="$2"; shift 2 ;;
        --no-migrate) RUN_MIGRATE=false; shift ;;
        --no-install) RUN_INSTALL=false; shift ;;
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

header "Packman Local Development Server"

# ── .env setup ────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
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
if command -v pipenv &>/dev/null; then
    info "Using pipenv"
    PYTHON="pipenv run python"

    if [ "$RUN_INSTALL" = true ]; then
        info "Checking dependencies..."
        pipenv install --dev 2>/dev/null \
            && success "Dependencies up to date" \
            || warn "pipenv install had warnings — continuing anyway"
    fi
else
    # Fall back to .venv or system python
    warn "pipenv not found — falling back to virtualenv"
    if [ ! -d ".venv" ]; then
        info "Creating .venv..."
        python3 -m venv .venv
    fi
    # shellcheck source=/dev/null
    source .venv/bin/activate

    if [ "$RUN_INSTALL" = true ]; then
        info "Installing local requirements..."
        pip install -q -r requirements/local.txt \
            && success "Dependencies installed"
    fi
    PYTHON="python"
fi

# ── npm / static assets ───────────────────────────────────────────────────────
if [ "$RUN_INSTALL" = true ] && [ -f "package.json" ]; then
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
