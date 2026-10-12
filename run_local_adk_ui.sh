#!/usr/bin/env bash
# ==============================================================================
# Partner Local Launcher: Autonomous B2B Deal Desk ADK Multi-Agent Web UI
# Runs natively on macOS, Linux, or Windows WSL laptops on Port 8081 or 8082.
# ==============================================================================
set -euo pipefail

# Prevent 80+ second mTLS / Enterprise Certificate Proxy (ECP) stalls when running
# with non-corp / demo Cloud Identity accounts
export CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=False

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="${SCRIPT_DIR}/deal_desk_adk_agent"
ENV_FILE="${AGENT_DIR}/.env"

# 1. Load Partner Configuration from deal_desk_adk_agent/.env
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

# 2. Select Port 8081 (or fallback to 8082 if 8081 is in use)
PORT=$(python3 -c "
import os, socket
preferred = [int(os.environ['PORT'])] if 'PORT' in os.environ else [8081, 8082]
selected = preferred[0]
for p in preferred:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', p))
            selected = p
            break
    except OSError:
        continue
print(selected)
")
export PORT

export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"
export ADK_DISABLE_LOCAL_STORAGE=1

echo "=============================================================================="
echo "  STARTING LOCAL ADK MULTI-AGENT WEB UI (deal_desk_adk_agent)"
echo "=============================================================================="
echo "  Project ID       : ${PROJECT_ID:-sekar-demo}"
echo "  Gemini Model     : ${GEMINI_MODEL:-gemini-3.1-pro-preview}"
echo "  Pricing Endpoint : ${VERTEX_ENDPOINT_ID:-${VERTEX_L4_ENDPOINT_ID:-4858295481421266944}} (${REGION:-northamerica-northeast2})"
echo "  CFO Policy Search: ${SEARCH_ENGINE_ID:-deal-desk-cfo-search-engine} (${SEARCH_LOCATION:-global})"
echo "  MCP Server URL   : ${MCP_SERVER_URL:-Not configured}"
echo "  Simulation Port  : ${PORT} (Port 8081/8082 standard)"
echo ""
echo "  >>> OPEN IN YOUR BROWSER:"
echo "      http://localhost:${PORT}"
echo "=============================================================================="
echo ""

# 3. Check Application Default Credentials (ADC)
if command -v gcloud >/dev/null 2>&1; then
  if ! gcloud auth application-default print-access-token --quiet >/dev/null 2>&1; then
    echo "  [NOTE] Application Default Credentials (ADC) not detected or expired."
    echo "         For live Vertex AI & Gemini 3.1 Pro calls, run in your terminal:"
    echo "           gcloud auth application-default login"
    echo "         (Simulation fallback mode is active until authenticated)."
    echo ""
  fi
fi

# 4. Resolve Python Interpreter (Portable across Partner Laptops & Environments)
check_python_deps() {
  local py_bin="$1"
  "${py_bin}" -c "import google.adk, fastapi, uvicorn, requests, dotenv, mcp" >/dev/null 2>&1
}

PYTHON_BIN=""

# Option A: Check local .venv in project folder first
if [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]] && check_python_deps "${SCRIPT_DIR}/.venv/bin/python"; then
  PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"
# Option B: Check active python3
elif command -v python3 >/dev/null 2>&1 && check_python_deps "python3"; then
  PYTHON_BIN="python3"
# Option C: Check uv tool google-adk python (if uv tools are installed)
elif [[ -x "${HOME}/.local/share/uv/tools/google-adk/bin/python" ]] && check_python_deps "${HOME}/.local/share/uv/tools/google-adk/bin/python"; then
  PYTHON_BIN="${HOME}/.local/share/uv/tools/google-adk/bin/python"
else
  # Option D: Automatically bootstrap a clean local .venv on the partner's laptop
  echo "  [SETUP] Installing ADK & MCP dependencies into local .venv (${SCRIPT_DIR}/.venv)..."
  if command -v uv >/dev/null 2>&1; then
    uv venv "${SCRIPT_DIR}/.venv"
    uv pip install --default-index https://pypi.org/simple --python "${SCRIPT_DIR}/.venv/bin/python" -r "${AGENT_DIR}/requirements.txt"
  else
    python3 -m venv "${SCRIPT_DIR}/.venv"
    "${SCRIPT_DIR}/.venv/bin/pip" install --upgrade pip
    "${SCRIPT_DIR}/.venv/bin/pip" install -r "${AGENT_DIR}/requirements.txt"
  fi
  PYTHON_BIN="${SCRIPT_DIR}/.venv/bin/python"
fi

exec "${PYTHON_BIN}" "${AGENT_DIR}/server.py"
