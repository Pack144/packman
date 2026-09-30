#!/usr/bin/env bash

set -euo pipefail

script_dir="$(dirname "${BASH_SOURCE[0]}")"

source "$script_dir/lib/logging.sh"

usage() {
    cat <<'EOF'
Usage: ./util/packman.sh <env> <command> [options]

Environments:
  dev     Local development environment.
  beta    Not implemented.
  prod    Not implemented.

Commands:
  start   Install backend dependencies, migrate, and start Django.
  stop    Stop the Packman server for this checkout.
    sync    Sync local data from the selected environment.

Options:
  --port PORT   Django port for start (default: 8000).
  --detach      Run Django in the background (start).
  --yes         Replace an existing Packman server without prompting (start).
    --sync-env ENV  Source environment for sync: beta or prod (default: beta).
  --help, -h    Show this help message.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

env_name="${1:-}"
command_name="${2:-}"
if [[ -z "$env_name" || -z "$command_name" ]]; then
    usage >&2
    error "Both <env> and <command> are required."
fi
shift 2

case "$env_name" in
    dev|beta|prod) ;;
    *) usage >&2; error "Unknown environment '$env_name'. Expected 'dev', 'beta', or 'prod'." ;;
esac

case "$command_name" in
    start|stop|sync) ;;
    *) usage >&2; error "Unknown command '$command_name'. Expected 'start', 'stop', or 'sync'." ;;
esac

if [[ "$env_name" != "dev" ]]; then
    error "The '$env_name' environment is not implemented yet."
fi

port=8000
port_set=false
detach=false
assume_yes=false
sync_env=beta

if [[ "$command_name" == "sync" ]]; then
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --sync-env)
                [[ $# -ge 2 ]] || error "--sync-env requires a value."
                sync_env="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *) error "Unknown sync option '$1'." ;;
        esac
    done

    case "$sync_env" in
        beta|prod) ;;
        *) error "--sync-env must be 'beta' or 'prod' (got '$sync_env')" ;;
    esac
else
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --port)
                [[ $# -ge 2 ]] || error "--port requires a value."
                port="$2"
                port_set=true
                shift 2
                ;;
            --detach) detach=true; shift ;;
            --yes) assume_yes=true; shift ;;
            --help|-h)
                usage
                exit 0
                ;;
            *) error "Unknown option '$1'." ;;
        esac
    done
fi

if [[ ! -f manage.py || ! -f pyproject.toml ]]; then
    error "Run this script from the Packman project root."
fi

if [[ "$command_name" == "stop" ]]; then
    [[ "$assume_yes" == false && "$detach" == false ]] || error "--detach and --yes are only valid with start."
    [[ "$port_set" == false ]] || error "--port is only valid with start."
fi

if [[ "$command_name" == "start" ]]; then
    [[ "$port" =~ ^[0-9]+$ ]] || error "Port must be an integer between 1 and 65535."
    port=$((10#$port))
    (( port >= 1 && port <= 65535 )) || error "Port must be an integer between 1 and 65535."
fi

runtime_dir="$PWD/.run"
pid_file="$runtime_dir/packman.pid"
log_file="$runtime_dir/packman.log"

cmd_start() {
    mkdir -p "$runtime_dir"
    local start_args=("$PWD" "$pid_file" "$log_file" "$port")
    [[ "$detach" == true ]] && start_args+=(--detach)
    [[ "$assume_yes" == true ]] && start_args+=(--yes)
    "$script_dir/lib/start-server.sh" "${start_args[@]}"
}

cmd_stop() {
    "$script_dir/lib/stop-server.sh" "$PWD" "$pid_file" --yes
}

cmd_sync() {
    "$script_dir/lib/sync_local_data.sh" "$sync_env"
}

case "$command_name" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    sync) cmd_sync ;;
esac
