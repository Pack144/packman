#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: util/deploy.sh --app-dir DIR

  --app-dir DIR   Path to the app directory containing the "env" virtualenv
                  and "packman" git checkout (e.g. ~/apps/django-beta)
  -h, --help      Show this help message
USAGE
}

APP_DIR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app-dir)
            APP_DIR="${2:-}"
            shift 2
            ;;
        --app-dir=*)
            APP_DIR="${1#*=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

if [[ -z "$APP_DIR" ]]; then
    echo "Error: --app-dir is required" >&2
    usage
    exit 2
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
