# Autonomous B2B Deal Desk & Margin Optimizer (`deal_desk_adk_agent`)

This folder contains the **Google ADK Multi-Agent System** (`gemini-3.1-pro-preview`) organized using the **Golden ADK Multi-Agent Folder Structure** so you can clearly see how **Orchestrator Agents**, **Sub-Agents**, and **Tools** fit together.

---

## Golden ADK Folder Structure

```text
deal_desk_adk_agent/
├── __init__.py                         # ADK Package Entrypoint (exports root_agent & app)
├── agent.py                            # 1. Root Orchestrator Agent + Workshop MCP Steps [1/3 - 3/3]
├── config.py                           # 2. Environment (.env) & GCP OAuth/IAM Token Loader
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

---

## Architecture Overview
- **`root_agent` (`deal_desk_executive_orchestrator` in [`agent.py`](./agent.py))**: Executive C-Level Orchestrator (`gemini-3.1-pro-preview`) that delegates to both specialist sub-agents, logs the binding decision via the Cloud Run Remote MCP Server (`deal_desk_db_mcp`), and synthesizes the Deal Desk Decision Memo.
- **`cro_pricing_agent` ([`sub_agents/cro_pricing_agent/agent.py`](./sub_agents/cro_pricing_agent/agent.py))**: Quantitative Pricing & Margin Optimizer (`gemini-3.1-pro-preview`) that calls [`predict_deal_win_probability`](./tools/pricing_tool.py) on the live **Vertex AI Online Prediction Endpoint** in `northamerica-northeast2`.
- **`cfo_policy_agent` ([`sub_agents/cfo_policy_agent/agent.py`](./sub_agents/cfo_policy_agent/agent.py))**: Policy & SLA Governance Auditor (`gemini-3.1-pro-preview`) that calls [`search_cfo_governance_policies`](./tools/policy_rag_tool.py) on **Vertex AI Search / Discovery Engine** over indexed corporate PDFs (`Global_Discount_Approval_Matrix_2026.pdf`, `Competitor_Displacement_Playbook.pdf`, `Enterprise_SLA_Governance_Rules.pdf`).
