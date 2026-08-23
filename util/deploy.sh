#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

APP_DIR="${1:?Usage: util/deploy.sh APP_DIR}"

if [[ ! -d "$APP_DIR/packman" ]]; then
    echo "Error: '$APP_DIR/packman' does not exist" >&2
    exit 2
fi

# Resolve to an absolute path
APP_DIR="$(cd "$APP_DIR" && pwd -P)"
STAGE="$(basename "$APP_DIR")"

echo "Deploying '$STAGE' ($APP_DIR)"

cd "$APP_DIR/packman"

echo "Updating dependencies"
UV_PROJECT_ENVIRONMENT="$APP_DIR/env" uv sync --group production

echo "Running database migrations"
"$APP_DIR/env/bin/python" manage.py migrate

echo "Collecting any new static files"
DJANGO_SETTINGS_MODULE=packman.settings.production "$APP_DIR/env/bin/python" manage.py collectstatic --no-input

echo "Initiating server restart"
touch "$APP_DIR/packman/packman/wsgi.py"
