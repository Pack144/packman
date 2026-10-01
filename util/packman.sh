#!/usr/bin/env bash

set -euo pipefail

script_dir="$(dirname "${BASH_SOURCE[0]}")"

source "$script_dir/lib/logging.sh"

usage() {
    cat <<'EOF'
Usage: ./util/packman.sh <env> <command> [options]

Environments:
  dev     Local development environment (start, stop, sync).
  beta    Beta server (deploy).
  prod    Production server (deploy).

Commands:
  start   Install backend dependencies, migrate, and start Django.
  stop    Stop the Packman server for this checkout.
  sync    Sync local data from the selected environment.
  deploy  Run safety checks, trigger the GitHub Deploy workflow, and wait.

Options:
  --port PORT     Django port for start (default: 8000).
  --detach        Run Django in the background (start).
  --yes           start: replace an existing server without prompting.
                  deploy: skip the prod confirmation prompt.
  --sync-env ENV  Source environment for sync: beta or prod (default: beta).
  --branch NAME   Branch to deploy (default: current branch; prod only allows main).
  --reset-db      Replace beta's database with a copy of prod first (beta deploy).
  --force         Deploy despite workspace/beta-validation warnings (deploy).
  --dry-run       Run deploy checks and print the gh command without deploying.
  --compact       Show only relevant/failed steps while watching the deploy.
  --help, -h      Show this help message.
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

case "$env_name:$command_name" in
    dev:start|dev:stop|dev:sync|beta:deploy|prod:deploy) ;;
    dev:*) usage >&2; error "Unknown dev command '$command_name'. Expected 'start', 'stop', or 'sync'." ;;
    *) usage >&2; error "Unknown $env_name command '$command_name'. Expected 'deploy'." ;;
esac

port=8000
port_set=false
detach=false
assume_yes=false
sync_env=beta
branch=
reset_db=false
force=false
dry_run=false
compact=false

if [[ "$command_name" == "deploy" ]]; then
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --branch)
                [[ $# -ge 2 && -n "$2" ]] || error "--branch requires a value."
                branch="$2"
                shift 2
                ;;
            --reset-db)
                [[ "$env_name" == "beta" ]] || error "--reset-db is only valid for beta."
                reset_db=true
                shift
                ;;
            --yes) assume_yes=true; shift ;;
            --force) force=true; shift ;;
            --dry-run) dry_run=true; shift ;;
            --compact) compact=true; shift ;;
            --help|-h)
                usage
                exit 0
                ;;
            *) error "Unknown deploy option '$1'." ;;
        esac
    done
elif [[ "$command_name" == "sync" ]]; then
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

cmd_deploy() {
    "$script_dir/lib/gh-deploy-action.sh" "$env_name" "$branch" "$reset_db" "$assume_yes" "$force" "$dry_run" "$compact"
}

case "$command_name" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    sync) cmd_sync ;;
    deploy) cmd_deploy ;;
esac
