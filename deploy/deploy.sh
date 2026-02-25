#!/usr/bin/env bash
set -euo pipefail

echo "== Deploy started =="

: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${VENV_PATH:?VENV_PATH is required}"
: "${SERVICE_NAME:?SERVICE_NAME is required}"   # <-- add this

SRC_DIR="$(pwd)"
TARGET_DIR="$DEPLOY_PATH"
VENV_DIR="$VENV_PATH"

mkdir -p "$TARGET_DIR"

echo "== Sync code to target (excluding migrations .py files) =="

rsync -a --delete \
  --exclude ".git/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --exclude "media/" \
  --exclude "staticfiles/" \
  --exclude "*/migrations/*.py" \
  --include "*/migrations/__init__.py" \
  "$SRC_DIR/" "$TARGET_DIR/"

echo "== Create/Use virtualenv =="

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel setuptools

echo "== Install requirements =="
pip install -r "$TARGET_DIR/requirements.txt"

echo "== Django migrate =="
cd "$TARGET_DIR"

python manage.py makemigrations
python manage.py migrate

echo "== Restart service: $SERVICE_NAME =="
sudo systemctl restart "$SERVICE_NAME"

echo "== Check service status =="
sudo systemctl --no-pager --full status "$SERVICE_NAME" || true

echo "== Deploy finished =="