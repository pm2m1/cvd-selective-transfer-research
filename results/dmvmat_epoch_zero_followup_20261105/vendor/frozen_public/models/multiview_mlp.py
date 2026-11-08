from __future__ import annotations

from collections import OrderedDict
from typing import Dict

import torch
from torch import nn


class ViewEncoder(nn.Module):
    def __init__(self, in_dim: int, hidden: int = 16):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.LayerNorm(hidden),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class MultiViewRiskNet(nn.Module):
    """Five-view MLP with explicit named modules for selective adaptation."""

    def __init__(self, view_dims: Dict[str, int], view_hidden: int = 16):
        super().__init__()
        if not view_dims or any(dim < 1 for dim in view_dims.values()) or view_hidden < 1:
            raise ValueError("Model input and hidden dimensions must be positive")
        self.view_names = list(view_dims.keys())
        self.encoders = nn.ModuleDict({
            name: ViewEncoder(dim, view_hidden) for name, dim in view_dims.items()
        })
        fused_dim = view_hidden * len(view_dims)
        self.fusion1 = nn.Sequential(nn.Linear(fused_dim, 64), nn.ReLU(), nn.LayerNorm(64))
        self.fusion2 = nn.Sequential(nn.Linear(64, 32), nn.ReLU(), nn.LayerNorm(32))
        self.head = nn.Linear(32, 1)

    def forward(self, views: Dict[str, torch.Tensor], return_features: bool = False):
        feats = OrderedDict()
        encoded = []
        for name in self.view_names:
            z = self.encoders[name](views[name])
            feats[f"view:{name}"] = z
            encoded.append(z)
        x = torch.cat(encoded, dim=1)
        x = self.fusion1(x)
        feats["fusion1"] = x
        x = self.fusion2(x)
        feats["fusion2"] = x
        logits = self.head(x).squeeze(-1)
        if return_features:
            return logits, feats
        return logits

    def selectable_modules(self):
        modules = OrderedDict((f"view:{name}", self.encoders[name]) for name in self.view_names)
        modules["fusion1"] = self.fusion1
        modules["fusion2"] = self.fusion2
        return modules
