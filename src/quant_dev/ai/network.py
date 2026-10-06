# src/quant_dev/ai/network.py
"""
Transformer-based trading agent network (public architecture).

This module defines the model architecture used by the AI trading agent.
The trained weights are NOT included in this repository.

Input:  (batch, seq_len, input_dim) OHLCV sequence
Output: action_logits (batch, 2), entry_offset (batch, 1), exit_offset (batch, 1)
"""
# ================================================= # 
import torch
import torch.nn as nn
# ================================================= # 
class TransformerPolicyNetwork(nn.Module):
    """Transformer policy network for instant trading decisions."""

    def __init__(
        self,
        input_dim: int = 8,
        d_model: int = 256,
        nhead: int = 8,
        num_layers: int = 3,
        dim_feedforward: int = 512,
        dropout: float = 0.1,
        max_seq_len: int = 300,
        output_dim: int = 2,
    ):
        super().__init__()

        self.input_proj = nn.Linear(input_dim, d_model)
        self.register_buffer(
            "pos_encoding",
            torch.randn(1, max_seq_len + 1, d_model) * 0.1,
        )

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.action_head = nn.Linear(d_model, output_dim)
        self.entry_price_head = nn.Linear(d_model, 1)
        self.exit_price_head = nn.Linear(d_model, 1)
# ================================================= # 
    def forward(self, ohlcv: torch.Tensor):
        batch_size, seq_len, _ = ohlcv.shape

        x = self.input_proj(ohlcv)
        x = x + self.pos_encoding[:, :seq_len, :]
        x = self.transformer(x)

        decision_token = x[:, -1, :]

        action_logits = self.action_head(decision_token)
        entry_offset = torch.tanh(self.entry_price_head(decision_token))
        exit_offset = torch.tanh(self.exit_price_head(decision_token))

        return action_logits, entry_offset, exit_offset
# ================================================= # 
