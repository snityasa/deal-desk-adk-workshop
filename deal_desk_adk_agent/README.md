# Autonomous B2B Deal Desk & Margin Optimizer (`deal_desk_adk_agent`)

This package contains the **Google ADK Multi-Agent System** (`gemini-3.1-pro-preview`) structured using the **Golden ADK Multi-Agent Folder Layout**.

> **Looking for the full step-by-step Cloud Shell workshop instructions?** See the root [`../README.md`](../README.md).

---

## 1. What This Agent Does

The **Autonomous B2B Deal Desk & Margin Optimizer** evaluates enterprise software deals in seconds by coordinating two specialist sub-agents and a remote Cloud Run MCP server:

1. **Root Executive Orchestrator (`deal_desk_executive_orchestrator` in [`agent.py`](./agent.py))**:
   - Coordinates the end-to-end deal evaluation and returns a concise (<150-word) executive decision (`APPROVED`, `CONDITIONAL_APPROVAL_REQUIRED`, or `REJECTED_RESTRUCTURE_REQUIRED`).
   - Presents two interactive next steps:
     - **Option 1 (`Fast-Track Restructuring`)**: Reply `"1"` to re-evaluate the deal with modified terms (e.g., removing a Custom SLA or lowering the discount) to qualify for faster/auto-approval.
     - **Option 2 (`Proceed As-Is`)**: Reply `"2"` to lock the deal parameters and route for approval (creating an official `DD-2026-XXXXX` ticket when the Cloud Run MCP server is connected, or instructing manual portal submission prior to connecting MCP).
2. **Sub-Agent A — CRO Pricing Agent (`cro_pricing_agent` in [`sub_agents/cro_pricing_agent/agent.py`](./sub_agents/cro_pricing_agent/agent.py))**:
   - Calls [`predict_deal_win_probability`](./tools/pricing_tool.py) against the live **Vertex AI Online Prediction Endpoint** to calculate predicted win probability (`%`), outcome (`Won`/`Lost`), and recommended maximum discount ceiling.
3. **Sub-Agent B — CFO Policy Agent (`cfo_policy_agent` in [`sub_agents/cfo_policy_agent/agent.py`](./sub_agents/cfo_policy_agent/agent.py))**:
   - Calls [`search_cfo_governance_policies`](./tools/policy_rag_tool.py) against **Vertex AI Search (Discovery Engine RAG)** over indexed CFO governance PDFs (`Global_Discount_Approval_Matrix_2026.pdf`, `Competitor_Displacement_Playbook.pdf`, `Enterprise_SLA_Governance_Rules.pdf`).
4. **Remote MCP Toolset (`deal_desk_db_mcp` in [`agent.py`](./agent.py))**:
   - Connects via SSE to the remote **Cloud Run MCP Server** (`deal_desk_mcp_server/server.py`) and exposes `insert_deal_decision_to_db` once `[WORKSHOP MCP STEP 1/3 - 3/3]` are uncommented.

---

## 2. Golden ADK Folder Structure

```text
deal_desk_adk_agent/
├── __init__.py                         # ADK Package Entrypoint (exports root_agent & app)
├── agent.py                            # 1. Root Orchestrator Agent + Workshop MCP Steps [1/3 - 3/3]
├── config.py                           # 2. Environment (.env), Auth Helpers & Cloud Logging Telemetry
├── sub_agents/                         # 3. Specialist Sub-Agents (Multi-Agent Delegation)
│   ├── __init__.py
│   ├── cro_pricing_agent/              #    ├─ Sub-Agent A: Quantitative ML Pricing Optimizer
│   │   ├── __init__.py
│   │   └── agent.py                    #    │   └─ Agent definition (`cro_pricing_agent`)
│   └── cfo_policy_agent/               #    └─ Sub-Agent B: Qualitative CFO Policy & SLA Auditor
│       ├── __init__.py
│       └── agent.py                    #        └─ Agent definition (`cfo_policy_agent`)
├── tools/                              # 4. ADK FunctionTools (External APIs & RAG)
│   ├── __init__.py
│   ├── pricing_tool.py                 #    ├─ `predict_deal_win_probability` (Vertex AI Online Prediction)
│   └── policy_rag_tool.py              #    └─ `search_cfo_governance_policies` (Vertex AI Search RAG)
├── server.py                           # FastAPI + ADK Web UI (`/`) + A2A Protocol (`/a2a/...`)
├── agent.json                          # A2A Agent Card metadata for Gemini Enterprise
├── Dockerfile                          # Cloud Run container build definition
├── requirements.txt                    # Python dependencies (`google-adk`, `mcp`, `fastapi`)
└── .env                                # Workshop Configuration
```
