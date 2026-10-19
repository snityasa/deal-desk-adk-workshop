# Autonomous B2B Deal Desk — Google ADK Multi-Agent & MCP Workshop

Welcome to the hands-on **Google Agent Development Kit (ADK) & Model Context Protocol (MCP)** repository for the Executive AI Workshop on Google Cloud.

---

## Repository Structure

```text
.
├── deal_desk_adk_agent/                # Google ADK Multi-Agent Application (Golden Layout)
│   ├── __init__.py                     # ADK Package Entrypoint (exports root_agent & app)
│   ├── agent.py                        # 1. Root Orchestrator Agent + Workshop MCP Steps [1/3 - 3/3]
│   ├── config.py                       # 2. Environment (.env) & GCP OAuth/IAM Token Loader
│   ├── sub_agents/                     # 3. Specialist Sub-Agents (Multi-Agent Delegation)
│   │   ├── cro_pricing_agent/          #    ├─ Sub-Agent A: Quantitative ML Pricing Optimizer
│   │   │   └── agent.py
│   │   └── cfo_policy_agent/           #    └─ Sub-Agent B: Qualitative CFO Policy & SLA Auditor
│   │       └── agent.py
│   ├── tools/                          # 4. ADK FunctionTools (External APIs & RAG)
│   │   ├── pricing_tool.py             #    ├─ `predict_deal_win_probability` (Vertex AI Prediction)
│   │   └── policy_rag_tool.py          #    └─ `search_cfo_governance_policies` (Vertex AI Search RAG)
│   ├── server.py                       # FastAPI + ADK Web UI (`/`) + A2A Protocol (`/a2a/...`)
│   ├── agent.json                      # A2A Agent Card metadata for Gemini Enterprise
│   ├── Dockerfile                      # Cloud Run container definition
│   ├── requirements.txt                # Python dependencies (`google-adk`, `mcp`, `fastapi`)
│   └── .env                            # Workshop environment configuration
├── deal_desk_mcp_server/               # Remote Cloud Run MCP Server (Deal Decisions Ledger DB)
│   ├── server.py                       # FastMCP SSE server exposing `insert_deal_decision_to_db`
│   ├── Dockerfile                      # Cloud Run container definition
│   └── requirements.txt                # MCP Server Python dependencies
└── run_local_adk_ui.sh                 # Launcher for testing the ADK Web UI in Cloud Shell / Locally
```

---

## Hands-On Workshop Instructions (Google Cloud Shell)

### 1. Configure `deal_desk_adk_agent/.env`
Open `deal_desk_adk_agent/.env` and set:
- `PROJECT_ID` and `GOOGLE_CLOUD_PROJECT` to your workshop GCP Project ID
- `VERTEX_ENDPOINT_ID` to your deployed Vertex AI Endpoint ID
- `MCP_SERVER_URL` to your deployed `deal-desk-mcp-server` Cloud Run URL

### 2. Connect the Remote MCP Toolset in `deal_desk_adk_agent/agent.py`
Open `deal_desk_adk_agent/agent.py` and complete the 3 guided markers:
- **`[WORKSHOP MCP STEP 1/3]`** *(Lines 20–22)*: Import `McpToolset` and `SseConnectionParams` from `google.adk.tools.mcp_tool`.
- **`[WORKSHOP MCP STEP 2/3]`** *(Lines 39–47)*: Instantiate `McpToolset` pointing to `MCP_SERVER_URL`.
- **`[WORKSHOP MCP STEP 3/3]`** *(Lines 114–115)*: Attach `tools=[deal_desk_db_mcp]` to `root_agent`.

### 3. Run & Test the ADK Web UI
From the repository root, run:
```bash
bash run_local_adk_ui.sh
```
Then open **Web Preview** in Cloud Shell on port `8081` (or `http://localhost:8081` if running locally).

### 4. Inspect Telemetry in Google Cloud Logging (`Logs Explorer`)
Every agent turn, Vertex AI Online Prediction call, Vertex AI Search RAG query, and Cloud Run MCP tool execution emits structured telemetry to **Google Cloud Logging** so you can verify whether live services or fallbacks were used:
- **All Deal Desk Telemetry**:
  ```text
  logName:"deal-desk-agent-telemetry"
  ```
- **Only Fallback Warnings (Auth / Endpoint / RAG issues)**:
  ```text
  logName:"deal-desk-agent-telemetry" AND severity=WARNING
  ```
- **Verify Live Vertex AI Endpoint & Vertex AI Search RAG Hits**:
  ```text
  logName:"deal-desk-agent-telemetry" AND (jsonPayload.event_type="VERTEX_AI_PREDICTION" OR jsonPayload.event_type="VERTEX_AI_SEARCH_RAG")
  ```
