from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterator

import numpy as np
import torch
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             matthews_corrcoef, roc_auc_score)

from .safeguards import SplitRole, require_role
from .training import move_views


@dataclass(frozen=True)
class BinaryMetrics:
    ap: float | None
    auroc: float | None
    brier: float
    prevalence: float
    threshold: float
    sensitivity: float | None
    specificity: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    balanced_accuracy: float | None
    mcc: float | None
    n: int

    def to_dict(self) -> dict:
        return asdict(self)


def binary_metrics(y: np.ndarray, p: np.ndarray, threshold: float = 0.5) -> BinaryMetrics:
    y, p = np.asarray(y), np.asarray(p)
    if y.ndim != 1 or p.shape != y.shape or len(y) == 0:
        raise ValueError("Expected nonempty equally sized label/probability vectors")
    if not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Expected binary labels and finite probabilities in [0, 1]")
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold must lie in [0, 1]")
    predicted = p >= threshold
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    divide = lambda a, b: float(a / b) if b else None
    sensitivity, specificity = divide(tp, tp + fn), divide(tn, tn + fp)
    both_classes = len(np.unique(y)) == 2
    return BinaryMetrics(
        ap=float(average_precision_score(y, p)) if np.any(y == 1) else None,
        auroc=float(roc_auc_score(y, p)) if both_classes else None,
        brier=float(brier_score_loss(y, p)), prevalence=float(y.mean()), threshold=float(threshold),
        sensitivity=sensitivity, specificity=specificity, precision=divide(tp, tp + fp),
        recall=sensitivity, f1=divide(2 * tp, 2 * tp + fp + fn),
        balanced_accuracy=(sensitivity + specificity) / 2 if both_classes else None,
        mcc=float(matthews_corrcoef(y, predicted)) if both_classes and len(np.unique(predicted)) == 2 else None,
        n=len(y),
    )


def predict(model, loader, device) -> tuple[np.ndarray, np.ndarray]:
    model.to(device).eval()
    ys, ps = [], []
    with torch.no_grad():
        for views, y in loader:
            logits = model(move_views(views, device))
            ys.append(y.cpu().numpy())
            ps.append(torch.sigmoid(logits).cpu().numpy())
    if not ys:
        raise ValueError("Cannot evaluate an empty dataset")
    return np.concatenate(ys), np.concatenate(ps)


def metrics(model, loader, device, threshold: float = 0.5) -> dict:
    """Compatibility dictionary; ap is primary, auprc is its legacy alias."""
    result = binary_metrics(*predict(model, loader, device), threshold).to_dict()
    return {**result, "auprc": result["ap"]}


@dataclass(frozen=True)
class ModuleRepresentations:
    features: dict[str, np.ndarray]
    labels: np.ndarray
    role: SplitRole

    def __iter__(self) -> Iterator:
        # Preserve feature/label unpacking for inspection, not unguarded scoring.
        yield self.features
        yield self.labels


def extract_features(model, loader, device) -> ModuleRepresentations:
    role = require_role(loader, {SplitRole.SOURCE_TRAIN, SplitRole.SOURCE_VALIDATION,
                                 SplitRole.TARGET_ADAPTATION}, "module representation extraction")
    model.to(device).eval()
    store, labels = {}, []
    with torch.no_grad():
        for views, y in loader:
            _, feats = model(move_views(views, device), return_features=True)
            for name, value in feats.items():
                store.setdefault(name, []).append(value.detach().cpu().numpy())
            labels.append(y.cpu().numpy())
    if not labels:
        raise ValueError("Cannot score an empty dataset")
    return ModuleRepresentations({k: np.concatenate(v, axis=0) for k, v in store.items()},
                                 np.concatenate(labels), role)


def select_threshold(y: np.ndarray, p: np.ndarray, partition: object) -> float:
    """Optional validation-only F1 threshold; ties choose the higher threshold."""
    require_role(partition, {SplitRole.SOURCE_VALIDATION, SplitRole.TARGET_VALIDATION}, "threshold selection")
    binary_metrics(y, p)  # validate before optimization
    candidates = np.unique(np.concatenate(([0.0, 0.5, 1.0], p)))
    return float(max(candidates, key=lambda t: (binary_metrics(y, p, t).f1 or 0.0, t)))
