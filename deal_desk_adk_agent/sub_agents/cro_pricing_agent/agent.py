"""ADK Agent Definition for the CRO Quantitative Pricing & Margin Optimizer."""

from __future__ import annotations

import inspect
from typing import Any

from google.adk.agents import Agent

try:
  from ... import config
  from ...tools.pricing_tool import predict_deal_win_probability
except ImportError:
  import config  # type: ignore
  from tools.pricing_tool import predict_deal_win_probability  # type: ignore

_AGENT_KWARGS: dict[str, Any] = {}
if "mode" in getattr(Agent, "model_fields", {}) or "mode" in inspect.signature(Agent.__init__).parameters:
  # ADK 2.x: single_turn mode allows root_agent to invoke sub-agents as tools
  # and receive their results back in the same turn while preserving the
  # visual sub_agents hierarchy in ADK Web UI
  _AGENT_KWARGS["mode"] = "single_turn"

cro_pricing_agent = Agent(
    name="cro_pricing_agent",
    model=config.GEMINI_MODEL,
    description=(
        "CRO Quantitative Pricing & Margin Optimizer Agent. Calls the live "
        "Vertex AI Online Prediction Endpoint (`predict_deal_win_probability`) to "
        "predict deal win probability, recommended max discount %, and margin policy."
    ),
    instruction="""You are the Chief Revenue Officer (CRO) Pricing & Margin Analyst.
Your job is to evaluate B2B deal proposals quantitatively using the `predict_deal_win_probability` tool.

CRITICAL RULES:
1. ALWAYS call `predict_deal_win_probability` with the exact deal parameters:
   - `customer_segment`: 'Enterprise', 'Mid_Market', or 'SMB'
   - `deal_value_sgd`: Total Contract Value in SGD (float)
   - `proposed_discount_pct`: Proposed discount percentage (float)
   - `contract_term_months`: Contract length in months (int, e.g. 12, 24, 36)
   - `competitor`: Fictional competitor name ONLY ('CloudCorp_Global', 'Apex_Systems', 'Local_Legacy', or 'None'). NEVER use real company names.
   - `custom_sla_requested`: 1 if custom SLA is requested, 0 otherwise.
2. NEVER mention infrastructure, deployment locations, regions, endpoint IDs, GPUs, or hardware in your response.
3. Return ONLY a concise 4-bullet summary for the Deal Desk Orchestrator (no intro/outro fluff):
   - **Win Probability**: `<X>%` (`Won` or `Lost`)
   - **Discount Benchmark**: `<Proposed>%` proposed vs. `<Recommended Max>%` recommended max
   - **Margin Policy**: `AUTO_APPROVE`, `VP_SALES_APPROVAL`, or `CFO_COMMITTEE_ESCALATION`
""",
    tools=[predict_deal_win_probability],
    **_AGENT_KWARGS,
)
