#!/usr/bin/env bash

set -euo pipefail

script_dir="$(dirname "${BASH_SOURCE[0]}")"
source "$script_dir/logging.sh"

project_root="${1:?Usage: start-server.sh PROJECT_ROOT PID_FILE LOG_FILE PORT [--detach] [--yes]}"
pid_file="${2:?Usage: start-server.sh PROJECT_ROOT PID_FILE LOG_FILE PORT [--detach] [--yes]}"
log_file="${3:?Usage: start-server.sh PROJECT_ROOT PID_FILE LOG_FILE PORT [--detach] [--yes]}"
port="${4:?Usage: start-server.sh PROJECT_ROOT PID_FILE LOG_FILE PORT [--detach] [--yes]}"
shift 4

detach=false
assume_yes=false
for argument in "$@"; do
    case "$argument" in
        --detach) detach=true ;;
        --yes) assume_yes=true ;;
        *) error "Unknown option '$argument'." ;;
    esac
done

cd "$project_root"
export DJANGO_SETTINGS_MODULE="packman.settings.local"

mkdir -p .local
runtime_dir="$(dirname "$pid_file")"
mkdir -p "$runtime_dir" "$(dirname "$log_file")"
"$script_dir/install-backend-dependencies.sh" "$project_root"
"$script_dir/install-frontend-dependencies.sh" "$project_root" "$runtime_dir"

stop_arguments=("$project_root" "$pid_file")
[[ "$assume_yes" == true ]] && stop_arguments+=(--yes)
"$script_dir/stop-server.sh" "${stop_arguments[@]}"

if ! command -v lsof >/dev/null 2>&1; then
    error "lsof is required to check whether the development server port is available."
fi
if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    error "Port $port is already in use. Choose another port with --port PORT."
fi

info "Applying migrations"
uv run python manage.py migrate
success "Migrations applied"

"$script_dir/configure-caddy.sh" "$port"

header "Starting Packman on http://localhost:$port"
if [[ "$detach" == true ]]; then
    nohup uv run python "$script_dir/run_server.py" "$port" "$pid_file" >"$log_file" 2>&1 < /dev/null &
    launcher_pid=$!

    for _ in $(seq 1 50); do
        server_pid=""
        [[ -f "$pid_file" ]] && server_pid="$(<"$pid_file")"
        if [[ "$server_pid" =~ ^[0-9]+$ ]] && kill -0 "$server_pid" 2>/dev/null; then
            if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
                success "Packman is running in the background (process group $server_pid)"
                info "Logs: $log_file"
                exit 0
            fi
        elif ! kill -0 "$launcher_pid" 2>/dev/null; then
            tail -n 20 "$log_file" >&2 || true
            "$script_dir/stop-server.sh" "$project_root" "$pid_file" --yes || true
            error "Development server exited before it was ready."
        fi
        sleep 0.2
    done

    "$script_dir/stop-server.sh" "$project_root" "$pid_file" --yes || true
    error "Development server did not begin listening within 10 seconds; see $log_file."
fi

uv run python "$script_dir/run_server.py" "$port" "$pid_file" &
server_launcher_pid=$!

stop_server() {
    "$script_dir/stop-server.sh" "$project_root" "$pid_file" --yes
}

handle_interrupt() {
    trap - INT TERM EXIT
    stop_server
    exit 130
}

trap stop_server EXIT
trap handle_interrupt INT TERM
wait "$server_launcher_pid"
