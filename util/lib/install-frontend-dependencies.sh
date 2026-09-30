#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"

project_root="${1:?Usage: install-frontend-dependencies.sh PROJECT_ROOT RUNTIME_DIR}"
runtime_dir="${2:?Usage: install-frontend-dependencies.sh PROJECT_ROOT RUNTIME_DIR}"

dependency_stamp="$runtime_dir/npm-dependencies.sha256"

cd "$project_root"

if ! command -v npm >/dev/null 2>&1; then
    error "npm is required to install frontend dependencies. Install Node.js and npm, then retry."
fi

info "Checking frontend dependencies"
dependency_manifest_hash="$(shasum package.json package-lock.json)"
installed_dependency_hash=""
[[ -f "$dependency_stamp" ]] && installed_dependency_hash="$(<"$dependency_stamp")"

if [[ ! -d node_modules || "$dependency_manifest_hash" != "$installed_dependency_hash" ]] \
    || ! npm ls --depth=0 >/dev/null 2>&1; then
    info "Installing frontend dependencies"
    npm ci --no-audit --no-fund
    printf '%s\n' "$dependency_manifest_hash" >"$dependency_stamp"
    success "Frontend dependencies installed"
else
    success "Frontend dependencies are already up to date"
fi
