#!/usr/bin/env bash
set -euo pipefail

echo "== Deploy started =="

: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${VENV_PATH:?VENV_PATH is required}"

SRC_DIR="$(pwd)"
TARGET_DIR="$DEPLOY_PATH"
VENV_DIR="$VENV_PATH"

mkdir -p "$TARGET_DIR"

echo "== Sync code to target (excluding migrations .py files) =="

# Important:
# - We keep migrations/__init__.py
# - We exclude other migration python files like 0001_initial.py, etc.
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

# If your manage.py needs env vars, export them here:
# export DJANGO_SETTINGS_MODULE="yourproject.settings"
# export SECRET_KEY="..."
# export DEBUG="0"

python manage.py makemigrations
python manage.py migrate

echo "== Deploy finished =="
