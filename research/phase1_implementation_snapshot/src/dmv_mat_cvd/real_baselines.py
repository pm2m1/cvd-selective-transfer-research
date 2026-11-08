"""Milestone 6A public-cohort development baselines; locked target test is inaccessible.

This entry point deliberately has no target-test evaluation mode. The MHAS
reader accepts only the private lock's development IDs before reading disease
or predictor fields. All written results are aggregate or model artifacts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import time
import platform

import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from torch import nn

from .data.locked_development import load_mhas_locked_development
from .data.public_preprocessing import PublicPreprocessor
from .data.public_v2 import SCHEMA_VERSIONS, VIEWS_TEN, construct_haalsi_v2, construct_mhas_v2
from .data.releases import file_sha256
from .evaluation import binary_metrics, predict
from .experiments.baselines import FlatMLP, flatten
from .experiments.runner import loader, seed_everything
from .models.multiview_mlp import MultiViewRiskNet
from .public_lock import _verified_evidence, schema_digest
from .public_v2_readiness import _haalsi_raw
from .safeguards import LeakageError, SplitRole
from .training import train_model
from .transfer.adapt import adapt_model

LOCK_SHA256 = 'WITHHELD_PRIVATE_BINDING'
ASSIGNMENTS_SHA256 = 'WITHHELD_PRIVATE_BINDING'
CONFIG = Path("configs/public_haalsi_mhas_v2.ready_pending_execution_m5l.json")
EVIDENCE = Path("results/public_governance/20261025/m5l_pending_execution/20261025T105836Z-2542127c/aggregate_public_v2.json")
MODEL_SETTINGS = {"source_epochs": 30, "target_epochs": 20, "batch_size": 64,
                  "source_lr": 0.001, "target_lr": 0.001, "patience": 5,
                  "view_hidden": 16, "weight_decay": 0.0001,
                  "class_weight": None, "device": "cpu", "threshold": 0.5}


def _digest_frame(frame: pd.DataFrame) -> str:
    ordered = frame.sort_values("participant_id").loc[:, sorted(frame.columns)]
    return hashlib.sha256(ordered.to_csv(index=False).encode()).hexdigest()


def _part(frame: pd.DataFrame, ids: set[str], role: SplitRole) -> pd.DataFrame:
    if role in {SplitRole.TARGET_TEST, SplitRole.SOURCE_TEST}:
        raise LeakageError("Milestone 6A does not expose held-out test partitions")
    result = frame.loc[frame.participant_id.isin(ids)].copy()
    if len(result) != len(ids) or result.participant_id.duplicated().any():
        raise ValueError("Locked partition membership absent or duplicate")
    return result


def validate_development_assignments(assignments: dict, source: pd.DataFrame,
                                     target: pd.DataFrame, snapshot: dict) -> dict:
    """Check private membership and budgets without constructing target test rows."""
    if assignments.get("lock_sha256") != LOCK_SHA256 or assignments.get("protocol_version") != "public-haalsi-mhas-v2":
        raise ValueError("Private assignment lock binding differs")
    sp = {k: set(v) for k, v in assignments["source_partitions"].items()}
    tp = {k: set(v) for k, v in assignments["target_partitions"].items()}
    if set(sp) != {"source_train", "source_validation", "source_test"} or set(tp) != {
            "target_test", "target_validation", "target_adaptation_pool"}:
        raise ValueError("Unexpected private partition structure")
    for group in (sp, tp):
        if any(len(ids) != len(group[name]) for name, ids in
               ((name, assignments["source_partitions" if group is sp else "target_partitions"][name])
                for name in group)):
            raise ValueError("Duplicate private participant IDs")
        if sum(map(len, group.values())) != len(set().union(*group.values())):
            raise ValueError("Private partitions overlap")
    if set(source.participant_id) != set().union(*sp.values()):
        raise ValueError("Source canonical cohort differs from private assignments")
    if set(target.participant_id) != tp["target_validation"] | tp["target_adaptation_pool"]:
        raise ValueError("Development cohort differs from private assignments")
    if set(source.participant_id) & set().union(*tp.values()):
        raise ValueError("Source/target participant identities overlap")
    if len(tp["target_test"]) != snapshot["partition_counts"]["target_test"]["n"]:
        raise ValueError("Test lock membership count differs from immutable metadata")
    labels = target.set_index("participant_id").label
    summary = {}
    for name in ("target_validation", "target_adaptation_pool"):
        ids = tp[name]
        count = {"n": len(ids), "events": int(labels.loc[list(ids)].sum()),
                 "nonevents": len(ids) - int(labels.loc[list(ids)].sum())}
        if count != snapshot["partition_counts"][name]:
            raise ValueError("Locked development event counts differ")
        summary[name] = count
    if len(assignments["adaptation_draws"]) != 10:
        raise ValueError("Prespecified ten repetitions missing")
    for repetition, draws in assignments["adaptation_draws"].items():
        if set(draws) != {"primary_25_75", "low_label_10_30"}:
            raise ValueError("Unknown adaptation budget")
        primary, low = set(draws["primary_25_75"]), set(draws["low_label_10_30"])
        if (len(primary) != 100 or len(low) != 40 or not low <= primary or
                not primary <= tp["target_adaptation_pool"] or
                int(labels.loc[list(primary)].sum()) != 25 or
                int(labels.loc[list(low)].sum()) != 10):
            raise ValueError(f"Locked adaptation draw {repetition} differs from approved nested budgets")
    return {"source_train": {"n": len(sp["source_train"]),
                              "events": int(source.set_index("participant_id").label.loc[list(sp["source_train"])].sum())},
            "source_validation": {"n": len(sp["source_validation"]),
                                    "events": int(source.set_index("participant_id").label.loc[list(sp["source_validation"])].sum())},
            **summary, "target_test_integrity_metadata": snapshot["partition_counts"]["target_test"],
            "draws": len(assignments["adaptation_draws"])}


def load_verified_development(data_root: Path, master_file: Path, questionnaire: Path,
                              config_path: Path = CONFIG, evidence_path: Path = EVIDENCE):
    private = data_root / "private_locks/public-haalsi-mhas-v2"
    lock_path, assignments_path = private / "target_lock.json", private / "participant_assignments.private.json"
    if file_sha256(lock_path) != LOCK_SHA256 or file_sha256(assignments_path) != ASSIGNMENTS_SHA256:
        raise ValueError("Immutable real target lock or assignment hash changed")
    snapshot, assignments = json.loads(lock_path.read_text()), json.loads(assignments_path.read_text())
    evidence = json.loads(evidence_path.read_text())
    config = _verified_evidence(evidence, config_path, data_root, master_file, questionnaire)
    if (snapshot.get("protocol_version") != "public-haalsi-mhas-v2" or
            snapshot.get("schema_version") != SCHEMA_VERSIONS["ten_doctor_report"] or
            snapshot.get("config_sha256") != file_sha256(config_path) or
            snapshot.get("evidence_digest") != evidence["evidence_digest"] or
            snapshot.get("raw_mapping_document_sha256") != evidence["file_sha256"] or
            snapshot.get("seed") != 20261025 or
            snapshot.get("adaptation_budgets") != [[25, 75], [10, 30]]):
        raise ValueError("Immutable protocol, release or budget binding changed")
    source_map = json.loads(Path(config["source_mapping"]).read_text())
    target_map = json.loads(Path(config["target_mapping"]).read_text())
    source_raw, source_labels, _ = _haalsi_raw(data_root, source_map)
    source = construct_haalsi_v2(source_raw, source_map, source_labels)
    if (_digest_frame(source.canonical) != snapshot["cohort_counts"]["source_canonical_sha256"] or
            len(source.canonical) != 2906 or int(source.canonical.label.sum()) != 107 or
            schema_digest(source) != snapshot["cohort_counts"]["schema_sha256"]):
        raise ValueError("Source or five-view schema differs from approved lock")
    target_parts = assignments["target_partitions"]
    allowed = set(target_parts["target_validation"]) | set(target_parts["target_adaptation_pool"])
    raw, loading = load_mhas_locked_development(data_root, master_file, target_map,
                                                  allowed, set(target_parts["target_test"]))
    target = construct_mhas_v2(raw, target_map, loading["labels"])
    if source.views != target.views or target.views != VIEWS_TEN:
        raise ValueError("Source/target five-view feature order differs")
    summary = validate_development_assignments(assignments, source.canonical,
                                               target.canonical, snapshot)
    return source.canonical, target.canonical, assignments, snapshot, summary, raw, target_map, loading["labels"]


def _torch_fit(model: nn.Module, train_ds, val_ds, settings: dict,
               seed: int, epochs: int, lr: float):
    seed_everything(seed)
    device = torch.device("cpu")
    start = time.monotonic()
    train_model(model, loader(train_ds, settings["batch_size"], True, seed),
                loader(val_ds, settings["batch_size"]), device,
                epochs=epochs, lr=lr, patience=settings["patience"])
    elapsed = time.monotonic() - start
    def loss(ds):
        model.eval()
        with torch.no_grad():
            y, p = predict(model, loader(ds, settings["batch_size"]), device)
        return float(nn.functional.binary_cross_entropy(torch.tensor(p).clamp(1e-7, 1-1e-7),
                    torch.tensor(y)).item())
    return elapsed, loss(train_ds), loss(val_ds)


def _metrics(model, ds):
    if isinstance(model, nn.Module):
        y, p = predict(model, loader(ds, 256), torch.device("cpu"))
    else:
        y = ds.labels.cpu().numpy()
        p = model.predict_proba(flatten(ds))[:, 1]
    return binary_metrics(y, p).to_dict(), {"mean_predicted": float(np.mean(p)),
                                           "observed_prevalence": float(np.mean(y))}


def _loss(model, ds) -> float:
    if isinstance(model, nn.Module):
        y, p = predict(model, loader(ds, 256), torch.device("cpu"))
    else:
        y, p = ds.labels.cpu().numpy(), model.predict_proba(flatten(ds))[:, 1]
    return float(log_loss(y, np.clip(p, 1e-7, 1-1e-7), labels=[0, 1]))


def run(data_root: Path, output: Path, master_file: Path, questionnaire: Path,
        repetitions: int = 10) -> dict:
    if output.exists():
        raise FileExistsError("Real baseline run path already exists; historical runs cannot be overwritten")
    if repetitions < 1 or repetitions > 10:
        raise ValueError("Only the ten prespecified stored draws may be used")
    source, target, assignments, snapshot, counts, target_raw, target_map, labels = load_verified_development(
        data_root, master_file, questionnaire)
    # Only development rows reached this point; the target test has never been
    # read with predictors/outcomes. Subsequent methods receive frames selected
    # from the immutable permitted membership alone.
    source_parts, target_parts = assignments["source_partitions"], assignments["target_partitions"]
    s_train = _part(source, set(source_parts["source_train"]), SplitRole.SOURCE_TRAIN)
    s_val = _part(source, set(source_parts["source_validation"]), SplitRole.SOURCE_VALIDATION)
    t_val = _part(target, set(target_parts["target_validation"]), SplitRole.TARGET_VALIDATION)
    source_pp = PublicPreprocessor().fit(s_train, SplitRole.SOURCE_TRAIN)
    s_train_ds = source_pp.transform(s_train, SplitRole.SOURCE_TRAIN)
    s_val_ds = source_pp.transform(s_val, SplitRole.SOURCE_VALIDATION)
    t_val_source_ds = source_pp.transform(t_val, SplitRole.TARGET_VALIDATION)
    settings = MODEL_SETTINGS.copy()
    torch.set_num_threads(2)
    seed_everything(20261025)
    output.mkdir(parents=True, exist_ok=False)
    (output / "checkpoints").mkdir()
    (output / "preprocessing").mkdir()
    source_pp.save(output / "preprocessing/source_train.json")
    rows: list[dict] = []
    def save_model(model, name: str) -> str:
        path = output / "checkpoints" / name
        if isinstance(model, nn.Module):
            torch.save(model.state_dict(), path)
        else:
            import joblib
            joblib.dump(model, path)
        return file_sha256(path)
    def record(stage: str, budget: str, repetition: int | None, method: str,
               model, train_ds, val_ds, fit_seconds: float,
               train_loss: float | None, val_loss: float | None,
               preprocessor_role: str, checkpoint: str, checkpoint_sha: str):
        metrics, calibration = _metrics(model, val_ds)
        parameter_count = (sum(p.numel() for p in model.parameters()) if isinstance(model, nn.Module)
                           else int(model.coef_.size + model.intercept_.size)
                           if isinstance(model, LogisticRegression) else None)
        trainable_count = (sum(p.numel() for p in model.parameters() if p.requires_grad)
                           if isinstance(model, nn.Module) else parameter_count)
        rows.append({"stage": stage, "budget": budget, "repetition": repetition,
                     "method": method, "train_n": len(train_ds), "train_events": int(train_ds.labels.sum()),
                     "validation_n": len(val_ds), "validation_events": int(val_ds.labels.sum()),
                     "ap": metrics["ap"], "auroc": metrics["auroc"], "brier": metrics["brier"],
                     "prevalence": metrics["prevalence"], **calibration,
                     "train_loss": _loss(model,train_ds) if train_loss is None else train_loss,
                     "validation_loss": _loss(model,val_ds) if val_loss is None else val_loss,
                     "fit_seconds": round(fit_seconds, 3),
                     "parameters": parameter_count,
                     "trainable_parameters": trainable_count,
                     "trees": int(model.n_estimators) if method == "source_xgboost" else None,
                     "preprocessing_fit_role": preprocessor_role,
                     "checkpoint": checkpoint, "checkpoint_sha256": checkpoint_sha})
    source_logit = LogisticRegression(max_iter=1000, random_state=20261025)
    t0=time.monotonic();source_logit.fit(flatten(s_train_ds),s_train_ds.labels.numpy());elapsed=time.monotonic()-t0
    name="source_logistic.joblib";sha=save_model(source_logit,name)
    record("source_validation","source",None,"source_logistic",source_logit,s_train_ds,s_val_ds,elapsed,None,None,
           "source_train",name,sha)
    record("target_validation","source",None,"source_logistic",source_logit,s_train_ds,t_val_source_ds,elapsed,None,None,
           "source_train",name,sha)
    try:
        from xgboost import XGBClassifier
    except ImportError:
        xgb_available = False
    else:
        xgb_available = True
        source_xgb = XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05,
                                   random_state=20261025, n_jobs=1, eval_metric="logloss")
        t0=time.monotonic();source_xgb.fit(flatten(s_train_ds),s_train_ds.labels.numpy());elapsed=time.monotonic()-t0
        name="source_xgboost.joblib";sha=save_model(source_xgb,name)
        for stage,ds in (("source_validation",s_val_ds),("target_validation",t_val_source_ds)):
            record(stage,"source",None,"source_xgboost",source_xgb,s_train_ds,ds,elapsed,None,None,
                   "source_train",name,sha)
    flat=FlatMLP(source_pp.view_dims)
    elapsed,tl,vl=_torch_fit(flat,s_train_ds,s_val_ds,settings,20261025,settings["source_epochs"],settings["source_lr"])
    name="source_flat_mlp.pt";sha=save_model(flat,name)
    for stage,ds in (("source_validation",s_val_ds),("target_validation",t_val_source_ds)):
        record(stage,"source",None,"source_flat_mlp",flat,s_train_ds,ds,elapsed,tl,vl,"source_train",name,sha)
    seed_everything(20261025)
    source_mv=MultiViewRiskNet(source_pp.view_dims,settings["view_hidden"])
    elapsed,tl,vl=_torch_fit(source_mv,s_train_ds,s_val_ds,settings,20261025,settings["source_epochs"],settings["source_lr"])
    name="source_multiview.pt";sha=save_model(source_mv,name)
    for stage,ds in (("source_validation",s_val_ds),("target_validation",t_val_source_ds)):
        record(stage,"source",None,"source_multiview",source_mv,s_train_ds,ds,elapsed,tl,vl,"source_train",name,sha)
    frozen_checks=[]
    for repetition in range(repetitions):
        draw = assignments["adaptation_draws"][str(repetition)]
        for budget in ("primary_25_75","low_label_10_30"):
            selected=set(draw[budget]);adapt=_part(target,selected,SplitRole.TARGET_ADAPTATION)
            transfer_train=source_pp.transform(adapt,SplitRole.TARGET_ADAPTATION)
            target_pp=PublicPreprocessor().fit(adapt,SplitRole.TARGET_ADAPTATION)
            target_pp.save(output / "preprocessing" / f"target_{budget}_rep{repetition}.json")
            native_train=target_pp.transform(adapt,SplitRole.TARGET_ADAPTATION)
            native_val=target_pp.transform(t_val,SplitRole.TARGET_VALIDATION)
            native_logit=LogisticRegression(max_iter=1000,random_state=20261025+repetition)
            t0=time.monotonic();native_logit.fit(flatten(native_train),native_train.labels.numpy());elapsed=time.monotonic()-t0
            name=f"target_logistic_{budget}_rep{repetition}.joblib";sha=save_model(native_logit,name)
            record("target_validation",budget,repetition,"target_logistic",native_logit,native_train,native_val,
                   elapsed,None,None,"target_adaptation",name,sha)
            seed_everything(20261025+repetition)
            native_mv=MultiViewRiskNet(target_pp.view_dims,settings["view_hidden"])
            elapsed,tl,vl=_torch_fit(native_mv,native_train,native_val,settings,20261025+repetition,
                                     settings["target_epochs"],settings["target_lr"])
            name=f"target_multiview_{budget}_rep{repetition}.pt";sha=save_model(native_mv,name)
            record("target_validation",budget,repetition,"target_multiview",native_mv,native_train,native_val,
                   elapsed,tl,vl,"target_adaptation",name,sha)
            for method,mask in (("head_only",dict.fromkeys(source_mv.selectable_modules(),False)),
                                ("full_finetune",dict.fromkeys(source_mv.selectable_modules(),True))):
                seed_everything(20261025+repetition)
                t0=time.monotonic()
                model,integrity=adapt_model(source_mv,mask,
                    loader(transfer_train,settings["batch_size"],True,20261025+repetition),
                    loader(t_val_source_ds,settings["batch_size"]),torch.device("cpu"),
                    epochs=settings["target_epochs"],lr=settings["target_lr"],patience=settings["patience"])
                elapsed=time.monotonic()-t0
                if not integrity["ok"]:
                    raise RuntimeError("Frozen module integrity failed")
                frozen_checks.append(integrity)
                name=f"{method}_{budget}_rep{repetition}.pt";sha=save_model(model,name)
                record("target_validation",budget,repetition,method,model,transfer_train,t_val_source_ds,
                       elapsed,None,None,"source_train",name,sha)
    metrics_frame = pd.DataFrame(rows)
    metrics_frame.to_csv(output/"development_metrics.csv",index=False)
    metrics_frame.loc[:, ["stage", "budget", "repetition", "method", "train_n",
                           "train_events", "train_loss", "validation_loss", "fit_seconds",
                           "checkpoint_sha256"]].to_csv(output/"training_log.csv",index=False)
    # 0–14-day feasibility is restricted to development rows and does not
    # inspect the inherited test labels.
    short=construct_mhas_v2(target_raw,target_map,labels,max_days=14)
    short_ids=set(short.canonical.participant_id)
    short_pool=short_ids & set(target_parts["target_adaptation_pool"])
    low_intersections=[len(set(assignments["adaptation_draws"][str(i)]["low_label_10_30"]) & short_pool)
                       for i in range(repetitions)]
    summary={"run_version":"m6a-public-baselines-v1","created_utc":datetime.now(timezone.utc).isoformat(),
             "protocol_version":snapshot["protocol_version"],"schema_version":snapshot["schema_version"],
             "seed":snapshot["seed"],"lock_sha256":LOCK_SHA256,"private_assignments_sha256":ASSIGNMENTS_SHA256,
             "config_sha256":file_sha256(CONFIG),"evidence_digest":snapshot["evidence_digest"],
             "runner_code_sha256":file_sha256(Path(__file__)),
             "preprocessor_code_sha256":file_sha256(Path(__file__).parent / "data/public_preprocessing.py"),
             "development_loader_code_sha256":file_sha256(Path(__file__).parent / "data/locked_development.py"),
             "input_hashes":snapshot["raw_mapping_document_sha256"],"counts":counts,
             "model_settings":settings,"view_dimensions":source_pp.view_dims,
             "environment":{"python":platform.python_version(),"torch":torch.__version__,
                            "pandas":pd.__version__,"xgboost_available":xgb_available,
                            "platform":platform.platform()},
             "view_feature_order":source_pp.encoded_columns,
             "method_label_access":{"source_logistic":"source_train_only","source_xgboost":"source_train_only",
                "source_flat_mlp":"source_train_only",
                "source_multiview":"source_train_only","target_logistic":"locked_adaptation_draw",
                "target_multiview":"locked_adaptation_draw","head_only":"locked_adaptation_draw",
                "full_finetune":"locked_adaptation_draw"},
             "frozen_integrity_all_passed":all(x["ok"] for x in frozen_checks),
             "timing_0_14_development_only":{"eligible_development_n":len(short_ids),
                   "eligible_development_events":int(short.canonical.label.sum()),
                   "stored_low_draw_intersection_sizes":low_intersections,
                   "trained":False,"reason":"Inherited test/validation event floors fail; sparse-event policy pending"},
             "target_test_features_read":False,"target_test_labels_read":False,
             "target_test_predictions_generated":False,"test_metrics_generated":False,
             "selector_experiment_run":False}
    (output/"run_manifest.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root",type=Path,default=Path(os.environ.get("DMVMAT_CVD_DATA_ROOT","")))
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--master-file",type=Path,required=True)
    parser.add_argument("--questionnaire",type=Path,required=True)
    parser.add_argument("--repetitions",type=int,default=10)
    args=parser.parse_args()
    if not args.data_root.is_dir():
        raise ValueError("DMVMAT_CVD_DATA_ROOT must point to the authorized external release directory")
    result=run(args.data_root,args.output,args.master_file,args.questionnaire,args.repetitions)
    print(json.dumps({"status":"development_only_complete","counts":result["counts"],
                      "output":str(args.output)},indent=2))


if __name__=="__main__":
    main()
