"""Cloud Run Remote MCP Server: Deal Desk Decisions Ledger Database.

Exposes an MCP Server over SSE (`/sse` and `/messages/`) plus a `/health` GET
endpoint on `0.0.0.0:${PORT:-8080}`.

Provides the `insert_deal_decision_to_db` tool used in the Executive AI Workshop
hands-on exercise to record B2B Deal Desk decisions and return an official
approval ticket ID (`DD-2026-XXXXX`) and ledger transaction hash.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import inspect
import json
import logging
import os
import random
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

try:
  from mcp.server.fastmcp import FastMCP
except ImportError:
  from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore

try:
  from mcp.server.transport_security import TransportSecuritySettings
except ImportError:
  TransportSecuritySettings = None  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("deal-desk-mcp-server")

PORT = int(os.environ.get("PORT", "8080"))

# Disable localhost-only DNS rebinding restrictions so Cloud Run (*.run.app) Host headers work
_SECURITY_SETTINGS = (
    TransportSecuritySettings(enable_dns_rebinding_protection=False)
    if TransportSecuritySettings is not None
    else None
)

_INIT_PARAMS = inspect.signature(FastMCP.__init__).parameters
_MCP_KWARGS: dict[str, Any] = {}
if "host" in _INIT_PARAMS:
  _MCP_KWARGS["host"] = "0.0.0.0"
if "port" in _INIT_PARAMS:
  _MCP_KWARGS["port"] = PORT
if "transport_security" in _INIT_PARAMS and _SECURITY_SETTINGS is not None:
  _MCP_KWARGS["transport_security"] = _SECURITY_SETTINGS

mcp = FastMCP("deal-desk-db-mcp-server", **_MCP_KWARGS)


@mcp.tool()
def insert_deal_decision_to_db(
    customer_segment: str,
    deal_value_sgd: float,
    proposed_discount_pct: float,
    contract_term_months: int,
    competitor: str,
    decision_status: str,
    required_approver: str,
    win_probability_pct: float,
) -> dict[str, Any]:
  """Inserts a finalized B2B Deal Desk decision record into the Enterprise Deal Decisions Ledger database.

  Args:
      customer_segment: Customer segment tier ('Enterprise', 'Mid_Market', or 'SMB').
      deal_value_sgd: Total Contract Value (TCV) in Singapore Dollars (SGD).
      proposed_discount_pct: Proposed discount percentage evaluated by Deal Desk.
      contract_term_months: Contract term in months (e.g., 12, 24, 36).
      competitor: Fictional competitor name ('CloudCorp_Global', 'Apex_Systems', 'Local_Legacy', or 'None').
      decision_status: Final executive decision status (e.g., 'APPROVED',
          'CONDITIONAL_APPROVAL_REQUIRED', 'REJECTED_RESTRUCTURE_REQUIRED').
      required_approver: Required sign-off authority (e.g., 'Auto-Approve',
          'VP of Sales', or 'CFO Deal Desk Committee').
      win_probability_pct: Predicted win probability percentage (e.g., 78.4 for 78.4%).

  Returns:
      A dictionary confirming the database insert (`status: "OK"`), including
      `deal_approval_ticket_id` (`DD-2026-XXXXX`), `transaction_id`, `committed_at_utc`,
      and `record_summary`.
  """
  committed_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
  ticket_number = random.randint(10000, 99999)
  deal_approval_ticket_id = f"DD-2026-{ticket_number}"

  hash_seed = (
      f"{customer_segment}:{deal_value_sgd}:{proposed_discount_pct}:"
      f"{contract_term_months}:{competitor}:{decision_status}:"
      f"{committed_at_utc}:{ticket_number}"
  )
  tx_hex = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:8].upper()
  transaction_id = f"TXN-{tx_hex}"

  record_summary = {
      "customer_segment": str(customer_segment),
      "deal_value_sgd": round(float(deal_value_sgd), 2),
      "proposed_discount_pct": round(float(proposed_discount_pct), 2),
      "contract_term_months": int(contract_term_months),
      "competitor": str(competitor),
      "decision_status": str(decision_status),
      "required_approver": str(required_approver),
      "win_probability_pct": round(float(win_probability_pct), 2),
  }

  receipt = {
      "status": "OK",
      "db_operation": "INSERT_COMMITTED",
      "table": "enterprise_deal_desk.deal_decisions_ledger",
      "deal_approval_ticket_id": deal_approval_ticket_id,
      "transaction_id": transaction_id,
      "committed_at_utc": committed_at_utc,
      "record_summary": record_summary,
  }

  logger.info(
      "MCP Tool [insert_deal_decision_to_db] committed record: %s",
      json.dumps(receipt),
  )
  return receipt


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
  """Cloud Run health check endpoint."""
  return JSONResponse({
      "status": "OK",
      "service": "deal-desk-mcp-server",
      "transport": "sse",
      "sse_endpoint": "/sse",
      "messages_endpoint": "/messages/",
      "tools": ["insert_deal_decision_to_db"],
  })


@mcp.custom_route("/", methods=["GET"])
async def root_info(_request: Request) -> JSONResponse:
  """Root informational endpoint when visiting the Cloud Run URL in a browser."""
  return JSONResponse({
      "status": "OK",
      "service": "deal-desk-mcp-server",
      "description": "Executive AI Workshop — Deal Desk Decisions Ledger MCP Server",
      "sse_endpoint": "/sse",
      "health_endpoint": "/health",
      "tools": ["insert_deal_decision_to_db"],
  })


def create_app() -> Any:
  """Creates the ASGI application serving `/sse`, `/messages/`, and `/health`."""
  sse_params = inspect.signature(mcp.sse_app).parameters
  sse_kwargs: dict[str, Any] = {}
  if "host" in sse_params:
    sse_kwargs["host"] = "0.0.0.0"
  if "transport_security" in sse_params and _SECURITY_SETTINGS is not None:
    sse_kwargs["transport_security"] = _SECURITY_SETTINGS
  return mcp.sse_app(**sse_kwargs)


app = create_app()

if __name__ == "__main__":
  logger.info(
      "Starting Deal Desk Cloud Run MCP Server on 0.0.0.0:%s (SSE: /sse, Health: /health)",
      PORT,
  )
  uvicorn.run(app, host="0.0.0.0", port=PORT)
