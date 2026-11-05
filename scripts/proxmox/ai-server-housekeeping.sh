#!/usr/bin/env bash
# Prune old lab build directories and build logs after a healthy start.
#
# Runs as the ai-server account (systemd user timer). It does nothing unless
# both application containers report healthy. It only considers entries named
# build-YYYYMMDD-<id> (directories) and build-YYYYMMDD-<id>.log (files) directly
# inside the application data root, never follows symlinks, always keeps the
# newest builds, and never touches deploy-backups, databases, logs, or images.
#
# Usage: ai-server-housekeeping.sh [--dry-run]
set -euo pipefail

ROOT="${AI_SERVER_HOUSEKEEPING_ROOT:-/var/lib/ai-server}"
MAX_AGE_DAYS="${AI_SERVER_HOUSEKEEPING_DAYS:-7}"
KEEP_NEWEST="${AI_SERVER_HOUSEKEEPING_KEEP:-1}"
DRY_RUN=0

case "${1:-}" in
  "") ;;
  --dry-run) DRY_RUN=1 ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 64 ;;
esac

[[ "$MAX_AGE_DAYS" =~ ^[0-9]+$ && "$KEEP_NEWEST" =~ ^[0-9]+$ ]] || {
  echo "housekeeping: age and keep settings must be non-negative integers" >&2
  exit 64
}
[ -d "$ROOT" ] || { echo "housekeeping: $ROOT is not a directory" >&2; exit 66; }

log() { echo "housekeeping: $*"; }

for container in ai-server-backend ai-server-dashboard; do
  state="$(podman inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null || true)"
  if [ "$state" != "healthy" ]; then
    log "skipped: $container is '${state:-absent}', not healthy"
    exit 0
  fi
done

name_pattern='^build-[0-9]{8}-[A-Za-z0-9._-]+(\.log)?$'
declare -A kept=()
kept_count=0
removed=0

# Newest first: release IDs start with a date, so reverse name order is newest first.
while IFS= read -r name; do
  [[ "$name" =~ $name_pattern ]] || continue
  base="${name%.log}"
  if [ -z "${kept[$base]+x}" ] && [ "$kept_count" -lt "$KEEP_NEWEST" ]; then
    kept[$base]=1
    kept_count=$((kept_count + 1))
  fi
  [ -n "${kept[$base]+x}" ] && continue
  if [ -z "$(find -P "$ROOT/$name" -maxdepth 0 -mtime "+$MAX_AGE_DAYS" -print 2>/dev/null)" ]; then
    continue
  fi
  if [ "$DRY_RUN" -eq 1 ]; then
    log "would remove $ROOT/$name"
  else
    rm -rf --one-file-system -- "${ROOT:?}/$name"
    log "removed $ROOT/$name"
  fi
  removed=$((removed + 1))
done < <(find -P "$ROOT" -mindepth 1 -maxdepth 1 \( -type d -o -type f \) -name 'build-*' -printf '%f\n' | sort -r)

log "done: ${removed} entr$([ "$removed" -eq 1 ] && echo y || echo ies) $([ "$DRY_RUN" -eq 1 ] && echo 'would be ')removed"
