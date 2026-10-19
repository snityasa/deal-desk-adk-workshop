"""Partner Configuration Loader for the Deal Desk ADK Multi-Agent System.

Loads environment variables from `os.environ` (Cloud Run / container overrides)
with automatic fallback to `deal_desk_adk_agent/.env`.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any
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


# ==============================================================================
# Structured Cloud Logging & Local Console Telemetry (`deal-desk-agent-telemetry`)
# ==============================================================================
CLOUD_LOGGING_LOG_ID: str = os.environ.get(
    "CLOUD_LOGGING_LOG_ID", "deal-desk-agent-telemetry"
)


def _ship_to_cloud_logging_async(
    entry_payload: dict[str, Any],
    severity: str,
    labels: dict[str, str],
) -> None:
  """Ships structured telemetry directly to Cloud Logging REST API when running locally."""
  import threading  # pylint: disable=g-import-not-at-top
  import requests  # pylint: disable=g-import-not-at-top

  def _worker() -> None:
    try:
      if not PROJECT_ID or PROJECT_ID == "YOUR_GCP_PROJECT_ID":
        return
      token = get_gcp_access_token()
      if not token:
        return
      url = "https://logging.googleapis.com/v2/entries:write"
      body = {
          "logName": f"projects/{PROJECT_ID}/logs/{CLOUD_LOGGING_LOG_ID}",
          "resource": {
              "type": "global",
              "labels": {"project_id": PROJECT_ID},
          },
          "labels": labels,
          "entries": [
              {
                  "severity": severity,
                  "jsonPayload": entry_payload,
              }
          ],
      }
      requests.post(
          url,
          headers={
              "Authorization": f"Bearer {token}",
              "Content-Type": "application/json",
              "X-Goog-User-Project": PROJECT_ID,
          },
          json=body,
          timeout=4,
      )
    except Exception:  # pylint: disable=broad-exception-caught
      pass

  threading.Thread(target=_worker, daemon=True).start()


def log_telemetry(
    component: str,
    event_type: str,
    message: str,
    *,
    severity: str = "INFO",
    execution_mode: str = "LIVE",
    details: dict[str, Any] | None = None,
) -> None:
  """Emits structured telemetry to stdout (Cloud Run jsonPayload) and Cloud Logging API.

  In Google Cloud Console -> Logs Explorer, filter by:
    `jsonPayload.log_source="deal-desk-agent-telemetry"`
  or:
    `logName:"deal-desk-agent-telemetry"`
  """
  from datetime import datetime, timezone  # pylint: disable=g-import-not-at-top
  import json  # pylint: disable=g-import-not-at-top

  clean_severity = severity.upper().strip()
  runtime_env = "CLOUD_RUN" if os.environ.get("K_SERVICE") else "LOCAL_WORKSTATION"
  labels = {
      "app": "deal-desk-adk-agent",
      "component": str(component),
      "event_type": str(event_type),
      "execution_mode": str(execution_mode),
      "runtime_env": runtime_env,
  }

  payload: dict[str, Any] = {
      "severity": clean_severity,
      "message": f"[DEAL_DESK_TELEMETRY] [{component}] [{event_type}] ({execution_mode}) {message}",
      "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
      "log_source": CLOUD_LOGGING_LOG_ID,
      "runtime_env": runtime_env,
      "project_id": PROJECT_ID,
      "region": REGION,
      "component": component,
      "event_type": event_type,
      "execution_mode": execution_mode,
      "logging.googleapis.com/labels": labels,
  }
  if details:
    payload.update(details)

  # 1. Print single-line JSON to stdout (auto-ingested as jsonPayload on Cloud Run
  #    and immediately visible in local terminal logs)
  try:
    print(json.dumps(payload, default=str), flush=True)
  except Exception:  # pylint: disable=broad-exception-caught
    pass

  # 2. Always write to dedicated `deal-desk-agent-telemetry` log stream via Cloud Logging
  #    REST API so both local runs and Cloud Run runs can be queried with a single filter!
  _ship_to_cloud_logging_async(payload, clean_severity, labels)


def configure_agent_telemetry(root_agent: Any, *sub_agents: Any) -> None:
  """Attaches single-turn duplicate-bubble suppression and Cloud Logging telemetry callbacks."""
  # 1. Suppress duplicate sub-agent prose bubbles in ADK 2.x single_turn mode
  try:
    from google.adk.workflow._node_runner import NodeRunner  # pylint: disable=g-import-not-at-top

    if not getattr(NodeRunner, "_deal_desk_quiet_subagents", False):
      orig_enqueue_event = NodeRunner._enqueue_event

      async def _quiet_subagent_enqueue(self, event, ctx):  # type: ignore
        node = getattr(self, "_node", None)
        if (
            getattr(node, "parent_agent", None) is not None
            and getattr(node, "mode", None) == "single_turn"
            and event.content
            and event.content.role == "model"
            and not event.get_function_calls()
            and not event.get_function_responses()
        ):
          if not event.partial:
            self._flush_deltas(event, ctx)
          if event.output is not None:
            ctx._output_emitted = True
          if event.node_info and event.node_info.message_as_output:
            ctx._output_delegated = True
          return
        await orig_enqueue_event(self, event, ctx)

      NodeRunner._enqueue_event = _quiet_subagent_enqueue  # type: ignore
      NodeRunner._deal_desk_quiet_subagents = True  # type: ignore
  except Exception:  # pylint: disable=broad-exception-caught
    pass

  # 2. Define Cloud Logging callbacks for Logs Explorer observability
  def _on_before_agent(callback_context):  # type: ignore
    try:
      inv_ctx = getattr(callback_context, "_invocation_context", None)
      session = getattr(inv_ctx, "session", None)
      has_mcp = any(
          "McpToolset" in type(t).__name__
          or "insert_deal_decision" in getattr(t, "name", "")
          for t in getattr(root_agent, "tools", [])
      )
      log_telemetry(
          component="deal_desk_orchestrator",
          event_type="AGENT_TURN_START",
          message=(
              f"Starting orchestrator turn | model={GEMINI_MODEL} "
              f"mcp_connected={has_mcp} session_id={getattr(session, 'id', 'N/A')}"
          ),
          severity="INFO",
          execution_mode="MCP_ENABLED" if has_mcp else "PRE_MCP_MODE",
          details={
              "agent_name": getattr(
                  root_agent, "name", "deal_desk_executive_orchestrator"
              ),
              "model": GEMINI_MODEL,
              "mcp_tool_connected": has_mcp,
              "mcp_server_url": MCP_SERVER_URL or "NOT_CONFIGURED",
              "session_id": getattr(session, "id", None),
              "invocation_id": getattr(inv_ctx, "invocation_id", None),
          },
      )
    except Exception:  # pylint: disable=broad-exception-caught
      pass
    return None

  def _on_after_tool(tool, args, tool_context, tool_response):  # type: ignore
    try:
      tool_name = getattr(tool, "name", str(tool))
      is_mcp = "insert_deal_decision" in tool_name
      mode = "LIVE_CLOUD_RUN_MCP" if is_mcp else "SUB_AGENT_DELEGATION"
      ticket_id = (
          tool_response.get("deal_approval_ticket_id")
          if isinstance(tool_response, dict)
          else None
      )
      tx_id = (
          tool_response.get("transaction_id")
          if isinstance(tool_response, dict)
          else None
      )
      log_telemetry(
          component="deal_desk_orchestrator",
          event_type="MCP_TOOL_RESULT" if is_mcp else "SUB_AGENT_RESULT",
          message=(
              f"Tool [{tool_name}] completed"
              + (f" | ticket={ticket_id} tx={tx_id}" if ticket_id else "")
          ),
          severity="INFO",
          execution_mode=mode,
          details={
              "tool_name": tool_name,
              "is_mcp_tool": is_mcp,
              "tool_args": args,
              "deal_approval_ticket_id": ticket_id,
              "transaction_id": tx_id,
              "tool_response_preview": str(tool_response)[:500],
          },
      )
    except Exception:  # pylint: disable=broad-exception-caught
      pass
    return None

  def _on_after_model(callback_context, llm_response):  # type: ignore
    try:
      node = getattr(callback_context, "_node", None)
      agent_name = getattr(node, "name", None) or getattr(
          callback_context, "agent_name", "deal_desk_executive_orchestrator"
      )
      usage = getattr(llm_response, "usage_metadata", None)
      content = getattr(llm_response, "content", None)
      parts = getattr(content, "parts", None) or []
      fcs = [
          p.function_call.name
          for p in parts
          if getattr(p, "function_call", None) is not None
      ]
      texts = [
          p.text
          for p in parts
          if getattr(p, "text", None) and not getattr(p, "thought", False)
      ]
      log_telemetry(
          component=str(agent_name),
          event_type="GEMINI_LLM_RESPONSE",
          message=(
              f"Agent [{agent_name}] Gemini ({GEMINI_MODEL}) responded | "
              f"tool_calls={fcs or 'NONE'} "
              f"total_tokens={getattr(usage, 'total_token_count', 'N/A')}"
          ),
          severity="INFO",
          execution_mode="LIVE_GEMINI_VERTEX_AI",
          details={
              "agent_name": str(agent_name),
              "model": GEMINI_MODEL,
              "function_calls_requested": fcs,
              "prompt_token_count": getattr(usage, "prompt_token_count", None),
              "candidates_token_count": getattr(
                  usage, "candidates_token_count", None
              ),
              "total_token_count": getattr(usage, "total_token_count", None),
              "cached_content_token_count": getattr(
                  usage, "cached_content_token_count", None
              ),
              "response_text_preview": " ".join(texts)[:400] if texts else None,
          },
      )
    except Exception:  # pylint: disable=broad-exception-caught
      pass
    return None

  root_agent.before_agent_callback = _on_before_agent
  root_agent.after_tool_callback = _on_after_tool
  root_agent.after_model_callback = _on_after_model
  for sub_agent in sub_agents:
    sub_agent.after_model_callback = _on_after_model
