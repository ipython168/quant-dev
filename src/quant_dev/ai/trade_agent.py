# src/quant_dev/ai/trade_agent.py
"""
AI Trading Agent (public interface).

Loads a pre-trained model from HuggingFace Hub and generates
order suggestions from OHLCV data.

Model: https://huggingface.co/ipython168/trader-transformer-v20
"""
# ================================================= # 
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
import pandas as pd
import torch

from .network import TransformerPolicyNetwork
# ================================================= # 
@dataclass
class AIContext:
    """AI input: recent N bars OHLCV + current position."""
    ohlcv: pd.DataFrame
    current_position: int
    direction: str  # "buy" / "sell"
# ================================================= # 
@dataclass
class AIOrder:
    """AI output: a single order decision."""
    action: Literal["entry", "exit", "hold"]
    price: Optional[float] = None
# ================================================= # 
    def __post_init__(self):
        if self.action != "hold" and self.price is None:
            raise ValueError(f"AIOrder action={self.action} requires price")
# ================================================= # 
class TradeAgent:
    """
    AI trading agent interface.

    Loading:
        agent = TradeAgent.from_pretrained("ipython168/trader-transformer-v20")
    """

    PRICE_OFFSET_SCALE = 0.05
    INFERENCE_THRESHOLD = 0.7

    # 13 features（同 trained model 一致）
    FEATURE_COLS = [
        "Open", "High", "Low", "Close", "Volume",
        "atr7_ratio", "close_sma5", "close_sma10",
        "rsi7", "rsi14", "adx7", "adx14", "macd",
    ]

    def __init__(
        self,
        metadata: dict,
        device: Optional[str] = None,
    ):
        self.metadata = metadata
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Read network params from metadata
        self.d_model = metadata.get("d_model", 256)
        self.nhead = metadata.get("nhead", 8)
        self.num_layers = metadata.get("num_layers", 3)
        self.dim_feedforward = metadata.get("dim_feedforward", 512)
        self.dropout = metadata.get("dropout", 0.1)
        self.input_bars = metadata.get("input_bars", 300)

        # Action names（同 trained model 一致）
        self.action_names = metadata.get("action_names", ["reverse", "hold"])

        # Network params from training history
        train_heads = (
            metadata.get("training_history", [{}])[-1]
            .get("train_heads", ["action_head"])
        )

        # Build network
        self.network = TransformerPolicyNetwork(
            input_dim=len(self.FEATURE_COLS),
            d_model=self.d_model,
            nhead=self.nhead,
            num_layers=self.num_layers,
            dim_feedforward=self.dim_feedforward,
            dropout=self.dropout,
            max_seq_len=self.input_bars,
            output_dim=len(self.action_names),
        ).to(self.device)

        self.network.eval()
# ================================================= # 
# HuggingFace-style loading
# ================================================= # 
    @classmethod
    def from_pretrained(
        cls,
        repo_id: str,
        device: Optional[str] = None,
    ) -> "TradeAgent":
        """Load a TradeAgent from HuggingFace Hub."""
        from huggingface_hub import hf_hub_download

        model_path = hf_hub_download(repo_id=repo_id, filename="agent.pt")
        checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)

        agent = cls(metadata=checkpoint["metadata"], device=device)
        agent.network.load_state_dict(checkpoint["model_state_dict"])
        print(f"✅ Loaded {repo_id}")
        return agent
# ================================================= # 
# Inference
# ================================================= # 
    @torch.no_grad()
    def compute_action(self, context: AIContext) -> AIOrder:
        """Generate an AI order from the given context."""
        features = self._prepare_features(context.ohlcv)
        ohlcv_tensor = torch.tensor(
            features, dtype=torch.float32
        ).unsqueeze(0).to(self.device)

        action_logits, entry_offset, exit_offset = self.network(ohlcv_tensor)
        action_probs = torch.softmax(action_logits, dim=-1)

        # action_names = ["reverse", "hold"]
        argmax_idx = torch.argmax(action_probs, dim=-1).item()
        action = self.action_names[argmax_idx]

        # Map "reverse"/"hold" → AIOrder action
        ai_action = self._map_action(action, context.current_position)

        if ai_action == "hold":
            return AIOrder(action="hold", price=None)

        # Compute price
        offset = entry_offset.item() if ai_action == "entry" else exit_offset.item()
        price_factor = 1.0 + offset * self.PRICE_OFFSET_SCALE
        price_factor = max(0.85, min(1.15, price_factor))

        last_close = context.ohlcv["Close"].iloc[-1]
        return AIOrder(action=ai_action, price=last_close * price_factor)
# ================================================= # 
    def _map_action(self, action: str, current_position: int) -> str:
        """Map model action (reverse/hold) → AIOrder action (entry/exit/hold)."""
        if action == "hold":
            return "hold"
        # "reverse"
        if current_position == 0:
            return "entry"
        else:
            return "exit"
# ================================================= # 
    def _prepare_features(self, ohlcv: pd.DataFrame) -> np.ndarray:
        """Prepare features (dummy version for demo)."""
        # For demo, use raw OHLCV + padding
        cols = ["Open", "High", "Low", "Close", "Volume"]
        data = ohlcv[cols].values.astype(np.float32)

        if len(data) < self.input_bars:
            pad = np.zeros((self.input_bars - len(data), len(cols)), dtype=np.float32)
            data = np.vstack([pad, data])
        else:
            data = data[-self.input_bars:]

        # Pad to 13 features
        n_features = len(self.FEATURE_COLS)
        if data.shape[1] < n_features:
            extra = np.zeros(
                (data.shape[0], n_features - data.shape[1]), dtype=np.float32
            )
            data = np.hstack([data, extra])

        return data
# ================================================= # 








