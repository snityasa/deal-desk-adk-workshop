"""Partner Configuration Loader for the Deal Desk ADK Multi-Agent System.

Loads environment variables from `os.environ` (Cloud Run / container overrides)
with automatic fallback to `deal_desk_adk_agent/.env`.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load .env from the agent directory without overriding active container env vars
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# ==============================================================================
# Partner Configurable Environment Variables
# ==============================================================================
def _resolve_project_id() -> str:
  """Resolves active GCP Project ID from env, Cloud Shell, or gcloud config."""
  for env_key in ("PROJECT_ID", "DEVSHELL_PROJECT_ID", "GOOGLE_CLOUD_PROJECT"):
    val = (os.environ.get(env_key) or "").strip()
    if val and val != "YOUR_GCP_PROJECT_ID":
      return val
  try:
    out = subprocess.check_output(
        ["gcloud", "config", "get-value", "project", "--quiet"],
        text=True,
        stderr=subprocess.DEVNULL,
        timeout=5,
    ).strip()
    if out and out != "(unset)":
      return out
  except Exception:  # pylint: disable=broad-exception-caught
    pass
  return "sekar-demo"


PROJECT_ID: str = _resolve_project_id()
REGION: str = os.environ.get("REGION", "northamerica-northeast2")
_RAW_ENDPOINT_ID: str = (
    os.environ.get("VERTEX_ENDPOINT_ID")
    or os.environ.get("VERTEX_L4_ENDPOINT_ID")
    or ""
).strip()
VERTEX_ENDPOINT_ID: str = (
    _RAW_ENDPOINT_ID
    if (_RAW_ENDPOINT_ID and _RAW_ENDPOINT_ID != "YOUR_VERTEX_ENDPOINT_ID")
    else "4858295481421266944"
)
# Backwards-compatible alias
VERTEX_L4_ENDPOINT_ID: str = VERTEX_ENDPOINT_ID

SEARCH_ENGINE_ID: str = os.environ.get(
    "SEARCH_ENGINE_ID", "deal-desk-cfo-search-engine"
)
SEARCH_LOCATION: str = os.environ.get("SEARCH_LOCATION", "global")

# Normalize 'gemini-3.1-pro' -> 'gemini-3.1-pro-preview' for Vertex AI compatibility
_RAW_GEMINI_MODEL: str = os.environ.get(
    "GEMINI_MODEL", "gemini-3.1-pro-preview"
).strip()
GEMINI_MODEL: str = (
    "gemini-3.1-pro-preview"
    if _RAW_GEMINI_MODEL in ("gemini-3.1-pro", "3.1-pro")
    else _RAW_GEMINI_MODEL
)

# Optional Step 6 Gemini Enterprise target app configuration
GEMINI_ENTERPRISE_APP_ID: str = os.environ.get("GEMINI_ENTERPRISE_APP_ID", "")
GEMINI_ENTERPRISE_LOCATION: str = os.environ.get(
    "GEMINI_ENTERPRISE_LOCATION", "global"
)


def _normalize_mcp_url(raw_url: str) -> str:
  """Normalizes a base Cloud Run URL to end with `/sse` if not already present."""
  cleaned = (raw_url or "").strip().strip('"').strip("'")
  if not cleaned or cleaned == "PASTE_YOUR_CLOUD_RUN_MCP_URL_HERE":
    return cleaned
  cleaned = cleaned.rstrip("/")
  if not cleaned.endswith("/sse"):
    cleaned = f"{cleaned}/sse"
  return cleaned


# Step 7: Remote Cloud Run MCP Server URL (auto-normalized to end with `/sse`)
MCP_SERVER_URL: str = _normalize_mcp_url(os.getenv("MCP_SERVER_URL", ""))

# Ensure Google GenAI / ADK SDK uses Vertex AI in the configured project
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")

# Fictional competitors enforced across all workshop artifacts
ALLOWED_COMPETITORS: tuple[str, ...] = (
    "CloudCorp_Global",
    "Apex_Systems",
    "Local_Legacy",
    "None",
)


def get_gcp_access_token() -> str | None:
  """Obtains a Google Cloud OAuth2 bearer token for Vertex AI & Discovery Engine REST calls.

  1. Tries Application Default Credentials (`google.auth.default`) with a short
     timeout so Cloud Run metadata server works in <50ms while local workstations
     without ADC do not hang.
  2. Falls back to `gcloud auth print-access-token --quiet` for local laptop execution.

  Returns:
      Bearer token string or None if unavailable.
  """
  try:
    import google.auth  # pylint: disable=g-import-not-at-top
    import google.auth.transport.requests  # pylint: disable=g-import-not-at-top

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    if credentials.token:
      return str(credentials.token).strip()
  except Exception:  # pylint: disable=broad-exception-caught
    pass

  try:
    env = os.environ.copy()
    env["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
    env["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "False"
    env["CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY"] = "False"
    env["CLOUDSDK_CONTEXT_AWARE_USE_MTLS_FOR_GRPC"] = "False"
    token = subprocess.check_output(
        ["gcloud", "auth", "print-access-token", "--quiet"],
        text=True,
        stderr=subprocess.DEVNULL,
        timeout=8,
        env=env,
    ).strip()
    if token:
      return token
  except Exception:  # pylint: disable=broad-exception-caught
    pass

  return None


def get_mcp_auth_headers(mcp_url: str) -> dict[str, str]:
  """Generates a Google Cloud Identity Token (`Authorization: Bearer <ID_TOKEN>`) for Cloud Run MCP calls.

  Supports both Cloud Run service account runtime (via metadata server / google-auth)
  and local workshop testing (`bash run_local_adk_ui.sh`) when Cloud Run requires
  IAM authentication (`--no-allow-unauthenticated`).

  Args:
      mcp_url: The target Cloud Run MCP Server URL (with or without `/sse`).

  Returns:
      A dictionary containing `{"Authorization": "Bearer <ID_TOKEN>"}` or `{}` if
      unauthenticated/local.
  """
  cleaned = (mcp_url or "").strip()
  if (
      not cleaned
      or cleaned == "PASTE_YOUR_CLOUD_RUN_MCP_URL_HERE"
      or "localhost" in cleaned
      or "127.0.0.1" in cleaned
  ):
    return {}

  parsed = urlparse(cleaned)
  target_audience = (
      f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else cleaned
  )

  # 1. Try google.oauth2.id_token (Cloud Run metadata server / service account credentials)
  try:
    import google.auth.transport.requests  # pylint: disable=g-import-not-at-top
    from google.oauth2 import id_token  # pylint: disable=g-import-not-at-top

    auth_req = google.auth.transport.requests.Request()
    token = id_token.fetch_id_token(auth_req, target_audience)
    if token:
      return {"Authorization": f"Bearer {token.strip()}"}
  except Exception:  # pylint: disable=broad-exception-caught
    pass

  # 2. Try ADC user credentials id_token if present
  try:
    import google.auth  # pylint: disable=g-import-not-at-top
    import google.auth.transport.requests  # pylint: disable=g-import-not-at-top

    credentials, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    adc_id_token = getattr(credentials, "id_token", None)
    if adc_id_token and isinstance(adc_id_token, str):
      return {"Authorization": f"Bearer {adc_id_token.strip()}"}
  except Exception:  # pylint: disable=broad-exception-caught
    pass

  # 3. Fallback to gcloud CLI identity token for local developer laptops
  env = os.environ.copy()
  env["CLOUDSDK_CORE_DISABLE_PROMPTS"] = "1"
  env["CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE"] = "False"
  env["CLOUDSDK_CONTEXT_AWARE_USE_ECP_HTTP_PROXY"] = "False"
  env["CLOUDSDK_CONTEXT_AWARE_USE_MTLS_FOR_GRPC"] = "False"

  for cmd in (
      ["gcloud", "auth", "print-identity-token", f"--audiences={target_audience}", "--quiet"],
      ["gcloud", "auth", "print-identity-token", "--quiet"],
  ):
    try:
      token = subprocess.check_output(
          cmd,
          text=True,
          stderr=subprocess.DEVNULL,
          timeout=8,
          env=env,
      ).strip()
      if token:
        return {"Authorization": f"Bearer {token}"}
    except Exception:  # pylint: disable=broad-exception-caught
      continue

  return {}
