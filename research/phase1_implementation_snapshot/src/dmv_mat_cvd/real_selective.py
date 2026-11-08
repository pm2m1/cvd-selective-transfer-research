"""Registered Milestone 6B selective adaptation on locked development rows only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import time

import numpy as np
import pandas as pd
import torch

from .data.public_preprocessing import CATEGORIES, CONTINUOUS, PublicPreprocessor
from .data.public_v2 import VIEWS_TEN
from .data.releases import file_sha256
from .evaluation import binary_metrics, extract_features, predict
from .experiments.runner import loader, seed_everything
from .experiments.validation_metrics import pairwise_mask_jaccard
from .method import SELECTOR_VERSIONS
from .models.multiview_mlp import MultiViewRiskNet
from .real_baselines import LOCK_SHA256, ASSIGNMENTS_SHA256, _part, load_verified_development
from .safeguards import SplitRole
from .transfer.adapt import adapt_model
from .transfer.calibration import CalibrationConfig, calibrate_modules, calibrated_mask
from .transfer.scores import score_modules
from .transfer.selector import diverse_random_budget_mask, select_adaptation_mask

BASELINE = Path("results/real_training/m6a_20261025_dev_baselines_v4")


def verify_registration(path: Path) -> dict:
    record = json.loads(path.read_text())
    if (record.get("registration_version") != "m6b-selective-adaptation-v1" or
            record.get("status") != "registered_before_6b_validation_training" or
            record.get("protocol_version") != "public-haalsi-mhas-v2" or
            record.get("schema_version") != "cvd-public-wave-v2-ten-doctor-report" or
            record.get("seed") != 20261025 or
            record.get("lock_sha256") != LOCK_SHA256 or
            record.get("private_assignments_sha256") != ASSIGNMENTS_SHA256 or
            record.get("fixed_mask") != ["fusion1", "fusion2"] or
            record.get("methods") != ["fixed_mask", "random_calibrated_logical",
                                       "legacy_topk", "calibrated_threshold", "calibrated_logical"] or
            record.get("repetitions") != list(range(10)) or
            record.get("budgets") != {"primary_25_75": [25, 75], "low_label_10_30": [10, 30]}):
        raise ValueError("Run-specific 6B registration differs from prespecified public experiment")
    expected = {
        "selector": "src/dmv_mat_cvd/transfer/selector.py",
        "calibration": "src/dmv_mat_cvd/transfer/calibration.py",
        "scores": "src/dmv_mat_cvd/transfer/scores.py",
        "adapt": "src/dmv_mat_cvd/transfer/adapt.py",
    }
    if any(file_sha256(Path(value)) != record["selector_code_sha256"][name]
           for name, value in expected.items()):
        raise ValueError("Registered selector/scoring/adaptation code changed")
    if file_sha256(Path("src/dmv_mat_cvd/models/multiview_mlp.py")) != record["model_code_sha256"]:
        raise ValueError("Registered five-view architecture changed")
    required = {"baseline_source_checkpoint_sha256": BASELINE / "checkpoints/source_multiview.pt",
                "baseline_source_preprocessor_sha256": BASELINE / "preprocessing/source_train.json",
                "baseline_metrics_sha256": BASELINE / "development_metrics.csv"}
    if any(file_sha256(file) != record[key] for key, file in required.items()):
        raise ValueError("Required Milestone 6A baseline artifact differs")
    manifest = json.loads((BASELINE / "run_manifest.json").read_text())
    if (manifest["lock_sha256"] != LOCK_SHA256 or
            manifest["private_assignments_sha256"] != ASSIGNMENTS_SHA256 or
            manifest["view_dimensions"] != {"background": 4, "haemodynamic": 2,
                                            "metabolic": 3, "behaviour": 4,
                                            "comorbidity_medication": 6}):
        raise ValueError("Milestone 6A manifest is incompatible with the registered run")
    baseline = pd.read_csv(BASELINE / "development_metrics.csv")
    for row in baseline.drop_duplicates("checkpoint").itertuples():
        if file_sha256(BASELINE / "checkpoints" / row.checkpoint) != row.checkpoint_sha256:
            raise ValueError("A Milestone 6A checkpoint changed or is missing")
    if baseline.checkpoint.nunique() != 84:
        raise ValueError("The authoritative Milestone 6A checkpoint set is incomplete")
    for budget in record["budgets"]:
        for method in ("head_only", "full_finetune"):
            subset = baseline.loc[(baseline.stage == "target_validation") &
                                  (baseline.budget == budget) & (baseline.method == method)]
            if len(subset) != 10 or set(subset.repetition.astype(int)) != set(range(10)):
                raise ValueError("Milestone 6A paired head/full reference is incomplete")
            expected_n = 100 if budget == "primary_25_75" else 40
            if not subset.train_n.eq(expected_n).all() or not subset.validation_n.eq(171).all():
                raise ValueError("Milestone 6A reference label access differs")
    return record


def load_frozen_source_preprocessor(path: Path, expected: dict) -> PublicPreprocessor:
    saved = json.loads(path.read_text())
    if (saved.get("schema_version") != "cvd-public-wave-v2-ten-doctor-report" or
            saved.get("fit_role") != "source_train" or
            saved.get("views") != {k: list(v) for k, v in VIEWS_TEN.items()} or
            saved.get("categories") != {k: list(v) + ["unknown"] for k, v in CATEGORIES.items()} or
            set(saved.get("continuous", {})) != set(CONTINUOUS)):
        raise ValueError("Saved source preprocessing contract changed")
    for values in saved["continuous"].values():
        if not all(np.isfinite(values[k]) for k in ("median", "mean", "scale")) or values["scale"] <= 0:
            raise ValueError("Saved source preprocessing statistics invalid")
    pp = PublicPreprocessor()
    pp.state = {k: v for k, v in saved.items() if k != "encoded_columns"}
    if pp.encoded_columns != saved.get("encoded_columns") or pp.view_dims != expected:
        raise ValueError("Saved preprocessing feature order or dimensions changed")
    return pp


def source_model_from_checkpoint(path: Path, dimensions: dict) -> MultiViewRiskNet:
    model = MultiViewRiskNet(dimensions, view_hidden=16)
    model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True), strict=True)
    model.eval()
    return model


def mask_effect(model: MultiViewRiskNet, source: MultiViewRiskNet,
                mask: dict[str, bool]) -> dict:
    """Verify trainability, actual selected updates and frozen tensors."""
    if set(mask) != set(source.selectable_modules()):
        raise ValueError("Mask must cover all seven frozen selectable modules")
    expected_trainable = sum(p.numel() for p in model.head.parameters()) + sum(
        p.numel() for name, module in model.selectable_modules().items() if mask[name]
        for p in module.parameters())
    actual_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    if expected_trainable != actual_trainable:
        raise RuntimeError("Optimizer trainability differs from selected mask")
    updates = {}
    for name, source_module in source.selectable_modules().items():
        actual_module = model.selectable_modules()[name]
        if any(p.requires_grad != mask[name] for p in actual_module.parameters()):
            raise RuntimeError("Module requires_grad does not match selection mask")
        changed = any(not torch.equal(value.detach().cpu(), actual_module.state_dict()[key].detach().cpu())
                      for key, value in source_module.state_dict().items())
        if changed != mask[name]:
            raise RuntimeError(f"Module update does not match ADAPT/SHARE decision: {name}")
        updates[name] = changed
    head_changed = any(not torch.equal(value.detach().cpu(), model.head.state_dict()[key].detach().cpu())
                       for key, value in source.head.state_dict().items())
    if not head_changed or not all(p.requires_grad for p in model.head.parameters()):
        raise RuntimeError("Prediction head did not update")
    return {"trainable_parameters": actual_trainable, "selected_module_updates": updates,
            "head_updated": True, "mask_enforced": True}


def _jsonable(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    raise TypeError(type(value).__name__)


def _summarize(per_run: pd.DataFrame, masks: pd.DataFrame, baseline: pd.DataFrame) -> dict:
    output = {"by_budget_method": {}, "paired_differences": {}, "mask_stability": {},
              "module_selection_frequency": {}}
    for (budget, method), group in per_run.groupby(["budget", "method"], sort=True):
        key = f"{budget}:{method}"
        output["by_budget_method"][key] = {}
        for field in ("ap", "auroc", "brier", "trainable_parameters", "adapted_fraction", "fit_seconds"):
            values = group[field].dropna().to_numpy(dtype=float)
            output["by_budget_method"][key][field] = {
                "n": len(values), "mean": float(values.mean()) if len(values) else None,
                "sd": float(values.std(ddof=1)) if len(values)>1 else None,
                "median": float(np.median(values)) if len(values) else None,
                "min": float(values.min()) if len(values) else None,
                "max": float(values.max()) if len(values) else None}
        mm=masks.loc[(masks.budget==budget)&(masks.method==method)]
        parsed=[json.loads(x) for x in mm.mask_json]
        output["mask_stability"][key]=pairwise_mask_jaccard(parsed)
        output["module_selection_frequency"][key]={name:sum(mask[name] for mask in parsed)/len(parsed)
            for name in parsed[0]} if parsed else {}
        comparisons={"head_only":baseline.loc[(baseline.budget==budget)&(baseline.method=="head_only")],
                     "full_finetune":baseline.loc[(baseline.budget==budget)&(baseline.method=="full_finetune")]}
        if method!="random_calibrated_logical":
            comparisons["random_calibrated_logical"]=per_run.loc[(per_run.budget==budget)&
                                                           (per_run.method=="random_calibrated_logical")]
        for reference, rows in comparisons.items():
            joined=group[["repetition","ap"]].merge(rows[["repetition","ap"]],on="repetition",
                                                       suffixes=("_selector","_reference"),validate="one_to_one")
            if len(joined)!=10:
                raise ValueError("Paired baseline comparison lost a stored draw")
            differences=joined.ap_selector.to_numpy()-joined.ap_reference.to_numpy()
            output["paired_differences"][f"{key}:vs:{reference}"]={
                "mean":float(differences.mean()),"median":float(np.median(differences)),
                "sd":float(differences.std(ddof=1)),"min":float(differences.min()),
                "max":float(differences.max()),"n":len(differences)}
    return output


def run(data_root: Path, master_file: Path, questionnaire: Path, output: Path) -> dict:
    registration_path=output/"experiment_registration.json"
    registration=verify_registration(registration_path)
    pre_registration_sha=file_sha256(registration_path)
    if (output/"per_run.csv").exists() or (output/"checkpoints").exists():
        raise FileExistsError("Milestone 6B run already started; do not overwrite or rerun masks")
    source, target, assignments, snapshot, counts, *_ = load_verified_development(
        data_root, master_file, questionnaire)
    if (file_sha256(data_root/"private_locks/public-haalsi-mhas-v2/target_lock.json") != LOCK_SHA256 or
            file_sha256(data_root/"private_locks/public-haalsi-mhas-v2/participant_assignments.private.json") != ASSIGNMENTS_SHA256):
        raise ValueError("Target lock changed before selector training")
    settings=registration["training"]
    calibration=CalibrationConfig(**{k:v for k,v in registration["calibration"].items()
                                   if k!="max_samples_per_domain"})
    pp=load_frozen_source_preprocessor(BASELINE/"preprocessing/source_train.json",
                                      json.loads((BASELINE/"run_manifest.json").read_text())["view_dimensions"])
    model=source_model_from_checkpoint(BASELINE/"checkpoints/source_multiview.pt",pp.view_dims)
    source_checkpoint_sha=file_sha256(BASELINE/"checkpoints/source_multiview.pt")
    sp,tp=assignments["source_partitions"],assignments["target_partitions"]
    source_validation=_part(source,set(sp["source_validation"]),SplitRole.SOURCE_VALIDATION)
    target_validation=_part(target,set(tp["target_validation"]),SplitRole.TARGET_VALIDATION)
    source_ds=pp.transform(source_validation,SplitRole.SOURCE_VALIDATION)
    target_val_ds=pp.transform(target_validation,SplitRole.TARGET_VALIDATION)
    baseline=pd.read_csv(BASELINE/"development_metrics.csv")
    source_features=extract_features(model,loader(source_ds,settings["batch_size"]),torch.device("cpu"))
    if len(source_features.labels)!=581 or int(source_features.labels.sum())!=21:
        raise ValueError("Source selector evidence differs from locked validation")
    torch.set_num_threads(2)
    (output/"checkpoints").mkdir()
    run_rows=[]; mask_rows=[]; score_rows=[]; failures=[]
    module_names=list(model.selectable_modules())
    total_parameters=sum(p.numel() for p in model.parameters())
    for budget_index,budget in enumerate(registration["budgets"]):
        wanted_events,wanted_nonevents=registration["budgets"][budget]
        for repetition in registration["repetitions"]:
            draw=set(assignments["adaptation_draws"][str(repetition)][budget])
            adapt=_part(target,draw,SplitRole.TARGET_ADAPTATION)
            if len(adapt)!=wanted_events+wanted_nonevents or int(adapt.label.sum())!=wanted_events:
                raise ValueError("Stored adaptation draw differs from registered label budget")
            target_ds=pp.transform(adapt,SplitRole.TARGET_ADAPTATION)
            target_features=extract_features(model,loader(target_ds,settings["batch_size"]),torch.device("cpu"))
            score_seed=registration["seed"]+repetition+1000*budget_index
            raw=score_modules(source_features,target_features,max_samples=registration["legacy_rule"]["mmd_max_samples"],
                              seed=score_seed,normalize=True,allow_invalid_geometry=True)
            calibrated=calibrate_modules(source_features,target_features,config=calibration,
                     max_samples=registration["calibration"]["max_samples_per_domain"],seed=score_seed)
            if any(raw[name]["discriminability"] is None for name in module_names):
                raise ValueError("Legacy selector geometry invalid; fixed registered comparison cannot complete")
            legacy,legacy_scores=select_adaptation_mask(raw,
                discrepancy_weight=registration["legacy_rule"]["discrepancy_weight"],
                adapt_fraction=registration["legacy_rule"]["adapt_fraction"])
            threshold,threshold_reason=calibrated_mask(calibrated,"calibrated_threshold",calibration)
            logical,logical_reason=calibrated_mask(calibrated,"calibrated_logical",calibration)
            fixed={name:name in registration["fixed_mask"] for name in module_names}
            random_seed=registration["seed"]+400+repetition+1000*budget_index
            random_mask,random_details=diverse_random_budget_mask(model,logical,random_seed,
                tolerance_fraction=registration["random_budget_tolerance_fraction"])
            masks={"fixed_mask":fixed,"random_calibrated_logical":random_mask,
                   "legacy_topk":legacy,"calibrated_threshold":threshold,"calibrated_logical":logical}
            for name in module_names:
                score_rows.append({"budget":budget,"repetition":repetition,"module":name,
                    **raw[name],**calibrated[name],"legacy_adapt_score":legacy_scores[name],
                    "fixed_decision":fixed[name],"random_decision":random_mask[name],
                    "legacy_decision":legacy[name],"threshold_decision":threshold[name],
                    "logical_decision":logical[name],"threshold_reason":threshold_reason[name],
                    "logical_reason":logical_reason[name]})
            for method in registration["methods"]:
                mask=masks[method]
                seed=registration["seed"]+repetition
                if method=="random_calibrated_logical":
                    seed=registration["seed"]+repetition  # mask RNG is independent of optimizer RNG
                seed_everything(seed)
                t0=time.monotonic()
                adapted,integrity=adapt_model(model,mask,
                    loader(target_ds,settings["batch_size"],True,seed),
                    loader(target_val_ds,settings["batch_size"]),torch.device("cpu"),
                    epochs=settings["epochs_target"],lr=settings["learning_rate"],
                    patience=settings["patience"])
                elapsed=time.monotonic()-t0
                if not integrity["ok"]:
                    raise RuntimeError("Frozen-weight check failed")
                effect=mask_effect(adapted,model,mask)
                y,p=predict(adapted,loader(target_val_ds,settings["batch_size"]),torch.device("cpu"))
                metrics=binary_metrics(y,p).to_dict()
                if len(y)!=171 or int(y.sum())!=13:
                    raise ValueError("MHAS validation observation count differs")
                checkpoint=f"{method}_{budget}_rep{repetition}.pt"
                torch.save(adapted.state_dict(),output/"checkpoints"/checkpoint)
                checkpoint_sha=file_sha256(output/"checkpoints"/checkpoint)
                selected=[name for name in module_names if mask[name]]
                mask_rows.append({"budget":budget,"repetition":repetition,"method":method,
                   "selector_version":SELECTOR_VERSIONS.get(method,"prespecified-fixed-or-random-v1"),
                   "mask_json":json.dumps(mask,sort_keys=True),"selected_modules_json":json.dumps(selected),
                   "selected_count":len(selected),"trainable_parameters":effect["trainable_parameters"],
                   "adapted_fraction":effect["trainable_parameters"]/total_parameters,
                   "head_updated":effect["head_updated"],"mask_enforced":effect["mask_enforced"],
                   "frozen_integrity":integrity["ok"],
                   "random_seed":random_seed if method=="random_calibrated_logical" else None,
                   "random_budget_error":random_details["parameter_budget_error"] if method=="random_calibrated_logical" else None,
                   "random_candidate_count":random_details["candidate_count"] if method=="random_calibrated_logical" else None,
                   "random_same_as_logical":random_details["same_as_adaptive"] if method=="random_calibrated_logical" else None})
                run_rows.append({"budget":budget,"repetition":repetition,"method":method,
                   "ap":metrics["ap"],"auroc":metrics["auroc"],"brier":metrics["brier"],
                   "validation_prevalence":metrics["prevalence"],"mean_predicted":float(p.mean()),
                   "adaptation_n":len(adapt),"adaptation_events":int(adapt.label.sum()),
                   "validation_n":len(y),"validation_events":int(y.sum()),
                   "source_selector_n":len(source_features.labels),
                   "source_selector_events":int(source_features.labels.sum()),
                   "target_selector_n":len(target_features.labels),
                   "target_selector_events":int(target_features.labels.sum()),
                   "total_parameters":total_parameters,
                   "trainable_parameters":effect["trainable_parameters"],
                   "adapted_fraction":effect["trainable_parameters"]/total_parameters,
                   "selected_module_count":len(selected),"fit_seconds":elapsed,
                   "checkpoint":checkpoint,"checkpoint_sha256":checkpoint_sha,
                   "source_checkpoint_sha256":source_checkpoint_sha,
                   "source_preprocessor_sha256":registration["baseline_source_preprocessor_sha256"],
                   "mask_enforced":True,"frozen_integrity":True})
    per_run=pd.DataFrame(run_rows); masks_df=pd.DataFrame(mask_rows)
    if len(per_run)!=100 or len(masks_df)!=100 or len(score_rows)!=140:
        raise RuntimeError("Registered selector experiment produced incomplete rows")
    summary=_summarize(per_run,masks_df,baseline)
    per_run.to_csv(output/"per_run.csv",index=False)
    masks_df.to_csv(output/"masks.csv",index=False)
    pd.DataFrame(score_rows).to_csv(output/"module_scores.csv",index=False)
    (output/"summary.json").write_text(json.dumps(summary,indent=2,default=_jsonable,allow_nan=False)+"\n")
    (output/"execution_manifest.json").write_text(json.dumps({
       "completed_utc":datetime.now(timezone.utc).isoformat(),"registration_sha256":pre_registration_sha,
       "runner_code_sha256":file_sha256(Path(__file__)),"protocol_version":snapshot["protocol_version"],
       "lock_sha256":LOCK_SHA256,"private_assignments_sha256":ASSIGNMENTS_SHA256,
       "source_checkpoint_sha256":source_checkpoint_sha,
       "source_preprocessor_sha256":registration["baseline_source_preprocessor_sha256"],
       "baseline_metrics_sha256":registration["baseline_metrics_sha256"],
       "source_selector_partition":"source_validation","target_selector_partition":"stored_adaptation_draw",
       "target_evaluation_partition":"target_validation","target_test_accessed":False,
       "validation_participants":171,"validation_events":13,"draws":10,
       "methods":registration["methods"],"checkpoints":len(run_rows),
       "environment":{"python":platform.python_version(),"torch":torch.__version__,
                      "numpy":np.__version__,"pandas":pd.__version__},
       "failures":failures},indent=2,allow_nan=False)+"\n")
    if file_sha256(BASELINE/"checkpoints/source_multiview.pt")!=source_checkpoint_sha:
        raise RuntimeError("Source checkpoint changed during selector experiment")
    return {"rows":len(per_run),"checkpoints":len(run_rows),"summary":summary}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",type=Path,required=True)
    parser.add_argument("--master-file",type=Path,required=True)
    parser.add_argument("--questionnaire",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=run(args.data_root,args.master_file,args.questionnaire,args.output)
    print(json.dumps({"status":"development_selectors_complete","rows":result["rows"],
                      "checkpoints":result["checkpoints"]}))


if __name__=="__main__":
    main()
