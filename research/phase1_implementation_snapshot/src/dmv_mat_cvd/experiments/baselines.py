from __future__ import annotations

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from torch import nn

from ..data.base import MultiViewDataset
from ..safeguards import SplitRole, require_role


class FlatMLP(nn.Module):
    def __init__(self, view_dims: dict[str, int]):
        super().__init__()
        self.view_names = list(view_dims)
        self.net = nn.Sequential(nn.Linear(sum(view_dims.values()), 64), nn.ReLU(),
                                 nn.LayerNorm(64), nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, views: dict[str, torch.Tensor]) -> torch.Tensor:
        return self.net(torch.cat([views[name] for name in self.view_names], dim=1)).squeeze(-1)


def flatten(dataset: MultiViewDataset) -> np.ndarray:
    return np.concatenate([dataset.views[name].cpu().numpy() for name in dataset.names], axis=1)


def fit_tabular(mode: str, dataset: MultiViewDataset, seed: int):
    require_role(dataset, {SplitRole.TARGET_ADAPTATION}, f"{mode} fit")
    labels = dataset.labels.cpu().numpy()
    if len(np.unique(labels)) != 2:
        raise ValueError(f"{mode} requires both classes in target adaptation")
    if mode == "logistic_regression":
        model = LogisticRegression(max_iter=1000, random_state=seed)
    elif mode == "xgboost":
        try:
            from xgboost import XGBClassifier
        except Exception as exc:
            # Native-library import failures can use XGBoost's own exception
            # class, which cannot be imported before the failing package.
            raise ImportError(
                "XGBoost is optional. Install with: pip install -e '.[xgboost]'. "
                "Its native runtime must also load (macOS: OpenMP/libomp); see the chained error."
            ) from exc
        model = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05,
                              random_state=seed, n_jobs=1, eval_metric="logloss")
    else:
        raise ValueError(f"Unknown tabular baseline: {mode}")
    return model.fit(flatten(dataset), labels)


def tabular_parameters(model) -> dict:
    """Preserve nonfinite estimator defaults as strings in strict JSON metadata."""
    return {key: str(value) if isinstance(value, float) and not np.isfinite(value) else value
            for key, value in model.get_params().items()}
