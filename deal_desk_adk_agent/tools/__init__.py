"""ADK Tools Package for the Autonomous B2B Deal Desk Multi-Agent System.

Exposes:
- `predict_deal_win_probability`: Calls the live Vertex AI Online Prediction
  Endpoint in `northamerica-northeast2` for quantitative deal scoring.
- `search_cfo_governance_policies`: Queries Vertex AI Search (Discovery Engine)
  over official corporate governance PDFs.
"""

from .policy_rag_tool import search_cfo_governance_policies
from .pricing_tool import predict_deal_win_probability

__all__ = [
    "predict_deal_win_probability",
    "search_cfo_governance_policies",
]
