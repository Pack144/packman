#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

if [[ $# -ge 1 ]]; then
    APP_DIR="$1"
else
    # No APP_DIR given — see if we're already sitting in
    # $HOME/apps/<app-dir>/packman and offer to use that.
    APPS_DIR="$HOME/apps"
    CURRENT_DIR="$(pwd -P)"

    if [[ "$CURRENT_DIR" == "$APPS_DIR"/*/packman ]]; then
        APP_DIR="${CURRENT_DIR%/packman}"
        read -rp "⚠️  No APP_DIR given; detected '$APP_DIR' from the current directory. Continue? (y/N): " CONFIRM
        CONFIRM="${CONFIRM,,}"  # Convert to lowercase

        if [[ "$CONFIRM" != "y" && "$CONFIRM" != "yes" ]]; then
            echo "Operation cancelled by user."
            exit 3
        fi
    else
        echo "Usage: util/deploy.sh APP_DIR" >&2
        exit 1
    fi
fi

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
