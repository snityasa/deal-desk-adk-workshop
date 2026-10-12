"""FastAPI Server Entrypoint for Autonomous B2B Deal Desk ADK Multi-Agent.

Serves:
1. Interactive Google ADK Web UI (`/`) for browser testing locally or via `gcloud run services proxy`.
2. Dynamic A2A (Agent-to-Agent) Protocol endpoints (`/a2a/deal_desk_adk_agent` and
   `/a2a/deal_desk_adk_agent/.well-known/agent-card.json`) with automatic Cloud Run
   HTTPS URL resolution for Gemini Enterprise registration (`agents-cli publish gemini-enterprise`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types
import uvicorn

import sys

# Point directly to the `deal_desk_adk_agent` package directory so ADK
# treats it as a single-agent app (`list_agents()` -> `['deal_desk_adk_agent']`)
_CURRENT_DIR = Path(__file__).resolve().parent
if str(_CURRENT_DIR.parent) not in sys.path:
  sys.path.insert(0, str(_CURRENT_DIR.parent))

try:
  from deal_desk_adk_agent import agent as deal_desk_agent
  from deal_desk_adk_agent import config
except ImportError:
  try:
    from . import agent as deal_desk_agent
    from . import config
  except ImportError:
    import agent as deal_desk_agent  # type: ignore
    import config  # type: ignore

# Check if a2a-sdk is installed in the current environment
try:
  import a2a  # noqa: F401
  _HAS_A2A_SDK = True
except ImportError:
  _HAS_A2A_SDK = False

# Build the ADK FastAPI application with Web UI, A2A, and allow_origins=["*"]
# so Cloudtop web proxies and Cloud Run tunnels can POST to create sessions.
app: FastAPI = get_fast_api_app(
    agents_dir=str(_CURRENT_DIR),
    web=True,
    a2a=_HAS_A2A_SDK,
    allow_origins=["*"],
    session_service_uri="memory://",
)

app.title = "Autonomous B2B Deal Desk & Margin Optimizer (ADK Multi-Agent)"
app.description = (
    f"Executive C-Level ADK Multi-Agent ({config.GEMINI_MODEL}) orchestrating "
    f"CRO Quantitative Pricing ({config.VERTEX_ENDPOINT_ID}) & CFO Policy RAG ({config.SEARCH_ENGINE_ID})"
)


def _load_dynamic_agent_card(request: Request, agent_slug: str = "deal_desk_adk_agent") -> dict[str, Any]:
  """Loads agent.json and dynamically sets the public/proxy Cloud Run HTTPS RPC URL."""
  card_path = _CURRENT_DIR / "agent.json"
  with card_path.open("r", encoding="utf-8") as f:
    card_data = json.load(f)

  # Determine base URL from APP_URL env var or Cloud Run X-Forwarded / Host headers
  app_url = os.environ.get("APP_URL", "").strip().rstrip("/")
  if not app_url:
    default_proto = "https" if os.environ.get("K_SERVICE") else (request.url.scheme or "http")
    proto = request.headers.get("x-forwarded-proto", default_proto)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    app_url = f"{proto}://{host}".rstrip("/")

  card_data["url"] = f"{app_url}/a2a/{agent_slug}"
  return card_data


@app.middleware("http")
async def dynamic_a2a_agent_card_middleware(request: Request, call_next: Any) -> Any:
  """Intercepts A2A AgentCard discovery and /healthz before mounted sub-apps."""
  path = request.url.path.rstrip("/")
  if request.method == "GET" and path == "/healthz":
    return JSONResponse(content={
        "status": "ok",
        "service": "deal-desk-adk-ui",
        "project_id": config.PROJECT_ID,
        "region": config.REGION,
        "model": config.GEMINI_MODEL,
        "endpoint_id": config.VERTEX_ENDPOINT_ID,
        "search_engine_id": config.SEARCH_ENGINE_ID,
        "a2a_sdk_enabled": str(_HAS_A2A_SDK),
    })
  if request.method == "GET" and (
      path.endswith("/.well-known/agent-card.json")
      or path.endswith("/.well-known/agent.json")
  ):
    slug = "app" if "/a2a/app/" in path else "deal_desk_adk_agent"
    return JSONResponse(content=_load_dynamic_agent_card(request, slug))
  return await call_next(request)


@app.get("/healthz", tags=["Health"])
async def healthz() -> dict[str, str]:
  """Health check endpoint for Cloud Run."""
  return {
      "status": "ok",
      "service": "deal-desk-adk-ui",
      "project_id": config.PROJECT_ID,
      "region": config.REGION,
      "model": config.GEMINI_MODEL,
      "endpoint_id": config.VERTEX_ENDPOINT_ID,
      "search_engine_id": config.SEARCH_ENGINE_ID,
      "a2a_sdk_enabled": str(_HAS_A2A_SDK),
  }


# Dynamic A2A AgentCard routes supporting both /a2a/deal_desk_adk_agent and /a2a/app
@app.get("/a2a/deal_desk_adk_agent/.well-known/agent-card.json", include_in_schema=False)
@app.get("/a2a/deal_desk_adk_agent/.well-known/agent.json", include_in_schema=False)
async def dynamic_agent_card_primary(request: Request) -> JSONResponse:
  return JSONResponse(content=_load_dynamic_agent_card(request, "deal_desk_adk_agent"))


@app.get("/a2a/app/.well-known/agent-card.json", include_in_schema=False)
@app.get("/a2a/app/.well-known/agent.json", include_in_schema=False)
async def dynamic_agent_card_alias(request: Request) -> JSONResponse:
  return JSONResponse(content=_load_dynamic_agent_card(request, "app"))


# Provide built-in JSON-RPC A2A endpoint fallback if a2a-sdk wasn't mounted by get_fast_api_app
if not _HAS_A2A_SDK:
  _fallback_runner = InMemoryRunner(
      agent=deal_desk_agent.root_agent, app_name="deal_desk_adk_agent"
  )

  @app.post("/a2a/{agent_slug}", include_in_schema=False)
  async def fallback_a2a_jsonrpc(agent_slug: str, request: Request) -> JSONResponse:
    body = await request.json()
    rpc_id = body.get("id", str(uuid.uuid4()))
    params = body.get("params", {})
    message = params.get("message", {})
    parts = message.get("parts", [])
    user_text = " ".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if not user_text:
      user_text = str(params)

    session_id = params.get("id") or str(uuid.uuid4())
    user_id = "gemini-enterprise-user"
    await _fallback_runner.session_service.create_session(
        app_name="deal_desk_adk_agent", user_id=user_id, session_id=session_id
    )
    content = genai_types.Content(
        role="user", parts=[genai_types.Part.from_text(text=user_text)]
    )
    response_text = ""
    async for event in _fallback_runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
      if event.content and event.content.parts:
        for part in event.content.parts:
          if part.text:
            response_text += part.text

    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "id": session_id,
                "status": {"state": "completed"},
                "artifacts": [
                    {
                        "parts": [{"type": "text", "text": response_text}],
                    }
                ],
            },
        }
    )


if __name__ == "__main__":
  port = int(os.environ.get("PORT", "8081"))
  uvicorn.run(app, host="0.0.0.0", port=port)
