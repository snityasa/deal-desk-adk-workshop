"""CFO Governance Policy RAG Tool (Vertex AI Search / Discovery Engine).

Provides the `search_cfo_governance_policies` ADK FunctionTool used by
`cfo_policy_agent` to retrieve official discount matrix, competitor
displacement, and SLA rules from indexed corporate PDFs.
"""

from __future__ import annotations

import logging
from typing import Any
import requests

try:
  from .. import config
except ImportError:
  import config  # type: ignore

logger = logging.getLogger(__name__)


def search_cfo_governance_policies(query: str) -> dict[str, Any]:
  """Searches official CFO Deal Desk Governance, Discount Matrix & SLA Policies via Vertex AI Search RAG.

  Queries the Discovery Engine (`deal-desk-cfo-search-engine`) indexing:
  1. `Global_Discount_Approval_Matrix_2026.pdf`
  2. `Competitor_Displacement_Playbook.pdf`
  3. `Enterprise_SLA_Governance_Rules.pdf`

  Args:
      query: Natural language policy question (e.g. "What is the maximum discount
          allowed for an Enterprise 36-month deal displacing CloudCorp_Global and
          what are the custom SLA requirements?").

  Returns:
      A dictionary containing the Generative AI RAG Summary (`rag_summary`),
      citations, and retrieved policy document chunks (`retrieved_policies`).
  """
  search_url = (
      f"https://discoveryengine.googleapis.com/v1/projects/{config.PROJECT_ID}/"
      f"locations/{config.SEARCH_LOCATION}/collections/default_collection/"
      f"engines/{config.SEARCH_ENGINE_ID}/servingConfigs/default_search:search"
  )

  request_body = {
      "query": query,
      "pageSize": 3,
      "contentSearchSpec": {
          "snippetSpec": {"returnSnippet": True},
          "summarySpec": {
              "summaryResultCount": 3,
              "includeCitations": True,
              "ignoreAdversarialQuery": True,
          },
          "extractiveContentSpec": {
              "maxExtractiveAnswerCount": 2,
              "maxExtractiveSegmentCount": 2,
          },
      },
  }

  token = config.get_gcp_access_token()
  if token:
    try:
      headers = {
          "Authorization": f"Bearer {token}",
          "Content-Type": "application/json",
          "X-Goog-User-Project": config.PROJECT_ID,
      }
      resp = requests.post(
          search_url, headers=headers, json=request_body, timeout=15
      )
      if resp.status_code == 200:
        data = resp.json()
        summary_text = data.get("summary", {}).get("summaryText", "")
        results = data.get("results", [])
        retrieved_docs = []
        for idx, r in enumerate(results, 1):
          doc = r.get("document", {})
          derived = doc.get("derivedStructData", {})
          link = derived.get("link", doc.get("content", {}).get("uri", "N/A"))
          title = derived.get("title", link.split("/")[-1] if link else f"Policy_Doc_{idx}")
          answers = [
              {
                  "page": a.get("pageNumber", "1"),
                  "content": a.get("content", "").strip(),
              }
              for a in derived.get("extractive_answers", [])
          ]
          segments = [
              {
                  "page": s.get("pageNumber", "1"),
                  "content": s.get("content", "").strip(),
              }
              for s in derived.get("extractive_segments", [])[:2]
          ]
          retrieved_docs.append({
              "rank": idx,
              "document_title": title,
              "gcs_uri": link,
              "extractive_answers": answers,
              "extractive_segments": segments,
          })

        return {
            "status": "success",
            "execution_mode": "LIVE_VERTEX_AI_SEARCH_RAG",
            "project_id": config.PROJECT_ID,
            "search_engine_id": config.SEARCH_ENGINE_ID,
            "query": query,
            "rag_summary": summary_text,
            "retrieved_policies": retrieved_docs,
        }
      else:
        logger.warning(
            "Vertex AI Search returned HTTP %s: %s",
            resp.status_code,
            resp.text,
        )
    except Exception as exc:
      logger.warning("Vertex AI Search request exception: %s", exc)

  # Grounded fallback excerpting the 3 official policy documents
  return {
      "status": "success",
      "execution_mode": "FALLBACK_POLICY_CACHE (Live Discovery Engine unreachable or local auth expired)",
      "project_id": config.PROJECT_ID,
      "search_engine_id": config.SEARCH_ENGINE_ID,
      "query": query,
      "rag_summary": (
          "According to the Global Discount Approval Matrix 2026 [1], standard "
          "auto-approval thresholds are capped at 10% for SMB, 12% for Mid_Market, "
          "and 14.2% for 36-month Enterprise contracts. Under the Competitor "
          "Displacement Playbook [2], an additional +2.0% to +3.0% displacement "
          "discount buffer is permitted when displacing CloudCorp_Global or "
          "Apex_Systems (requires VP Sales sign-off up to 17%, CFO Deal Desk Committee "
          "above 17%). Under Enterprise SLA Governance Rules [3], custom SLAs "
          "(custom_sla_requested=1) require a minimum Total Contract Value (TCV) of "
          "SGD 1,500,000 and are strictly prohibited for SMB and Mid_Market tiers "
          "unless an executive SLA fee addendum is attached."
      ),
      "retrieved_policies": [
          {
              "rank": 1,
              "document_title": "Global_Discount_Approval_Matrix_2026.pdf",
              "gcs_uri": f"gs://{config.PROJECT_ID}-ai-workshop-nane2/rag_policies/Global_Discount_Approval_Matrix_2026.pdf",
              "extractive_answers": [
                  {
                      "page": "1",
                      "content": (
                          "Discount Approval Tiers: Up to Recommended Max Discount "
                          "(~14.2% for 36M Enterprise) = AUTO_APPROVE. +0.1% to +3.0% "
                          "above recommended max = VP_SALES_APPROVAL. >3.0% above "
                          "recommended max or gross margin <68% = CFO_COMMITTEE_ESCALATION."
                      ),
                  }
              ],
          },
          {
              "rank": 2,
              "document_title": "Competitor_Displacement_Playbook.pdf",
              "gcs_uri": f"gs://{config.PROJECT_ID}-ai-workshop-nane2/rag_policies/Competitor_Displacement_Playbook.pdf",
              "extractive_answers": [
                  {
                      "page": "2",
                      "content": (
                          "Approved Fictional Competitor Displacement Allowances: "
                          "CloudCorp_Global (+2.5% max additional discount allowance on "
                          "36-month commitments), Apex_Systems (+2.0% allowance), "
                          "Local_Legacy (+1.0% allowance). Multi-year commitment required."
                      ),
                  }
              ],
          },
          {
              "rank": 3,
              "document_title": "Enterprise_SLA_Governance_Rules.pdf",
              "gcs_uri": f"gs://{config.PROJECT_ID}-ai-workshop-nane2/rag_policies/Enterprise_SLA_Governance_Rules.pdf",
              "extractive_answers": [
                  {
                      "page": "1",
                      "content": (
                          "Custom SLA Eligibility (`custom_sla_requested=1`): Minimum "
                          "deal_value_sgd of SGD 1,500,000 is mandatory for custom SLA "
                          "provisioning. SMB and Mid_Market deals requesting custom SLAs "
                          "must be rejected or restructured to Standard Enterprise Support."
                      ),
                  }
              ],
          },
      ],
  }
