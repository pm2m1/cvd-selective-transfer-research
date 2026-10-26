from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from importlib.metadata import version
from pathlib import Path
import random
import sys
import uuid

import numpy as np
import torch
from torch.utils.data import DataLoader

from ..config import ExperimentConfig, TRANSFER_MODES, SELECTOR_POLICIES, SELECTOR_COMPARISON_MODES
from ..method import SELECTOR_VERSIONS
from ..publication import prepare_publication, bind_target_test, verify_target_test, verify_configuration
from ..data.base import CohortPartition, CohortTable
from ..data.budgets import participant_fingerprint, sample_event_budget
from ..data.preprocessing import Preprocessor
from ..data.schema import SCHEMA_VERSION
from ..data.splitting import assert_disjoint, split_source, split_target
from ..evaluation import binary_metrics, extract_features, predict, select_threshold
from ..models.multiview_mlp import MultiViewRiskNet
from ..safeguards import AuditLog, SplitRole
from ..training import train_model
from ..transfer.adapt import adapt_model
from ..transfer.scores import score_modules
from ..transfer.calibration import calibrate_modules, calibrated_mask
from ..transfer.selector import normalize_scores, random_budget_mask, select_adaptation_mask, diverse_random_budget_mask
from .baselines import FlatMLP, fit_tabular, flatten, tabular_parameters


def choose_device(name: str = "auto") -> torch.device:
    if name != "auto":
        return torch.device(name)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def loader(dataset, batch: int = 256, shuffle: bool = False, seed: int = 0) -> DataLoader:
    return DataLoader(dataset, batch_size=batch, shuffle=shuffle, num_workers=0,
                      generator=torch.Generator().manual_seed(seed))


def observed(partition: CohortPartition) -> CohortPartition:
    frame = partition.cohort.records
    if "label" not in frame:
        raise ValueError("Construct canonical endpoints/labels before running an experiment")
    selected = frame.loc[frame.label.notna()]
    if selected.empty:
        raise ValueError(f"No observed binary endpoints in {partition.role.value}")
    return CohortPartition(CohortTable(selected, partition.cohort.domain), partition.role)


def parameter_summary(model, mask: dict[str, bool] | None = None, *, train_head: bool = True) -> dict:
    total = sum(p.numel() for p in model.parameters())
    if mask is None:
        count = sum(p.numel() for p in model.parameters() if p.requires_grad)
    else:
        count = sum(p.numel() for name, module in model.selectable_modules().items()
                    if mask.get(name, False) for p in module.parameters())
        if train_head:
            count += sum(p.numel() for p in model.head.parameters())
    return {"total_parameters": total, "adapted_parameter_count": count,
            "adapted_parameter_fraction": count / total}


def run_experiment(source: CohortTable, target: CohortTable,
                   config: ExperimentConfig | None = None) -> dict:
    """All fitting/selection finishes before the final target-test evaluation phase.

    Unknown and competing-death endpoints are excluded separately within each
    partition, and attrition is reported. This is a complete-case fixed-horizon
    classifier experiment, not competing-risk or censoring-adjusted estimation.
    """
    cfg = config or ExperimentConfig()
    publication_lock = prepare_publication(source, target, cfg)
    seed_everything(cfg.seed)
    device = choose_device(cfg.device)
    audit = AuditLog()
    partitions = {
        **split_source(source, cfg.source_train_fraction, cfg.source_validation_fraction, cfg.seed),
        **split_target(target, cfg.target_test_fraction, cfg.target_adaptation_fraction, cfg.seed + 1),
    }
    assert_disjoint(*partitions.values())
    test_binding = bind_target_test(publication_lock, partitions["target_test"])
    development = {name: observed(partition) for name, partition in partitions.items()
                   if partition.role not in {SplitRole.SOURCE_TEST, SplitRole.TARGET_TEST}}
    src_train, src_val = (development[name] for name in ("source_train", "source_validation"))
    tgt_train, tgt_val = (development[name] for name in ("target_adaptation", "target_validation"))
    if cfg.target_event_budget is not None:
        tgt_train = sample_event_budget(tgt_train, cfg.target_event_budget, cfg.seed + 200)
        audit.record("target_event_budget_selection", tgt_train)
    adaptation_fingerprint = participant_fingerprint(tgt_train)
    source_preprocessor = Preprocessor().fit(src_train)
    audit.record("fit_source_preprocessing", src_train)
    # Target-only baselines never use source preprocessing statistics.
    native_modes = {"logistic_regression", "xgboost", "flat_mlp", "target_only"}
    need_target_preprocessor = bool(native_modes.intersection(cfg.modes)) or cfg.preprocessing_policy == "target_adaptation"
    target_preprocessor = None
    if need_target_preprocessor:
        target_preprocessor = Preprocessor().fit(tgt_train)
        audit.record("fit_target_preprocessing", tgt_train)
    transfer_preprocessor = (source_preprocessor if cfg.preprocessing_policy == "source_fitted"
                             else target_preprocessor)
    source_train_ds, source_val_ds = (source_preprocessor.transform(p) for p in (src_train, src_val))
    target_train_ds, target_val_ds = (transfer_preprocessor.transform(p) for p in (tgt_train, tgt_val))
    dims = source_preprocessor.view_dims
    source_model = MultiViewRiskNet(dims, cfg.view_hidden)
    train_model(source_model, loader(source_train_ds, cfg.batch_size, True, cfg.seed),
                loader(source_val_ds, cfg.batch_size), device,
                epochs=cfg.epochs_source, lr=cfg.lr_source, patience=cfg.patience)
    audit.record("source_pretraining", src_train)
    audit.record("source_early_stopping", src_val)

    models, preprocessors, details = {"source_only": source_model}, {"source_only": source_preprocessor}, {}
    names = list(source_model.selectable_modules())
    details["source_only"] = {
        **parameter_summary(source_model, dict.fromkeys(names, False), train_head=False),
        "mask": dict.fromkeys(names, "SHARE"),
        "frozen_integrity": {"ok": True, "message": "source checkpoint used without target updates", "frozen_modules_checked": 0},
        "preprocessing_fit_role": "source_train",
    }
    module_rows, adaptive_mask, policy_masks, policy_reasons, calibration_rows = {}, {}, {}, {}, {}
    selection_modes = {"dmv_mat", "random_mask", *SELECTOR_COMPARISON_MODES}
    if selection_modes.intersection(cfg.modes):
        source_features = extract_features(source_model, loader(source_val_ds, cfg.batch_size), device)
        target_features = extract_features(source_model, loader(target_train_ds, cfg.batch_size), device)
        requested = {name.removeprefix("random_") for name in cfg.modes if name in SELECTOR_COMPARISON_MODES}
        if {"dmv_mat", "random_mask"}.intersection(cfg.modes):
            requested.add(cfg.selector_policy)
        scores = score_modules(source_features, target_features, max_samples=cfg.mmd_max_samples,
                               seed=cfg.seed, normalize=cfg.mmd_normalize,
                               allow_invalid_geometry="legacy_topk" not in requested)
        candidates = {name: value for name, value in scores.items()
                      if cfg.selector_scope == "all" or name.startswith("view:")}
        legacy_valid = all(v["discriminability"] is not None for v in scores.values())
        legacy_mask, adapt_scores = (select_adaptation_mask(candidates, cfg.discrepancy_weight, cfg.adapt_fraction)
                                    if legacy_valid else ({}, {}))
        policy_masks["legacy_topk"] = {name: legacy_mask.get(name, False) for name in names}
        policy_reasons["legacy_topk"] = {name: "legacy_rank" if name in candidates else "outside_scope" for name in names}
        requested = {name.removeprefix("random_") for name in cfg.modes if name in SELECTOR_COMPARISON_MODES}
        if {"dmv_mat", "random_mask"}.intersection(cfg.modes):
            requested.add(cfg.selector_policy)
        if requested - {"legacy_topk"}:
            calibration_rows = calibrate_modules(source_features, target_features, config=cfg.calibration,
                                                 max_samples=cfg.mmd_max_samples, seed=cfg.seed)
            for policy in sorted(requested - {"legacy_topk"}):
                selected, reasons = calibrated_mask({name: calibration_rows[name] for name in candidates},
                                                    policy, cfg.calibration)
                policy_masks[policy] = {name: selected.get(name, False) for name in names}
                policy_reasons[policy] = {name: reasons.get(name, "outside_scope") for name in names}
        adaptive_mask = policy_masks.get(cfg.selector_policy, policy_masks["legacy_topk"])
        scoped_normalized = normalize_scores(candidates) if legacy_valid else {}
        normalized = {stat: {name: scoped_normalized.get(stat, {}).get(name) for name in names}
                      for stat in ("mmd", "discriminability")}
        module_rows = {name: {**scores[name], "normalized_mmd": normalized["mmd"][name],
                              "normalized_discriminability": normalized["discriminability"][name],
                              "adapt_score": adapt_scores.get(name),
                              "decision": "ADAPT" if adaptive_mask[name] else "SHARE",
                              "parameters": sum(p.numel() for p in module.parameters())}
                       for name, module in source_model.selectable_modules().items()}
        audit.record("source_module_scoring", src_val)
        audit.record("target_module_scoring_and_mask_selection", tgt_train)
        if calibration_rows:
            audit.record("source_permutation_and_geometry_calibration", src_val)
            audit.record("target_permutation_and_geometry_calibration", tgt_train)
    if "fixed_mask" in cfg.modes and set(cfg.fixed_mask) - set(names):
        raise ValueError("Fixed mask contains an unknown module")

    for mode in cfg.modes:
        if mode == "source_only":
            continue
        # Re-seed each method and its loader: results do not depend on mode order.
        seed_everything(cfg.seed + 10)
        if mode in TRANSFER_MODES:
            mask = (adaptive_mask if mode == "dmv_mat" else
                    {name: mode == "full" or (mode == "fixed_mask" and name in cfg.fixed_mask) for name in names})
            random_diagnostics = {}
            if mode == "random_mask":
                mask, random_diagnostics = random_budget_mask(source_model, adaptive_mask, cfg.seed + 400)
            if mode in SELECTOR_POLICIES:
                mask = policy_masks[mode]
            elif mode in SELECTOR_COMPARISON_MODES:
                mask, random_diagnostics = diverse_random_budget_mask(
                    source_model, policy_masks[mode.removeprefix("random_")], cfg.seed + 400,
                    tolerance_fraction=cfg.random_budget_tolerance, views_only=cfg.selector_scope == "views")
            lr = cfg.lr_head if mode == "head_only" else cfg.lr_full if mode == "full" else cfg.lr_selective
            model, integrity = adapt_model(
                source_model, mask, loader(target_train_ds, cfg.batch_size, True, cfg.seed + 10),
                loader(target_val_ds, cfg.batch_size), device,
                epochs=cfg.epochs_target, lr=lr, patience=cfg.patience,
            )
            pp = transfer_preprocessor
            details[mode] = {**parameter_summary(model, mask),
                             "mask": {k: "ADAPT" if value else "SHARE" for k, value in mask.items()},
                             "frozen_integrity": integrity, **random_diagnostics}
        else:
            pp = target_preprocessor
            train_ds, val_ds = (pp.transform(p) for p in (tgt_train, tgt_val))
            if mode in {"logistic_regression", "xgboost"}:
                model = fit_tabular(mode, train_ds, cfg.seed)
                details[mode] = {"baseline_training": "target_adaptation", "hyperparameters": tabular_parameters(model)}
            else:
                model = (FlatMLP(pp.view_dims) if mode == "flat_mlp"
                         else MultiViewRiskNet(pp.view_dims, cfg.view_hidden))
                train_model(model, loader(train_ds, cfg.batch_size, True, cfg.seed + 10),
                            loader(val_ds, cfg.batch_size), device,
                            epochs=cfg.epochs_target, lr=cfg.lr_target_only, patience=cfg.patience)
                details[mode] = {"baseline_training": "target_adaptation",
                                 "trainable_parameters": sum(p.numel() for p in model.parameters())}
        models[mode], preprocessors[mode] = model, pp
        details[mode]["preprocessing_fit_role"] = pp.state["fit_role"]
        details[mode]["adaptation_participant_fingerprint"] = adaptation_fingerprint
        audit.record(f"{mode}_training", tgt_train)
        if mode not in {"logistic_regression", "xgboost"}:
            audit.record(f"{mode}_early_stopping", tgt_val)

    def probabilities(model, dataset):
        if isinstance(model, torch.nn.Module):
            return predict(model, loader(dataset, cfg.batch_size), device)
        return dataset.labels.numpy(), model.predict_proba(flatten(dataset))[:, 1]

    thresholds = {}
    for mode, model in models.items():
        if cfg.threshold_policy == "validation_f1":
            # Source-only remains untouched by target supervision, even for threshold choice.
            validation = src_val if mode == "source_only" else tgt_val
            y, p = probabilities(model, preprocessors[mode].transform(validation))
            thresholds[mode] = select_threshold(y, p, validation)
            audit.record(f"{mode}_threshold_selection", validation)
        else:
            thresholds[mode] = cfg.threshold

    verify_configuration(publication_lock, cfg)
    verify_target_test(test_binding, partitions["target_test"])
    # FINAL EVALUATION BOUNDARY. No fitting, model selection, or threshold updates below.
    audit.entries.append({"stage": "locked_test_evaluation_begins"})
    target_test = observed(partitions["target_test"])
    results = {}
    for mode, model in models.items():
        ds = preprocessors[mode].transform(target_test)
        results[mode] = binary_metrics(*probabilities(model, ds), thresholds[mode]).to_dict()
        audit.record(f"{mode}_test_evaluation", target_test)
    source_evaluation = {}
    for key in ("source_validation", "source_test"):
        if key in partitions:
            part = observed(partitions[key])
            source_evaluation[key] = binary_metrics(
                *probabilities(source_model, source_preprocessor.transform(part)), thresholds["source_only"]).to_dict()
            audit.record(f"{key}_evaluation", part)
    gains = {}
    for mode in TRANSFER_MODES:
        if mode in results:
            gain = {f"transfer_gain_{key}": (results[mode][key] - results["source_only"][key]
                    if results[mode][key] is not None and results["source_only"][key] is not None else None)
                    for key in ("ap", "auroc")}
            gain["negative_transfer_ap"] = None if gain["transfer_gain_ap"] is None else gain["transfer_gain_ap"] < 0
            gain["negative_transfer_auroc"] = None if gain["transfer_gain_auroc"] is None else gain["transfer_gain_auroc"] < 0
            gains[mode] = gain

    summaries = {}
    for name, part in partitions.items():
        frame = part.cohort.records
        labels = frame.label.dropna()
        summaries[name] = {"rows": len(frame), "participants": len(part.participant_ids),
                           "observed_rows": len(labels), "excluded_unobserved_rows": len(frame) - len(labels),
                           "prevalence": float(labels.mean()) if len(labels) else None,
                           "endpoint_status_counts": frame.endpoint_status.value_counts().to_dict()
                           if "endpoint_status" in frame else {}}
    verify_configuration(publication_lock, cfg)
    verify_target_test(test_binding, partitions["target_test"])
    experiment_id = (publication_lock["experiment_id"] if publication_lock else
                     f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}")
    output = publication_lock["output"] if publication_lock else Path(cfg.output_dir) / experiment_id
    if publication_lock is None:
        output.mkdir(parents=True, exist_ok=False)
    for mode, detail in details.items():
        policy = cfg.selector_policy if mode in {"dmv_mat", "random_mask"} else mode.removeprefix("random_")
        detail["selector_name"] = policy if policy in SELECTOR_VERSIONS else None
        detail["selector_version"] = SELECTOR_VERSIONS.get(policy)
        if mode.startswith("random_"):
            detail["mask_generator_version"] = "exact-budget-m2-v1" if mode == "random_mask" else "near-budget-m3-v1"
            detail["reference_selector_name"] = policy
            detail["reference_selector_version"] = SELECTOR_VERSIONS[policy]
            detail["selector_name"] = mode
            detail["selector_version"] = detail["mask_generator_version"]
    result = {
        "experiment_id": experiment_id, "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": cfg.seed, "source_domain": source.domain, "target_domain": target.domain,
        "schema_version": SCHEMA_VERSION, "method_spec_version": cfg.method_spec_version,
        "selector_name": cfg.selector_policy, "selector_version": SELECTOR_VERSIONS[cfg.selector_policy],
        "publication_lock": publication_lock["snapshot"] if publication_lock else None,
        "locked_target_test": test_binding, "config": asdict(cfg), "device": str(device),
        "versions": {"python": sys.version.split()[0],
                     **{name: version(name) for name in ("numpy", "pandas", "scikit-learn", "torch")},
                     **({"xgboost": version("xgboost")} if "xgboost" in cfg.modes else {})},
        "splits": summaries, "adaptation_size": len(tgt_train),
        "adaptation_events": int(tgt_train.cohort.records.label.sum()),
        "adaptation_participant_fingerprint": adaptation_fingerprint,
        "model_configuration": {"view_dims": dims, "view_hidden": cfg.view_hidden, "fusion_dims": [64, 32]},
        "preprocessing_policy": cfg.preprocessing_policy,
        "selector": "re-engineered DMV-MAT-style selector",
        "mmd_normalization": "source_rms_radius" if cfg.mmd_normalize else "legacy_raw",
        "selector_policy": cfg.selector_policy, "selector_scope": cfg.selector_scope,
        "calibration_scores": calibration_rows, "policy_masks": policy_masks, "policy_reasons": policy_reasons,
        "module_scores": module_rows, "methods": details,
        "source_evaluation": source_evaluation, "target_metrics": results,
        "transfer_gains": gains, "audit_log": audit.entries, "output_directory": str(output),
    }
    source_preprocessor.save(output / "preprocessing_source.json")
    if target_preprocessor is not None:
        target_preprocessor.save(output / "preprocessing_target.json")
    for mode, model in models.items():
        if isinstance(model, torch.nn.Module):
            torch.save({key: value.detach().cpu() for key, value in model.state_dict().items()}, output / f"{mode}.pt")
    (output / "results.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with (output / "metrics.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["method", "method_spec_version", "schema_version", "selector_name", "selector_version", *next(iter(results.values()))])
        writer.writeheader()
        writer.writerows({"method": name, "method_spec_version": cfg.method_spec_version, "schema_version": SCHEMA_VERSION,
                          "selector_name": details[name]["selector_name"], "selector_version": details[name]["selector_version"],
                          **values} for name, values in results.items())
    if module_rows:
        with (output / "module_scores.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["module", *next(iter(module_rows.values()))])
            writer.writeheader()
            writer.writerows({"module": name, **values} for name, values in module_rows.items())
    return result
