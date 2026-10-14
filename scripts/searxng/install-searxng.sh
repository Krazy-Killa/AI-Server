#!/usr/bin/env bash
# Installs SearXNG into a Python 3.12 virtualenv inside WSL (no root required).
# SearXNG needs Python 3.11+, so uv downloads a private Python if the system one is older.
# Safe to re-run: it updates the checkout and dependencies and keeps your settings.
set -euo pipefail

SEARXNG_HOME="${SEARXNG_HOME:-$HOME/searxng}"
PYTHON_VERSION="${SEARXNG_PYTHON:-3.12}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS_FILE="$SEARXNG_HOME/settings.yml"
export PATH="$HOME/.local/bin:$PATH"

command -v git >/dev/null || { echo "git is required." >&2; exit 1; }
command -v curl >/dev/null || { echo "curl is required." >&2; exit 1; }

if ! command -v uv >/dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

mkdir -p "$SEARXNG_HOME"

if [ -d "$SEARXNG_HOME/src/.git" ]; then
    echo "Updating SearXNG source..."
    git -C "$SEARXNG_HOME/src" pull --ff-only --depth 1
else
    echo "Cloning SearXNG..."
    git clone --depth 1 https://github.com/searxng/searxng.git "$SEARXNG_HOME/src"
fi

if ! "$SEARXNG_HOME/venv/bin/python" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    echo "Creating Python $PYTHON_VERSION virtualenv..."
    rm -rf "$SEARXNG_HOME/venv"
    uv venv --python "$PYTHON_VERSION" "$SEARXNG_HOME/venv"
fi

echo "Installing dependencies..."
uv pip install -q --python "$SEARXNG_HOME/venv/bin/python" \
    -r "$SEARXNG_HOME/src/requirements.txt" \
    -r "$SEARXNG_HOME/src/requirements-server.txt"

if [ ! -f "$SETTINGS_FILE" ]; then
    secret="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    sed "s/__SECRET_KEY__/$secret/" "$SCRIPT_DIR/settings.yml" > "$SETTINGS_FILE"
    chmod 600 "$SETTINGS_FILE"
    echo "Created $SETTINGS_FILE"
else
    echo "Keeping existing $SETTINGS_FILE"
fi

echo
echo "SearXNG is installed in $SEARXNG_HOME"
echo "Start it with run-searxng.bat (Windows) or scripts/searxng/run-searxng.sh (WSL)."
