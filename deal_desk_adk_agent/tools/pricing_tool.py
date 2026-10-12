"""CRO Quantitative Pricing Tool (Vertex AI Online Prediction Endpoint).

Provides the `predict_deal_win_probability` ADK FunctionTool used by
`cro_pricing_agent` to score B2B enterprise deals against the deployed model
endpoint in `northamerica-northeast2`.
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


def predict_deal_win_probability(
    customer_segment: str,
    deal_value_sgd: float,
    proposed_discount_pct: float,
    contract_term_months: int,
    competitor: str = "None",
    custom_sla_requested: int = 0,
) -> dict[str, Any]:
  """Calls the live Vertex AI Online Prediction Endpoint to predict B2B deal win probability and margin policy.

  Args:
      customer_segment: Customer tier. Must be one of 'Enterprise', 'Mid_Market', or 'SMB'.
      deal_value_sgd: Total Contract Value (TCV) in Singapore Dollars (SGD), e.g., 1850000.0.
      proposed_discount_pct: Proposed discount percentage (e.g., 12.5 for 12.5%).
      contract_term_months: Contract duration in months (e.g., 12, 24, or 36).
      competitor: Fictional competitor being displaced. Must be one of:
          'CloudCorp_Global', 'Apex_Systems', 'Local_Legacy', or 'None'.
          NEVER use real company names.
      custom_sla_requested: 1 if the customer requested non-standard custom SLA terms, 0 otherwise.

  Returns:
      A dictionary containing the live Vertex AI prediction response (`win_probability`,
      `predicted_outcome`, `recommended_max_discount_pct`, `margin_policy`)
      along with endpoint metadata.
  """
  # Normalize and sanitize inputs
  clean_segment = str(customer_segment).strip()
  if clean_segment not in ("Enterprise", "Mid_Market", "SMB"):
    clean_segment = "Enterprise" if float(deal_value_sgd) >= 500000 else "Mid_Market"

  clean_competitor = str(competitor).strip()
  if clean_competitor not in config.ALLOWED_COMPETITORS:
    # Map any unrecognized value to safe fictional competitor
    clean_competitor = "None"

  clean_sla = 1 if int(custom_sla_requested) > 0 else 0

  instance_payload = {
      "customer_segment": clean_segment,
      "deal_value_sgd": float(deal_value_sgd),
      "proposed_discount_pct": float(proposed_discount_pct),
      "contract_term_months": int(contract_term_months),
      "competitor": clean_competitor,
      "custom_sla_requested": clean_sla,
  }

  endpoint_url = (
      f"https://{config.REGION}-aiplatform.googleapis.com/v1/"
      f"projects/{config.PROJECT_ID}/locations/{config.REGION}/"
      f"endpoints/{config.VERTEX_ENDPOINT_ID}:predict"
  )

  token = config.get_gcp_access_token()
  if token:
    try:
      headers = {
          "Authorization": f"Bearer {token}",
          "Content-Type": "application/json",
          "X-Goog-User-Project": config.PROJECT_ID,
      }
      resp = requests.post(
          endpoint_url,
          headers=headers,
          json={"instances": [instance_payload]},
          timeout=15,
      )
      if resp.status_code == 200:
        data = resp.json()
        predictions = data.get("predictions", [])
        raw_pred = predictions[0] if predictions else {}
        if isinstance(raw_pred, dict):
          # Strip any internal hardware/accelerator telemetry fields from display
          pred = {
              k: v
              for k, v in raw_pred.items()
              if "gpu" not in k.lower() and "hardware" not in k.lower()
          }
        else:
          pred = raw_pred
        return {
            "status": "success",
            "execution_mode": "LIVE_VERTEX_AI_ENDPOINT",
            "project_id": config.PROJECT_ID,
            "region": config.REGION,
            "endpoint_id": config.VERTEX_ENDPOINT_ID,
            "input_instance": instance_payload,
            "prediction": pred,
        }
      else:
        logger.warning(
            "Vertex AI Endpoint returned HTTP %s: %s",
            resp.status_code,
            resp.text,
        )
    except Exception as exc:
      logger.warning("Vertex AI Endpoint request exception: %s", exc)

  # Deterministic fallback matching the trained model physics if offline/unauthenticated
  base_rec_discount = 10.0
  if clean_segment == "Enterprise":
    base_rec_discount += 2.5
  elif clean_segment == "Mid_Market":
    base_rec_discount += 1.0

  if int(contract_term_months) >= 36:
    base_rec_discount += 1.7
  elif int(contract_term_months) >= 24:
    base_rec_discount += 0.8

  if clean_competitor in ("CloudCorp_Global", "Apex_Systems"):
    base_rec_discount += 1.5

  recommended_max_discount = round(base_rec_discount, 1)
  discount_delta = float(proposed_discount_pct) - recommended_max_discount

  win_prob = min(
      0.92,
      max(
          0.18,
          round(
              0.62
              + (float(proposed_discount_pct) * 0.012)
              - (clean_sla * 0.05)
              + (0.04 if int(contract_term_months) >= 36 else 0.0),
              2,
          ),
      ),
  )

  if discount_delta <= 0.0:
    margin_policy = "AUTO_APPROVE"
  elif discount_delta <= 3.0:
    margin_policy = "VP_SALES_APPROVAL"
  else:
    margin_policy = "CFO_COMMITTEE_ESCALATION"

  return {
      "status": "success",
      "execution_mode": "FALLBACK_SIMULATION (Live endpoint unreachable or local auth expired)",
      "project_id": config.PROJECT_ID,
      "region": config.REGION,
      "endpoint_id": config.VERTEX_ENDPOINT_ID,
      "input_instance": instance_payload,
      "prediction": {
          "win_probability": win_prob,
          "predicted_outcome": "Won" if win_prob >= 0.55 else "Lost",
          "recommended_max_discount_pct": recommended_max_discount,
          "margin_policy": margin_policy,
      },
  }
