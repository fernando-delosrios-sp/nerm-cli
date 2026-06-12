#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_DIR="${PROJECT_ROOT}/app/Default"
VENV_DIR="${APP_DIR}/.venv"

# Load local env vars if present.
if [[ -f "${APP_DIR}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${APP_DIR}/.env"
fi

# Create/activate app-local virtual environment.
if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi
if [[ -f "${VENV_DIR}/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
fi

# Ensure runtime dependencies are installed in this venv.
if ! python3 -c "import strands" >/dev/null 2>&1; then
  echo "Installing nermTestAgent dependencies into ${VENV_DIR} ..."
  if command -v uv >/dev/null 2>&1; then
    (cd "${APP_DIR}" && uv sync)
  else
    python3 -m pip install --upgrade pip
    python3 -m pip install -e "${APP_DIR}"
  fi
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
exec python3 "${APP_DIR}/main.py"
