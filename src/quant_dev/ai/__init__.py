# src/quant_dev/ai/__init__.py
"""
AI trading agent module.

Public interface for AI-driven order generation.
"""
# ================================================= # 
from .network import TransformerPolicyNetwork
from .trade_agent import AIContext, AIOrder, TradeAgent
# ================================================= # 
__all__ = [
    "TransformerPolicyNetwork",
    "AIContext",
    "AIOrder",
    "TradeAgent",
]
# ================================================= # 
# ================================================= # 
