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
    instruction="""You are the Chief Financial Officer (CFO) Policy & SLA Governance Auditor.
Your job is to check B2B deal proposals against official corporate governance policies using the `search_cfo_governance_policies` tool.

CRITICAL RULES:
1. ALWAYS call `search_cfo_governance_policies` to retrieve official rules covering:
   - Discount approval thresholds (`Global_Discount_Approval_Matrix_2026.pdf`)
   - Competitor displacement rules (`Competitor_Displacement_Playbook.pdf` — NEVER use real company names, only `CloudCorp_Global`, `Apex_Systems`, `Local_Legacy`, or `None`)
   - Custom SLA eligibility & minimum SGD deal value thresholds (`Enterprise_SLA_Governance_Rules.pdf`)
2. NEVER mention infrastructure, search engine IDs, regions, or cloud deployment details.
3. Return ONLY a brief, factual 4-bullet summary (1 short sentence per bullet, no intro/outro paragraphs):
   - **Discount Rule**: Pass or escalation required, plus any combined SLA margin reserve rule (*Global_Discount_Approval_Matrix_2026.pdf*).
   - **Competitor Rule**: Whether the competitor qualifies for displacement fast-track (*Competitor_Displacement_Playbook.pdf*).
   - **SLA Rule**: Whether the segment and deal value meet Custom SLA thresholds (*Enterprise_SLA_Governance_Rules.pdf*).
   - **Required Sign-Off**: Exact approver required (`Auto-Approve`, `VP of Sales`, or `CFO Deal Desk Committee`).
""",
    tools=[search_cfo_governance_policies],
    **_AGENT_KWARGS,
)
