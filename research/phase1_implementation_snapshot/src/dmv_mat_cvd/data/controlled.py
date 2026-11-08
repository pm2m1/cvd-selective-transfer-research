"""Synthetic additive teacher with declared view-local predictive mechanisms.

Ground truth describes the teacher's local factorization, not unique optimal
weight updates in the learned MLP. Fusion ground truth is intentionally absent.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .base import CohortTable
from .schema import VIEW_FEATURES

VIEWS = tuple(VIEW_FEATURES)


@dataclass(frozen=True)
class ShiftScenario:
    name: str
    mechanism: str = "none"
    shifted_views: tuple[str, ...] = ()
    magnitude: float = 1.0
    teacher_variant: str = "linear"
    concept_multiplier: float | None = None

    def __post_init__(self) -> None:
        if self.mechanism not in {"none", "measurement", "concept", "nuisance", "rotation"}:
            raise ValueError("Unknown controlled shift mechanism")
        if set(self.shifted_views) - set(VIEWS) or len(set(self.shifted_views)) != len(self.shifted_views):
            raise ValueError("Shifted views must be unique canonical view names")
        if (self.mechanism == "none") != (len(self.shifted_views) == 0):
            raise ValueError("No-shift requires no shifted views; other mechanisms require views")
        if not np.isfinite(self.magnitude) or self.magnitude <= 0:
            raise ValueError("Shift magnitude must be finite and positive")
        if self.teacher_variant not in {"linear", "saturating"}:
            raise ValueError("Unknown synthetic teacher variation")
        if self.concept_multiplier is not None and (self.mechanism != "concept" or not np.isfinite(self.concept_multiplier) or self.concept_multiplier == 1):
            raise ValueError("Concept multiplier requires an actual finite concept change")
        if self.mechanism == "rotation" and (set(self.shifted_views) - {"haemodynamic", "metabolic"} or self.magnitude > np.pi):
            raise ValueError("Rotation applies to haemodynamic/metabolic views, angle in (0, pi]")
        if self.mechanism == "nuisance" and self.shifted_views != ("haemodynamic",):
            raise ValueError("The nuisance control changes only nonpredictive DBP")

    @property
    def ground_truth(self) -> dict[str, bool | None]:
        return {**{f"view:{name}": self.mechanism in {"measurement", "concept", "rotation"}
                   and name in self.shifted_views for name in VIEWS},
                "fusion1": None, "fusion2": None}


SCENARIOS = {
    "A_no_shift": ShiftScenario("A_no_shift"),
    "B_haemodynamic": ShiftScenario("B_haemodynamic", "measurement", ("haemodynamic",)),
    "C_haemodynamic_metabolic": ShiftScenario("C_haemodynamic_metabolic", "measurement", ("haemodynamic", "metabolic")),
    "D_behaviour": ShiftScenario("D_behaviour", "measurement", ("behaviour",)),
    "E_broad": ShiftScenario("E_broad", "measurement", VIEWS),
    "F_concept": ShiftScenario("F_concept", "concept", ("haemodynamic",)),
    "G_nuisance_control": ShiftScenario("G_nuisance_control", "nuisance", ("haemodynamic",)),
}


def teacher_components(records: pd.DataFrame, scenario: ShiftScenario, domain: str) -> np.ndarray:
    """Exact per-view logit contributions as a function of observed predictors."""
    if domain not in {"source", "target"}:
        raise ValueError("domain must be source or target")
    smoking = records.smoking_status.map({"never": 0, "former": 1, "current": 2}).to_numpy()
    treatment = records.antihypertensive_treatment.map({"no": 0, "yes": 1}).to_numpy()
    signals = np.column_stack(((records.age - 55) / 8, (records.sbp - 125) / 15,
                               (records.bmi - 27) / 4, smoking, treatment)).astype(float)
    if domain == "target" and scenario.mechanism == "measurement":
        for name in scenario.shifted_views:
            index = VIEWS.index(name)
            if name == "behaviour":
                signals[:, index] = (signals[:, index] - 1) % 3
            elif name == "comorbidity_medication":
                signals[:, index] = 1 - signals[:, index]
            else:
                signals[:, index] = scenario.magnitude - signals[:, index]
    if domain == "target" and scenario.mechanism == "rotation":
        for name in scenario.shifted_views:
            index = VIEWS.index(name)
            auxiliary = (records.dbp - 78) / 8 if name == "haemodynamic" else (records.fasting_glucose - 100) / 12
            signals[:, index] = np.cos(scenario.magnitude) * signals[:, index] - np.sin(scenario.magnitude) * auxiliary
    # Source category probabilities: smoking (.5, .3, .2), treatment (.7, .3).
    signals[:, 3] = (signals[:, 3] - .7) / np.sqrt(.61)
    signals[:, 4] = (signals[:, 4] - .3) / np.sqrt(.21)
    if scenario.teacher_variant == "saturating":
        signals = 1.4 * np.tanh(signals)
    coefficients = np.array([.6, .9, .8, .6, .7])
    if domain == "target" and scenario.mechanism == "concept":
        for name in scenario.shifted_views:
            coefficients[VIEWS.index(name)] *= (-scenario.magnitude if scenario.concept_multiplier is None else scenario.concept_multiplier)
    return signals * coefficients


def generate_controlled_cohort(n: int, domain: str, seed: int,
                               scenario: ShiftScenario) -> CohortTable:
    if n < 1 or domain not in {"source", "target"}:
        raise ValueError("Positive n and source/target domain required")
    rng = np.random.default_rng(seed)
    signals = rng.uniform(-np.sqrt(3), np.sqrt(3), size=(n, 3))
    nuisance = rng.normal(size=(n, 5))
    smoking = rng.choice(3, n, p=[.5, .3, .2])
    treatment = rng.binomial(1, .3, n)
    frame = pd.DataFrame({
        "participant_id": [f"controlled-{domain}-{seed}-{i}" for i in range(n)],
        "age": 55 + 8 * signals[:, 0], "sex": np.where(nuisance[:, 0] > 0, "male", "female"),
        "sbp": 125 + 15 * signals[:, 1], "dbp": 78 + 8 * nuisance[:, 1],
        "bmi": 27 + 4 * signals[:, 2], "fasting_glucose": 100 + 12 * nuisance[:, 2],
        "total_cholesterol": 195 + 20 * nuisance[:, 3], "hdl": 52 + 6 * nuisance[:, 4],
        "smoking_status": np.array(["never", "former", "current"])[smoking],
        "antihypertensive_treatment": np.where(treatment, "yes", "no"),
    })
    if domain == "target" and scenario.mechanism == "measurement":
        for name in scenario.shifted_views:
            if name in VIEWS[:3]:
                column, center, scale = {"background": ("age", 55, 8),
                                         "haemodynamic": ("sbp", 125, 15),
                                         "metabolic": ("bmi", 27, 4)}[name]
                frame[column] = center + scale * (scenario.magnitude - (frame[column] - center) / scale)
            elif name == "behaviour":
                frame["smoking_status"] = np.array(["never", "former", "current"])[(smoking + 1) % 3]
            else:
                frame["antihypertensive_treatment"] = np.where(1 - treatment, "yes", "no")
    if domain == "target" and scenario.mechanism == "rotation":
        for name in scenario.shifted_views:
            primary, auxiliary, center, scale, acenter, ascale = (
                ("sbp", "dbp", 125, 15, 78, 8) if name == "haemodynamic"
                else ("bmi", "fasting_glucose", 27, 4, 100, 12))
            a, b = (frame[primary] - center) / scale, (frame[auxiliary] - acenter) / ascale
            frame[primary] = center + scale * (np.cos(scenario.magnitude) * a + np.sin(scenario.magnitude) * b)
            frame[auxiliary] = acenter + ascale * (-np.sin(scenario.magnitude) * a + np.cos(scenario.magnitude) * b)
    if domain == "target" and scenario.mechanism == "nuisance":
        frame["dbp"] += 8 * scenario.magnitude
    logits = -1.1 + teacher_components(frame, scenario, domain).sum(axis=1)
    labels = (rng.random(n) < 1 / (1 + np.exp(-logits))).astype(int)
    frame["index_date"] = "2000-01-01"
    frame["event_type"] = np.where(labels, "mi", None)
    frame["event_time_days"] = np.where(labels, rng.integers(1, 1827, n), np.nan)
    frame["death_time_days"] = np.nan
    frame["last_followup_days"] = 2200.0
    frame["death_is_nonqualifying"] = False
    frame["endpoint_status"] = np.where(labels, "positive", "known_negative")
    frame["label"] = labels
    return CohortTable(frame, f"controlled_{domain}")
