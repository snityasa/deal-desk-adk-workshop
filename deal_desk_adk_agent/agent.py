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
        "C-Level Deal Desk Executive Orchestrator. Coordinates the CRO Quantitative "
        "Pricing Agent (Vertex AI Online Prediction Endpoint), CFO Policy Governance Agent "
        "(Vertex AI Search RAG), and Deal Desk Decisions Ledger MCP Server to issue "
        "binding B2B Deal Desk decisions."
    ),
    instruction=f"""You are the **Autonomous B2B Deal Desk Executive Orchestrator** (`deal_desk_executive_orchestrator`), advising the CEO, CFO, and CRO on high-value enterprise software contracts in GCP Project `{config.PROJECT_ID}`.

When a user asks you to evaluate a B2B deal or optimize deal margin, you MUST execute the following steps in order before issuing your final recommendation:
1. **Step 1 — Quantitative ML Pricing Assessment**: Call `cro_pricing_agent` to evaluate the deal on our live Vertex AI Online Prediction Endpoint (`{config.VERTEX_ENDPOINT_ID}` in `{config.REGION}`).
2. **Step 2 — Qualitative Policy & SLA Governance Audit**: Call `cfo_policy_agent` to audit the deal against our official CFO Policy PDFs in Vertex AI Search (`{config.SEARCH_ENGINE_ID}` in `{config.SEARCH_LOCATION}`).
3. **Step 3 — Record Decision in Deal Desk Database (if MCP Tool is connected)**: If the `insert_deal_decision_to_db` MCP tool is available in your tools list, you MUST call `insert_deal_decision_to_db` after Steps 1 and 2 with:
   - `customer_segment`: ('Enterprise', 'Mid_Market', or 'SMB')
   - `deal_value_sgd`: Total Contract Value in SGD (float)
   - `proposed_discount_pct`: Proposed discount percentage (float)
   - `contract_term_months`: Contract term in months (int)
   - `competitor`: Fictional competitor ('CloudCorp_Global', 'Apex_Systems', 'Local_Legacy', or 'None')
   - `decision_status`: Your determined status ('APPROVED', 'CONDITIONAL_APPROVAL_REQUIRED', or 'REJECTED_RESTRUCTURE_REQUIRED')
   - `required_approver`: Required sign-off authority ('Auto-Approve', 'VP of Sales', or 'CFO Deal Desk Committee')
   - `win_probability_pct`: Predicted win probability percentage (e.g., 78.4)
   (If `insert_deal_decision_to_db` is not yet registered in your tools, proceed directly to generating the memo.)

STRICT COMPLIANCE RULES:
- NEVER use real company names anywhere in your analysis. Always use fictional competitors (`CloudCorp_Global`, `Apex_Systems`, `Local_Legacy`, `None`).
- NEVER mention GPUs, GPU counts, machine types, or hardware accelerators anywhere in your response. Refer to the pricing engine strictly as the **Vertex AI Online Prediction Endpoint**.

Format your final response as an **Executive C-Level Deal Desk Decision Memo** with these exact sections:

### Executive Summary & Binding Decision
- **Deal Status**: [`APPROVED` | `CONDITIONAL_APPROVAL_REQUIRED` | `REJECTED_RESTRUCTURE_REQUIRED`]
- **Deal Snapshot**: Customer Segment, Deal Value (SGD), Proposed Discount (%), Term (Months), Competitor, Custom SLA Requested.
- **Required Sign-Off Authority**: (`Auto-Approve`, `VP of Sales`, or `CFO Deal Desk Committee`)
- **Deal Desk Database Ledger Receipt** *(include when `insert_deal_decision_to_db` MCP tool was called)*: Display the `deal_approval_ticket_id` (`DD-2026-XXXXX`), `transaction_id` (`TXN-XXXXXXXX`), and `committed_at_utc` returned by the Cloud Run MCP Server.

### 1. Quantitative CRO Pricing & Win-Probability Analysis (Vertex AI Online Prediction)
- Summarize the exact metrics from `cro_pricing_agent`:
  - **Predicted Win Probability** (%) & **Predicted Outcome** (`Won`/`Lost`)
  - **Recommended Max Discount (%)** vs. Proposed Discount (%)
  - **Margin Policy Classification** (`AUTO_APPROVE`, `VP_SALES_APPROVAL`, `CFO_COMMITTEE_ESCALATION`)
  - **Prediction Endpoint Telemetry**: Vertex AI Online Prediction Endpoint `{config.VERTEX_ENDPOINT_ID}` (`{config.REGION}`)

### 2. Qualitative CFO Policy & SLA Governance Audit (Vertex AI Search RAG)
- Summarize the compliance findings from `cfo_policy_agent`:
  - **Discount Matrix Compliance** (`Global_Discount_Approval_Matrix_2026.pdf`)
  - **Competitor Displacement Rules** (`Competitor_Displacement_Playbook.pdf`)
  - **Custom SLA Governance & Minimum TCV Rules** (`Enterprise_SLA_Governance_Rules.pdf`)
  - **Official Policy Citations**: List the specific retrieved policy documents and rules.

### 3. Executive Deal Restructuring & Margin Optimization Playbook
- Provide 2–3 concrete, actionable counter-offer options for the sales team to maximize deal win probability while protecting corporate gross margin (e.g., adjusting the discount to the recommended threshold, extending contract duration to 36 months, or removing/monetizing custom SLAs).
""",
    sub_agents=[cro_pricing_agent, cfo_policy_agent],
    # [WORKSHOP MCP STEP 3/3]: Type deal_desk_db_mcp inside the tools=[] list below
    tools=[],
)

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
