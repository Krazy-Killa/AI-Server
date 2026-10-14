#!/usr/bin/env bash
# Runs SearXNG from the install created by install-searxng.sh.
set -euo pipefail

SEARXNG_HOME="${SEARXNG_HOME:-$HOME/searxng}"
SEARXNG_PORT="${SEARXNG_PORT:-8888}"

if [ ! -x "$SEARXNG_HOME/venv/bin/granian" ]; then
    echo "SearXNG is not installed. Run scripts/searxng/install-searxng.sh first." >&2
    exit 1
fi

export SEARXNG_SETTINGS_PATH="$SEARXNG_HOME/settings.yml"
cd "$SEARXNG_HOME/src"
echo "SearXNG listening on http://127.0.0.1:$SEARXNG_PORT (Ctrl+C to stop)"
exec "$SEARXNG_HOME/venv/bin/granian" --interface wsgi \
    --host 127.0.0.1 --port "$SEARXNG_PORT" searx.webapp:app
