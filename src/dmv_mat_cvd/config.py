from __future__ import annotations

from dataclasses import dataclass, field

from .transfer.calibration import CalibrationConfig
import math

SELECTOR_POLICIES = ("legacy_topk", "calibrated_threshold", "calibrated_logical")
SELECTOR_COMPARISON_MODES = (*SELECTOR_POLICIES, *("random_" + name for name in SELECTOR_POLICIES))
TRANSFER_MODES = ("head_only", "full", "fixed_mask", "dmv_mat", "random_mask")
DEFAULT_MODES = ("logistic_regression", "flat_mlp", "target_only", "source_only", *TRANSFER_MODES[:-1])
TRANSFER_MODES = (*TRANSFER_MODES, *SELECTOR_COMPARISON_MODES)
ALL_MODES = (*DEFAULT_MODES, "xgboost", "random_mask", *SELECTOR_COMPARISON_MODES)


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = 7
    source_train_fraction: float = 0.6
    source_validation_fraction: float = 0.2
    target_test_fraction: float = 0.25
    target_adaptation_fraction: float = 0.8
    target_event_budget: int | None = None
    batch_size: int = 256
    epochs_source: int = 40
    epochs_target: int = 20
    lr_source: float = 1e-3
    lr_head: float = 8e-4
    lr_full: float = 5e-4
    lr_selective: float = 7e-4
    lr_target_only: float = 1e-3
    patience: int = 8
    view_hidden: int = 16
    discrepancy_weight: float = 0.65
    adapt_fraction: float = 0.5  # fraction of modules, not target participants
    selector_policy: str | None = None
    selector_scope: str = "all"
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    random_budget_tolerance: float = .005
    fixed_mask: tuple[str, ...] = ("fusion1", "fusion2")
    preprocessing_policy: str = "source_fitted"
    mmd_normalize: bool = True
    mmd_max_samples: int = 1024
    threshold: float = 0.5
    threshold_policy: str = "fixed"  # fixed or validation_f1
    modes: tuple[str, ...] = DEFAULT_MODES
    device: str = "auto"
    output_dir: str = "results"
    publication_mode: bool = False
    exploratory_override: bool = False
    method_spec_version: str | None = None
    schema_version: str | None = None
    analysis_role: str = "secondary"
    cohort_inputs: dict | None = None

    def __post_init__(self) -> None:
        from .method import METHOD_SPEC_VERSION
        from .data.schema import SCHEMA_VERSION
        from .publication import validate_locked_config
        if not self.publication_mode:
            if self.selector_policy is None:
                object.__setattr__(self, "selector_policy", "legacy_topk")
            if self.method_spec_version is None:
                object.__setattr__(self, "method_spec_version", METHOD_SPEC_VERSION)
            if self.schema_version is None:
                object.__setattr__(self, "schema_version", SCHEMA_VERSION)
        if isinstance(self.calibration, dict):
            object.__setattr__(self, "calibration", CalibrationConfig(**self.calibration))
        validate_locked_config(self)
        if self.selector_policy not in SELECTOR_POLICIES or self.selector_scope not in {"all", "views"}:
            raise ValueError("Unknown selector policy or scope")
        if not 0 <= self.random_budget_tolerance <= .1:
            raise ValueError("Invalid random budget tolerance")
        if self.target_event_budget is not None and (
            type(self.target_event_budget) is not int or self.target_event_budget < 2
        ):
            raise ValueError("target_event_budget must be an integer >= 2 or None")
        if not self.modes or set(self.modes) - set(ALL_MODES) or len(set(self.modes)) != len(self.modes):
            raise ValueError("Choose unique known experiment modes")
        if self.preprocessing_policy not in {"source_fitted", "target_adaptation"}:
            raise ValueError("Unknown preprocessing policy")
        if self.threshold_policy not in {"fixed", "validation_f1"}:
            raise ValueError("Unknown threshold policy")
        if not 0 <= self.threshold <= 1 or not 0 <= self.adapt_fraction <= 1 or not 0 <= self.discrepancy_weight <= 1:
            raise ValueError("Threshold and selector fractions/weights must lie in [0, 1]")
        if (self.source_train_fraction <= 0 or self.source_validation_fraction <= 0
                or self.source_train_fraction + self.source_validation_fraction > 1):
            raise ValueError("Invalid source split fractions")
        if not 0 < self.target_test_fraction < 1 or not 0 < self.target_adaptation_fraction < 1:
            raise ValueError("Invalid target split fractions")
        for value in (self.lr_source, self.lr_head, self.lr_full, self.lr_selective, self.lr_target_only):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Learning rates must be finite and positive")
        if min(self.batch_size, self.epochs_source, self.epochs_target, self.patience, self.view_hidden) < 1:
            raise ValueError("Training sizes/epochs/patience must be positive")
        if self.mmd_max_samples < 2:
            raise ValueError("MMD requires at least two samples")
