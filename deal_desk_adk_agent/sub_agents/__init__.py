"""Specialist Sub-Agents Package for the Deal Desk Multi-Agent System.

Exposes:
- `cro_pricing_agent`: Quantitative ML Pricing & Margin Optimizer Agent.
- `cfo_policy_agent`: Qualitative CFO Policy & SLA Governance Agent.
"""

from .cfo_policy_agent import cfo_policy_agent
from .cro_pricing_agent import cro_pricing_agent

__all__ = [
    "cfo_policy_agent",
    "cro_pricing_agent",
]
