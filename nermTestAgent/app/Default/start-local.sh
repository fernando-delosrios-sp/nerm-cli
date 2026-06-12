#!/usr/bin/env bash
set -euo pipefail


# Load local env vars if present.
if [[ -f ".env" ]]; then
  # shellcheck disable=SC1091
  source ".env"
fi

# Activate virtual environment when available.
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

# Local defaults (override by exporting before running script).
export LOG_LEVEL=DEBUG
# "event" preserves structured/image blocks for chat clients that support MCP rendering.
export IMAGE_OUTPUT_MODE="${IMAGE_OUTPUT_MODE:-event}"
export MCP_PROFILE="${MCP_PROFILE:-local}"
export MCP_RECOVERY_RETRIES="${MCP_RECOVERY_RETRIES:-1}"
export MCP_ENDPOINT=http://127.0.0.1:8080/mcp
export MCP_TARGET_URL="${MCP_TARGET_URL:-}"
export MCP_AUTHORIZATION="${MCP_AUTHORIZATION:-}"

echo "Starting agent on 0.0.0.0:8085 (LOG_LEVEL=${LOG_LEVEL}, IMAGE_OUTPUT_MODE=${IMAGE_OUTPUT_MODE}, MCP_PROFILE=${MCP_PROFILE})"
exec python3 main.py
