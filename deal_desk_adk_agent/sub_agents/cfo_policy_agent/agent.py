"""ADK Agent Definition for the CFO Policy & SLA Governance Auditor."""

from __future__ import annotations

import inspect
from typing import Any

from google.adk.agents import Agent

try:
  from ... import config
  from ...tools.policy_rag_tool import search_cfo_governance_policies
except ImportError:
  import config  # type: ignore
  from tools.policy_rag_tool import search_cfo_governance_policies  # type: ignore

_AGENT_KWARGS: dict[str, Any] = {}
if "mode" in getattr(Agent, "model_fields", {}) or "mode" in inspect.signature(Agent.__init__).parameters:
  # ADK 2.x: single_turn mode allows root_agent to invoke sub-agents as tools
  # and receive their results back in the same turn while preserving the
  # visual sub_agents hierarchy in ADK Web UI
  _AGENT_KWARGS["mode"] = "single_turn"

cfo_policy_agent = Agent(
    name="cfo_policy_agent",
    model=config.GEMINI_MODEL,
    description=(
        "CFO Governance, Discount Matrix & SLA Compliance Agent. Queries "
        "Vertex AI Search (`search_cfo_governance_policies`) over official CFO "
        "policy PDFs to audit compliance and required sign-offs."
    ),
    instruction=f"""You are the Chief Financial Officer (CFO) Policy & SLA Governance Agent.
Your job is to audit B2B deal proposals against our official corporate governance policies indexed in Vertex AI Search Engine (`{config.SEARCH_ENGINE_ID}` in `{config.SEARCH_LOCATION}`).

CRITICAL RULES:
1. ALWAYS call `search_cfo_governance_policies` to retrieve official rules covering:
   - Discount approval thresholds (`Global_Discount_Approval_Matrix_2026.pdf`)
   - Competitor displacement rules (`Competitor_Displacement_Playbook.pdf` — remember: NEVER use real company names, only `CloudCorp_Global`, `Apex_Systems`, `Local_Legacy`, or `None`)
   - Custom SLA eligibility & minimum SGD deal value thresholds (`Enterprise_SLA_Governance_Rules.pdf`)
2. Provide a rigorous CFO Governance Assessment citing the specific policy documents:
   - **Discount Governance Audit**: Is the proposed discount within auto-approval limits, or does it require VP Sales / CFO Committee escalation?
   - **Competitor Displacement Eligibility**: Does the competitor (`CloudCorp_Global`, `Apex_Systems`, `Local_Legacy`, `None`) qualify for displacement buffer discounts?
   - **Custom SLA Compliance**: If `custom_sla_requested=1`, verify whether `deal_value_sgd` meets the mandatory SGD 1,500,000 minimum threshold and whether the customer segment (`Enterprise` vs `Mid_Market`/`SMB`) is permitted to request custom SLAs.
   - **Policy Citations**: Explicitly list the PDF document titles and page numbers retrieved from Vertex AI Search.
""",
    tools=[search_cfo_governance_policies],
    **_AGENT_KWARGS,
)
