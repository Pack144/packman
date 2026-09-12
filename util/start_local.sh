#!/usr/bin/env bash
# start_local.sh — Start the Packman site locally for development/testing.
#
# Usage:
#   ./util/start_local.sh [OPTIONS]
#
# Options:
#   --port PORT              Port to run on (default: 8000)
#   --kill-existing          Stop the process currently listening on the port
#                            before starting the development server
#   --detach                 Start the server in the background and return once
#                            it is accepting connections
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

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$PROJECT_ROOT"

# ── Defaults ──────────────────────────────────────────────────────────────────
PORT=8000
KILL_EXISTING=false
DETACH=false
RUN_MIGRATE=true
RUN_INSTALL=true
BASE_WORKSPACE="${PACKMAN_BASE_WORKSPACE:-}"
BASE_WORKSPACE_SET=false

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            [ "$#" -ge 2 ] || { echo "Missing value for --port" >&2; exit 1; }
            PORT="$2"
            shift 2 ;;
        --kill-existing)  KILL_EXISTING=true; shift ;;
        --detach)         DETACH=true; shift ;;
        --no-migrate)     RUN_MIGRATE=false; shift ;;
        --no-install)     RUN_INSTALL=false; shift ;;
        --base-workspace) BASE_WORKSPACE="$2"; BASE_WORKSPACE_SET=true; shift 2 ;;
        -h|--help)
            sed -n '/^# Usage:/,/^[^#]/p' "$0" | sed '$d; s/^# \{0,2\}//'
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

PID_FILE="${PACKMAN_DEV_PID:-${TMPDIR:-/tmp}/packman-dev-$PORT.pid}"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo "  $*"; }
success() { echo "✅ $*"; }
warn()    { echo "⚠️  $*"; }
error()   { echo "❌ $*" >&2; exit 1; }
header()  { echo; echo "══════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════"; }

if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    error "Port must be an integer between 1 and 65535"
fi

command -v lsof &>/dev/null || error "lsof is required to check the development server port"

listening_pids() {
    lsof -nP -tiTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | sort -u
}

port_is_available() {
    ! lsof -nP -iTCP:"$PORT" -sTCP:LISTEN &>/dev/null
}

port_is_listening() {
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN &>/dev/null
}

is_packman_dev_server() {
    local pid="$1"
    local command_line
    local process_cwd

    command_line="$(ps -p "$pid" -o command= 2>/dev/null)" || return 1
    if ! [[ "$command_line" =~ (^|[[:space:]])manage\.py[[:space:]]+runserver([[:space:]]|$) ]]; then
        return 1
    fi

    process_cwd="$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)"
    [ -n "$process_cwd" ] || return 1
    process_cwd="$(cd "$process_cwd" 2>/dev/null && pwd -P)" || return 1
    [ "$process_cwd" = "$PROJECT_ROOT" ]
}

is_descendant_of() {
    local pid="$1"
    local ancestor="$2"

    while [ "$pid" -gt 1 ] 2>/dev/null; do
        [ "$pid" = "$ancestor" ] && return 0
        pid="$(ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ')" || return 1
        [ -n "$pid" ] || return 1
    done
    return 1
}

stop_existing_server() {
    local pids="$1"
    local listening_pid
    local tracked_pid=""
    local deadline

    if [ -f "$PID_FILE" ]; then
        tracked_pid="$(cat "$PID_FILE")"
        if ! [[ "$tracked_pid" =~ ^[0-9]+$ ]] || ! is_packman_dev_server "$tracked_pid"; then
            tracked_pid=""
        else
            for listening_pid in $pids; do
                if is_descendant_of "$listening_pid" "$tracked_pid"; then
                    pids="$tracked_pid"
                    break
                fi
            done
        fi
    fi

    info "Stopping process(es) listening on port $PORT: $pids"
    for pid in $pids; do
        kill "$pid" || error "Unable to stop PID $pid"
    done

    deadline=$((SECONDS + 10))
    for pid in $pids; do
        while kill -0 "$pid" 2>/dev/null; do
            if [ "$SECONDS" -ge "$deadline" ]; then
                error "PID $pid did not stop within 10 seconds"
            fi
            sleep 0.2
        done
    done
    if port_is_listening; then
        error "Port $PORT is still accepting connections after stopping PID(s): $pids"
    fi
    success "Port $PORT is available"
}

header "Packman Local Development Server"

# ── Port availability ─────────────────────────────────────────────────────────
LISTENING_PIDS="$(listening_pids || true)"
if [ -n "$LISTENING_PIDS" ]; then
    ps -p "$(echo "$LISTENING_PIDS" | paste -sd, -)" -o pid=,command= 2>/dev/null || true
    NON_PACKMAN_PIDS=""
    for pid in $LISTENING_PIDS; do
        if ! is_packman_dev_server "$pid"; then
            NON_PACKMAN_PIDS="$NON_PACKMAN_PIDS $pid"
        fi
    done
    if [ -n "$NON_PACKMAN_PIDS" ]; then
        error "Port $PORT is used by a process that is not this checkout's Packman development server (PID(s):${NON_PACKMAN_PIDS}). Stop it separately or choose another port with --port PORT."
    fi
    if [ "$KILL_EXISTING" = true ]; then
        stop_existing_server "$LISTENING_PIDS"
    else
        error "Packman development server is already using port $PORT. Re-run with --kill-existing or choose another port with --port PORT."
    fi
elif ! port_is_available; then
    error "Port $PORT is already in use, but its process could not be identified. Choose another port with --port PORT."
fi

# ── Base workspace reuse ──────────────────────────────────────────────────────
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
echo

if [ "$DETACH" = true ]; then
    LOG_FILE="${PACKMAN_DEV_LOG:-${TMPDIR:-/tmp}/packman-dev-$PORT.log}"

    nohup $PYTHON manage.py runserver "0.0.0.0:$PORT" >"$LOG_FILE" 2>&1 < /dev/null &
    SERVER_PID=$!
    echo "$SERVER_PID" >"$PID_FILE"

    for _ in $(seq 1 50); do
        if ! kill -0 "$SERVER_PID" 2>/dev/null; then
            tail -n 20 "$LOG_FILE" >&2 || true
            error "Development server exited before it was ready"
        fi
        if port_is_listening; then
            success "Development server started in the background (PID $SERVER_PID)"
            info "Log: $LOG_FILE"
            info "PID file: $PID_FILE"
            exit 0
        fi
        sleep 0.2
    done

    kill "$SERVER_PID" 2>/dev/null || true
    error "Development server did not begin listening within 10 seconds; see $LOG_FILE"
else
    info "Press Ctrl+C to stop"
    $PYTHON manage.py runserver "0.0.0.0:$PORT"
fi
