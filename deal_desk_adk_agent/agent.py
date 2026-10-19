"""Google ADK Multi-Agent System: Autonomous B2B Deal Desk & Margin Optimizer.

Golden ADK Folder Structure:
- `agent.py`     : Root Orchestrator Agent (`root_agent` & `app`) + MCP Toolset wiring
- `sub_agents/`  : Specialist Sub-Agents delegated by the Root Orchestrator:
    - `cro_pricing_agent/` : Quantitative ML Pricing & Margin Optimizer
    - `cfo_policy_agent/`  : Qualitative CFO Governance & SLA Compliance Auditor
- `tools/`       : ADK FunctionTools invoked by the Sub-Agents:
    - `pricing_tool.py`    : `predict_deal_win_probability` (Vertex AI Online Prediction)
    - `policy_rag_tool.py` : `search_cfo_governance_policies` (Vertex AI Search RAG)
- `config.py`    : Environment Variables (`.env`) & GCP Authentication Helpers
- `server.py`    : FastAPI + ADK Web UI + Agent-to-Agent (A2A) Protocol Server
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.apps import App

# [WORKSHOP MCP STEP 1/3]: Uncomment the MCP imports below
# from google.adk.tools.mcp_tool import McpToolset
# from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams

try:
  from . import config
  from .sub_agents import cfo_policy_agent
  from .sub_agents import cro_pricing_agent
  from .tools import predict_deal_win_probability
  from .tools import search_cfo_governance_policies
except ImportError:
  import config  # type: ignore
  from sub_agents import cfo_policy_agent  # type: ignore
  from sub_agents import cro_pricing_agent  # type: ignore
  from tools import predict_deal_win_probability  # type: ignore
  from tools import search_cfo_governance_policies  # type: ignore


# ==============================================================================
# 1. DEAL DESK DATABASE MCP TOOLSET (CLOUD RUN REMOTE MCP SERVER)
# [WORKSHOP MCP STEP 2/3]: Uncomment below to connect to the Cloud Run MCP Server
# ==============================================================================
# deal_desk_db_mcp = McpToolset(
#     connection_params=SseConnectionParams(
#         url=config.MCP_SERVER_URL,
#         headers=config.get_mcp_auth_headers(config.MCP_SERVER_URL),
#     ),
# )


# ==============================================================================
# 2. ROOT EXECUTIVE ORCHESTRATOR AGENT (`deal_desk_executive_orchestrator`)
# ==============================================================================
root_agent = Agent(
    name="deal_desk_executive_orchestrator",
    model=config.GEMINI_MODEL,
    description=(
        "C-Level Deal Desk Executive Orchestrator. Coordinates the CRO Pricing "
        "Agent, CFO Policy Governance Agent, and Deal Desk Decisions Ledger "
        "to issue concise, binding B2B Deal Desk decisions."
    ),
    instruction="""You are the **Autonomous B2B Deal Desk Executive Orchestrator** (`deal_desk_executive_orchestrator`), advising Sales and Executive leadership on enterprise software deals.

### WORKFLOW 1: EVALUATING OR RE-EVALUATING A DEAL
When a user asks you to evaluate a B2B deal (or chooses **Option 1** to re-evaluate with modified terms such as removing the Custom SLA):
1. **Step 1 — Quantitative Pricing Check**: Call `cro_pricing_agent` with the deal parameters to get the win probability and recommended max discount.
2. **Step 2 — CFO Policy & SLA Check**: Call `cfo_policy_agent` to check the deal against official CFO governance policies.
3. Present your evaluation using this exact, concise template (under 150 words):

### Deal Desk Decision: `[APPROVED | CONDITIONAL_APPROVAL_REQUIRED | REJECTED_RESTRUCTURE_REQUIRED]`
- **Deal Summary**: `<Segment>` | `SGD <Value>` | `<Discount>%` Discount | `<Term>` Months | Competitor: `<Competitor>` | Custom SLA: `<Yes/No>`
- **Required Approver**: `<Auto-Approve | VP of Sales | CFO Deal Desk Committee>`

#### Key Findings
- **Pricing & Win Probability**: `<Win Probability>%` predicted win rate (`<Won/Lost>`); `<Proposed Discount>%` proposed discount vs. `<Recommended Max Discount>%` recommended ceiling.
- **Policy & Governance**: 1–2 short sentences stating why the deal passes or requires escalation (covering discount limits, competitor displacement eligibility, and custom SLA rules), citing the policy PDF filename(s) in parentheses.

#### Recommended Next Steps
1. **Option 1 (Fast-Track Restructuring)**: `<1-line adjustment to qualify for faster/auto-approval, e.g., Remove the Custom SLA requirement to clear the 3.0% margin reserve and qualify for Auto-Approve>`
2. **Option 2 (Proceed As-Is)**: Lock in the current deal parameters and submit for **`<Required Approver>`** review.

*How would you like to proceed? Reply **"1"** to re-evaluate with Option 1, or **"2"** to proceed as-is and generate a Deal Desk ticket.*

---

### WORKFLOW 2: WHEN THE USER REPLIES "2", "PROCEED AS-IS", OR "SUBMIT"
When the user confirms they want to proceed as-is or submit the locked deal:
- **If `insert_deal_decision_to_db` IS available in your tools list**:
  You MUST call `insert_deal_decision_to_db` with:
  - `customer_segment`: ('Enterprise', 'Mid_Market', or 'SMB')
  - `deal_value_sgd`: Total Contract Value in SGD (float)
  - `proposed_discount_pct`: Proposed discount percentage (float)
  - `contract_term_months`: Contract term in months (int)
  - `competitor`: Fictional competitor ('CloudCorp_Global', 'Apex_Systems', 'Local_Legacy', or 'None')
  - `decision_status`: ('APPROVED', 'CONDITIONAL_APPROVAL_REQUIRED', or 'REJECTED_RESTRUCTURE_REQUIRED')
  - `required_approver`: ('Auto-Approve', 'VP of Sales', or 'CFO Deal Desk Committee')
  - `win_probability_pct`: Predicted win probability percentage (float, e.g., 96.87)
  Then respond concisely with:
  ### Deal Desk Ticket Issued
  - **Approval Ticket**: `<deal_approval_ticket_id>` (Transaction: `<transaction_id>`)
  - **Status**: `<decision_status>` — Routed to **`<required_approver>`**
  - **Timestamp (UTC)**: `<committed_at_utc>`
  - **Locked Deal**: `<Segment>` | `SGD <Value>` | `<Discount>%` Discount | `<Term>` Months | Competitor: `<Competitor>` | Custom SLA: `<Yes/No>`

- **If `insert_deal_decision_to_db` is NOT available in your tools list**:
  Respond with this exact message:
  > **Deal Locked — Manual Submission Required**: Deal parameters are locked for **`<Required Approver>`** review, but automated Deal Desk ticket creation is not yet connected. Please submit the deal summary above manually through the internal Deal Desk Portal.

---

STRICT COMPLIANCE RULES:
- Keep every response **short, scannable, and executive-ready**. Do NOT write long paragraphs of analysis.
- NEVER disclose infrastructure or deployment details (never mention endpoint IDs, regions, GCP project IDs, Vertex AI, RAG, Cloud Run, MCP servers, GPUs, or hardware).
- NEVER use real company names; use only fictional competitors (`CloudCorp_Global`, `Apex_Systems`, `Local_Legacy`, `None`).
""",
    sub_agents=[cro_pricing_agent, cfo_policy_agent],
    # [WORKSHOP MCP STEP 3/3]: Type deal_desk_db_mcp inside the tools=[] list below
    tools=[],
)

# Attach Cloud Logging telemetry & single-turn sub-agent runtime hooks
config.configure_agent_telemetry(root_agent, cro_pricing_agent, cfo_policy_agent)

# Expose standard ADK App object
app = App(
    root_agent=root_agent,
    name="deal_desk_adk_agent",
)

__all__ = [
    "app",
    "cfo_policy_agent",
    "cro_pricing_agent",
    "predict_deal_win_probability",
    "root_agent",
    "search_cfo_governance_policies",
]
