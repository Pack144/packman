#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"

project_root="${1:?Usage: stop-server.sh PROJECT_ROOT PID_FILE [--yes]}"
pid_file="${2:?Usage: stop-server.sh PROJECT_ROOT PID_FILE [--yes]}"
assume_yes="${3:-}"
server_group_ids=()

process_cwd() {
    lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p'
}

process_group_id() {
    ps -o pgid= -p "$1" 2>/dev/null | tr -d ' '
}

current_group_id="$(process_group_id "$$")"

add_server_group_id() {
    local server_group_id="$1"
    [[ "$server_group_id" =~ ^[0-9]+$ ]] || return 0

    local existing_group_id
    for existing_group_id in "${server_group_ids[@]}"; do
        [[ "$existing_group_id" == "$server_group_id" ]] && return 0
    done
    server_group_ids+=("$server_group_id")
}

if [[ -f "$pid_file" ]]; then
    recorded_pid="$(<"$pid_file")"
    if [[ "$recorded_pid" =~ ^[0-9]+$ ]] && kill -0 "$recorded_pid" 2>/dev/null \
        && [[ "$(process_cwd "$recorded_pid")" == "$project_root" ]]; then
        add_server_group_id "$(process_group_id "$recorded_pid")"
    else
        warn "Removing stale Packman PID file"
        rm -f "$pid_file"
    fi
fi

if [[ ${#server_group_ids[@]} -eq 0 ]]; then
    while read -r server_pid; do
        [[ -n "$server_pid" ]] || continue
        if [[ "$(process_cwd "$server_pid")" == "$project_root" ]]; then
            add_server_group_id "$(process_group_id "$server_pid")"
        fi
    done < <(pgrep -f 'manage.py runserver' || true)
fi

[[ ${#server_group_ids[@]} -eq 0 ]] && exit 0

if [[ "$assume_yes" != "--yes" ]]; then
    read -r -p "Packman server process group(s) ${server_group_ids[*]} appear to be running. Stop them? [y/N] " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "Keeping the existing server."
        exit 0
    fi
fi

for server_group_id in "${server_group_ids[@]}"; do
    if [[ "$server_group_id" == "$current_group_id" ]]; then
        warn "Refusing to signal the launcher process group ($server_group_id)"
        continue
    fi

    info "Stopping Packman server process group ($server_group_id)"
    if ! kill -- -"$server_group_id" 2>/dev/null; then
        info "Packman server process group ($server_group_id) already stopped"
        continue
    fi

    deadline=$((SECONDS + 10))
    while kill -0 -- -"$server_group_id" 2>/dev/null; do
        if (( SECONDS >= deadline )); then
            warn "Packman process group ($server_group_id) did not stop within 10 seconds; sending KILL"
            kill -KILL -- -"$server_group_id" 2>/dev/null || true
            break
        fi
        sleep 0.2
    done
done

rm -f "$pid_file"
