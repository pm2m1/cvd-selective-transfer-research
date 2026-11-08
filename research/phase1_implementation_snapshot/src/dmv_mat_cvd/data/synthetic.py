from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from .base import CohortTable, MultiViewDataset
from ..safeguards import SplitRole


# Legacy array generator retained verbatim as a regression fixture. New experiments
# use generate_cohort and infer dimensions from fitted canonical preprocessing.
VIEW_DIMS = {
    "background": 4,
    "haemodynamic": 4,
    "metabolic": 5,
    "lifestyle": 3,
    "comorbidity": 4,
}


@dataclass
class SyntheticDomainConfig:
    n: int
    domain: str
    seed: int


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate_domain(cfg: SyntheticDomainConfig) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
    """Generate a source or target cohort with controlled per-view domain shift.

    The disease label is produced from latent risk factors. The target cohort changes
    observation distributions and slightly changes two risk relationships so that a
    source model experiences realistic covariate/concept shift.
    """
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n

    z = {
        "background": rng.normal(size=n),
        "haemodynamic": rng.normal(size=n),
        "metabolic": rng.normal(size=n),
        "lifestyle": rng.normal(size=n),
        "comorbidity": rng.normal(size=n),
    }

    if cfg.domain == "source":
        beta = np.array([0.50, 1.10, 1.00, 0.55, 0.90])
        mean_shifts = dict(background=0.0, haemodynamic=0.0, metabolic=0.0, lifestyle=0.0, comorbidity=0.0)
        scales = dict(background=1.0, haemodynamic=1.0, metabolic=1.0, lifestyle=1.0, comorbidity=1.0)
        noise = dict(background=0.65, haemodynamic=0.55, metabolic=0.55, lifestyle=0.75, comorbidity=0.60)
    elif cfg.domain == "target":
        beta = np.array([0.45, 1.35, 0.75, 0.50, 1.20])
        mean_shifts = dict(background=0.15, haemodynamic=0.80, metabolic=1.10, lifestyle=0.25, comorbidity=0.95)
        scales = dict(background=1.05, haemodynamic=1.30, metabolic=0.80, lifestyle=1.10, comorbidity=1.25)
        noise = dict(background=0.70, haemodynamic=0.75, metabolic=0.80, lifestyle=0.80, comorbidity=0.85)
    else:
        raise ValueError("domain must be 'source' or 'target'")

    latent = np.column_stack([z[k] for k in VIEW_DIMS])
    logits = latent @ beta - 0.30 + rng.normal(scale=0.45, size=n)
    p = _sigmoid(logits)
    y = rng.binomial(1, p, size=n).astype(np.int64)

    views: Dict[str, np.ndarray] = {}
    for i, (name, dim) in enumerate(VIEW_DIMS.items()):
        base = z[name][:, None]
        loadings = np.linspace(0.75, 1.25, dim)[None, :]
        eps = rng.normal(scale=noise[name], size=(n, dim))
        x = base * loadings + eps
        x = x * scales[name] + mean_shifts[name]

        # Mild nonlinear distortions in the two most shifted target views.
        if cfg.domain == "target" and name == "metabolic":
            x[:, 0] = np.tanh(x[:, 0]) * 1.8
            x[:, -1] = np.square(np.clip(x[:, -1], -2.0, 2.0)) - 0.8
        if cfg.domain == "target" and name == "comorbidity":
            x[:, 1] = np.sign(x[:, 1]) * np.sqrt(np.abs(x[:, 1]) + 1e-6)

        views[name] = x.astype(np.float32)

    return views, y


def split_views(
    views: Dict[str, np.ndarray],
    labels: np.ndarray,
    fractions=(0.6, 0.2, 0.2),
    seed: int = 0,
    roles=(SplitRole.SOURCE_TRAIN, SplitRole.SOURCE_VALIDATION, SplitRole.SOURCE_TEST),
):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(labels))
    n_train = int(fractions[0] * len(idx))
    n_val = int(fractions[1] * len(idx))
    parts = [idx[:n_train], idx[n_train:n_train + n_val], idx[n_train + n_val:]]

    out = []
    for p, role in zip(parts, roles):
        out.append(MultiViewDataset({k: v[p] for k, v in views.items()}, labels[p], role))
    return tuple(out)


def generate_cohort(cfg: SyntheticDomainConfig) -> CohortTable:
    """Canonical synthetic records, NOT simulated ARIC/MESA participants.

    Retains the original latent risk/shift generator. Numeric rescalings below
    are test-fixture choices in canonical units, not cohort distribution claims.
    """
    if cfg.n < 1:
        raise ValueError("Synthetic cohort size must be positive")
    views, labels = generate_domain(cfg)
    background, pressure, metabolic = (views[k] for k in ("background", "haemodynamic", "metabolic"))
    smoking = views["lifestyle"][:, 0]
    rng = np.random.default_rng(cfg.seed + 10000)
    frame = pd.DataFrame({
        "participant_id": [f"synthetic-{cfg.domain}-{cfg.seed}-{i}" for i in range(cfg.n)],
        "age": np.clip(55 + 9 * background[:, 0], 30, 90),
        "sex": np.where(background[:, 1] > 0, "male", "female"),
        "sbp": np.clip(125 + 16 * pressure[:, 0], 75, 240),
        "dbp": np.clip(78 + 9 * pressure[:, 1], 40, 140),
        "bmi": np.clip(27 + 4 * metabolic[:, 0], 15, 55),
        "fasting_glucose": np.clip(100 + 20 * metabolic[:, 1], 45, 350),
        "total_cholesterol": np.clip(195 + 30 * metabolic[:, 2], 70, 400),
        "hdl": np.clip(52 - 9 * metabolic[:, 3], 15, 120),
        "smoking_status": np.select([smoking < -0.4, smoking < 0.7], ["never", "former"], default="current"),
        "antihypertensive_treatment": np.where(views["comorbidity"][:, 0] > 0.2, "yes", "no"),
        "index_date": "2000-01-01",
        "event_type": np.where(labels == 1, "mi", None),
        "event_time_days": np.where(labels == 1, rng.integers(1, 1827, cfg.n), np.nan),
        "death_time_days": np.nan,
        "last_followup_days": 2200.0,
        "death_is_nonqualifying": False,
        "endpoint_status": np.where(labels == 1, "positive", "known_negative"),
        "label": labels,
    })
    return CohortTable(frame, f"synthetic_{cfg.domain}")
