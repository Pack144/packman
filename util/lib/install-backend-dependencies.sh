#!/usr/bin/env bash

set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/logging.sh"

project_root="${1:?Usage: install-backend-dependencies.sh PROJECT_ROOT}"
cd "$project_root"

if ! command -v uv >/dev/null 2>&1; then
    error "uv is required to install backend dependencies. Install uv, then retry."
fi

info "Checking backend dependencies"
if [[ ! -d .venv ]] || ! uv sync --locked --check >/dev/null 2>&1; then
    info "Installing backend dependencies"
    uv sync --locked
    success "Backend dependencies installed"
else
    info "Backend dependencies are already up to date"
fi
