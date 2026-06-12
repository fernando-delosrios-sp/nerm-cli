#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR/app"

export NERM_TRANSPORT="${NERM_TRANSPORT:-streamable-http}"
export NERM_HTTP_HOST="${NERM_HTTP_HOST:-127.0.0.1}"
export NERM_HTTP_PORT="${NERM_HTTP_PORT:-8080}"

exec python -m main "$@"
