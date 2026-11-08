"""Proposed family-isolated, inference-only CPU runtime for frozen models.

This module never loads a cohort or performs an evaluation. A future recovery
executor must launch separate fresh processes for Torch and tabular families;
it must not import both native stacks in a single process. The 6C-2 executor
and its failed attempt remain untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
import pandas as pd


VIEWS = {
    "background": ("age", "sex"),
    "haemodynamic": ("sbp", "dbp"),
    "metabolic": ("bmi", "total_cholesterol", "hdl"),
    "behaviour": ("smoking_status",),
    "comorbidity_medication": ("diabetes", "antihypertensive_treatment"),
}
CONTINUOUS = ("age", "sbp", "dbp", "bmi", "total_cholesterol", "hdl")
CATEGORIES = {
    "sex": ("female", "male"),
    "smoking_status": ("never", "former", "current"),
    "diabetes": ("no", "yes"),
    "antihypertensive_treatment": ("no", "yes"),
}
_THREAD_VARIABLES = ("OMP_NUM_THREADS", "MKL_NUM_THREADS",
                     "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def initialize_isolated_cpu(family_group: str) -> None:
    """Set native-thread policy before importing either model stack."""
    if family_group not in {"torch", "tabular"}:
        raise ValueError("Unknown frozen model family group")
    if "torch" in sys.modules or "xgboost" in sys.modules or "sklearn" in sys.modules:
        raise RuntimeError("Initialize native inference in a fresh process")
    for name in _THREAD_VARIABLES:
        os.environ[name] = "1"
    # sklearn sets this to True by default at import; FALSE exposes a conflict
    # rather than masking it. Native stacks are isolated by process.
    os.environ["KMP_DUPLICATE_LIB_OK"] = "FALSE"
    if family_group == "torch":
        import torch
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
    else:
        import xgboost  # noqa: F401


def encode_frozen(entry: dict, frame: pd.DataFrame, dimensions: dict) -> dict[str, np.ndarray]:
    """Recreate the frozen ten-feature transform without importing training code."""
    path = Path(entry["preprocessor_path"])
    if file_sha256(path) != entry["preprocessor_sha256"]:
        raise ValueError("Frozen preprocessor changed")
    saved = json.loads(path.read_text())
    if (saved.get("schema_version") != "cvd-public-wave-v2-ten-doctor-report" or
            saved.get("fit_role") not in {"source_train", "target_adaptation"} or
            saved.get("views") != {k: list(v) for k, v in VIEWS.items()} or
            saved.get("categories") != {k: list(v) + ["unknown"] for k, v in CATEGORIES.items()} or
            set(saved.get("continuous", {})) != set(CONTINUOUS)):
        raise ValueError("Frozen feature schema or preprocessing provenance changed")
    if ((entry["method"].startswith("source_") or entry["method"] in {
            "head_only", "full_finetune", "fixed_mask", "random_calibrated_logical",
            "legacy_topk", "calibrated_threshold", "calibrated_logical"}) and
            saved["fit_role"] != "source_train"):
        raise ValueError("Transfer/source model has target-fitted preprocessing")
    if entry["method"].startswith("target_") and saved["fit_role"] != "target_adaptation":
        raise ValueError("Target-only model has wrong preprocessing role")
    expected = {feature for fields in VIEWS.values() for feature in fields}
    if not frame.columns.is_unique or set(frame.columns) != expected:
        raise ValueError("Inference requires exactly ten approved predictors")
    encoded = {}
    for name in CONTINUOUS:
        values = pd.to_numeric(frame[name], errors="raise").to_numpy(dtype=float)
        stats = saved["continuous"][name]
        if (np.isinf(values).any() or not np.isfinite([stats["median"], stats["mean"], stats["scale"]]).all()
                or stats["scale"] <= 0):
            raise ValueError("Invalid continuous feature or preprocessing statistic")
        encoded[name] = ((np.where(np.isnan(values), stats["median"], values) -
                         stats["mean"]) / stats["scale"])[:, None]
    for name, categories in saved["categories"].items():
        if not frame[name].dropna().isin(CATEGORIES[name]).all():
            raise ValueError("Unmapped test category")
        values = frame[name].fillna("unknown").to_numpy()
        encoded[name] = np.column_stack([values == value for value in categories])
    views = {view: np.concatenate([encoded[name] for name in fields], axis=1).astype(np.float32)
             for view, fields in VIEWS.items()}
    columns = {view: [column for name in fields for column in (
        [name] if name in CONTINUOUS else [f"{name}={v}" for v in saved["categories"][name]])]
        for view, fields in VIEWS.items()}
    if (columns != saved.get("encoded_columns") or
            {name: value.shape[1] for name, value in views.items()} != dimensions or
            any(not np.isfinite(value).all() for value in views.values())):
        raise ValueError("Frozen encoded order/dimensions or values differ")
    return views


def infer_frozen_isolated(entry: dict, frame: pd.DataFrame, dimensions: dict, family_group: str) -> np.ndarray:
    """Predict with exact frozen weights; no fit, optimizer, mask or calibration."""
    path = Path(entry["checkpoint_path"])
    if file_sha256(path) != entry["checkpoint_sha256"]:
        raise ValueError("Frozen model checkpoint changed")
    views = encode_frozen(entry, frame, dimensions)
    family = entry["model_family"]
    if family_group == "tabular" and family in {"sklearn_logistic", "xgboost"}:
        if "torch" in sys.modules:
            raise RuntimeError("Torch entered isolated tabular process")
        import joblib
        from sklearn.linear_model import LogisticRegression
        from xgboost import XGBClassifier
        model = joblib.load(path)
        if (family == "sklearn_logistic" and not isinstance(model, LogisticRegression)) or (
                family == "xgboost" and not isinstance(model, XGBClassifier)):
            raise ValueError("Frozen tabular family mismatch")
        flat = np.concatenate([views[name] for name in VIEWS], axis=1)
        values = np.asarray(model.predict_proba(flat))
        if values.shape != (len(frame), 2) or list(model.classes_) != [0, 1]:
            raise ValueError("Frozen tabular class order/output changed")
        output = values[:, 1]
    elif family_group == "torch" and family in {"flat_mlp", "five_view_net"}:
        if "sklearn" in sys.modules or "xgboost" in sys.modules:
            raise RuntimeError("Tabular native stack entered isolated Torch process")
        import torch
        from torch import nn
        from .models.multiview_mlp import MultiViewRiskNet

        if family == "flat_mlp":
            # Exact frozen FlatMLP topology from experiments/baselines.py.
            # Kept local so importing that training module cannot import sklearn.
            class FlatMLP(nn.Module):
                def __init__(self, view_dims: dict[str, int]):
                    super().__init__()
                    self.view_names = list(view_dims)
                    self.net = nn.Sequential(nn.Linear(sum(view_dims.values()), 64), nn.ReLU(),
                                             nn.LayerNorm(64), nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1))

                def forward(self, tensors):
                    return self.net(torch.cat([tensors[name] for name in self.view_names], dim=1)).squeeze(-1)

            model = FlatMLP(dimensions)
        else:
            model = MultiViewRiskNet(dimensions, 16)
        model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True), strict=True)
        model.eval()
        with torch.inference_mode():
            output = torch.sigmoid(model({k: torch.from_numpy(v) for k, v in views.items()})).numpy()
    else:
        raise ValueError("Model family violates isolated process boundary")
    output = np.asarray(output, dtype=float)
    if (output.shape != (len(frame),) or not np.isfinite(output).all() or
            ((output < 0) | (output > 1)).any()):
        raise ValueError("Frozen model returned invalid probabilities")
    return output
