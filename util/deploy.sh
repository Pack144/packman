#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

APPS_DIR="/home/pack144/apps"
PROD_APP_DIR="$APPS_DIR/django"
PROD_PACKMAN_DIR="$PROD_APP_DIR/packman"
BETA_APP_DIR="$APPS_DIR/django-beta"
BETA_PACKMAN_DIR="$BETA_APP_DIR/packman"

CURRENT_DIR="$(pwd -P)"

# Verify directory and identify stage
if [[ "$CURRENT_DIR" == "$PROD_PACKMAN_DIR" ]]; then
    STAGE="prod"
    APP_DIR="$PROD_APP_DIR"
elif [[ "$CURRENT_DIR" == "$BETA_PACKMAN_DIR" ]]; then
    STAGE="beta"
    APP_DIR="$BETA_APP_DIR"
else
    echo "Error: This script must be run from:"
    echo "   $PROD_PACKMAN_DIR"
    echo "   $BETA_PACKMAN_DIR"
    exit 2
fi

# Ask user for confirmation
read -rp "⚠️  You are in the '$STAGE' environment. Proceed with deployment? (y/N): " CONFIRM
CONFIRM="${CONFIRM,,}"  # Convert to lowercase

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "yes" ]]; then
    echo "Operation cancelled by user."
    exit 3
fi

echo "Updating dependencies"
UV_PROJECT_ENVIRONMENT="$APP_DIR/env" uv sync --group production

echo "Running database migrations"
$APP_DIR/env/bin/python manage.py migrate

echo "Collecting any new static files"
DJANGO_SETTINGS_MODULE=packman.settings.production $APP_DIR/env/bin/python manage.py collectstatic --no-input

echo "Initiating server restart"
touch $APP_DIR/packman/packman/wsgi.py