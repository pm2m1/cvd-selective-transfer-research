"""Separate HAALSI/MHAS publication lock; never used by historical ARIC/MESA.

Importing this module has no side effects. Real execution needs an explicit
``--execute-real-lock`` command and a reviewed approval record. This module
contains no training, preprocessing fit, selector or target-test evaluation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .data.public_v2 import (PUBLIC_V2_VERSION, SCHEMA_VERSIONS, VIEWS_NINE, VIEWS_TEN, PublicV2Cohort,
                             construct_haalsi_v2, construct_mhas_v2)
from .data.releases import file_sha256
from .method import SELECTOR_VERSIONS
from .public_v2_readiness import (_haalsi_raw, _mhas_raw, delegated_review_documents_valid,
                                  readiness_evidence,
                                  require_public_v2_ready)


COMPARATORS_USING_TARGET = ("head_only", "full_finetune", "fixed_mask",
    "random_mask", "legacy_topk", "calibrated_threshold", "calibrated_logical")
SOURCE_ONLY = "source_only"
APPROVED_FLAG = "approved_for_one_time_public_lock"
REPORTED_DECISION_IDS = frozenset({"wave_reported_endpoint", "mhas_exam_landmark",
    "haalsi_retraction_uncertainty", "unknown_outcome_complete_case",
    "diabetes_omission_comparison", "haalsi_medication_route",
    "ten_primary_nine_sensitivity", "target_label_budgets", "event_reserves",
    "one_time_partition"})
REQUIRED_DOCUMENTS = frozenset({"harmonized_D", "eol_C", "master_V1_2026",
    "section_C_2012", "section_C_2015", "section_C_2018",
    "haalsi_longitudinal", "haalsi_W3", "haalsi_W1_questionnaire",
    "haalsi_icpsr_codebook"})
MHAS_USER_ATTESTATION_VERSION = "public-mhas-user-terms-attestation-v1"
MHAS_USER_ATTESTATION_STATEMENT = (
    "Yes, I personally registered or signed in to the official MHAS website, "
    "agreed to its data-use terms, and downloaded the MHAS datasets using my own account.")


@dataclass(frozen=True)
class PublicLockPolicy:
    schema_version: str
    target_window_days: int
    seed: int
    test_fraction: float
    validation_fraction_of_development: float
    test_event_floor: int
    validation_event_floor: int
    adaptation_budgets: tuple[tuple[int, int], ...]  # (positive, negative)

    def __post_init__(self) -> None:
        if self.schema_version not in (SCHEMA_VERSIONS["ten_doctor_report"],
                                       SCHEMA_VERSIONS["nine_no_diabetes"]):
            raise ValueError("Unapproved public predictor schema")
        if self.target_window_days not in (14, 30):
            raise ValueError("Only prespecified examination windows are supported")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("Explicit nonnegative split seed required")
        if not (0 < self.test_fraction < 1 and 0 < self.validation_fraction_of_development < 1):
            raise ValueError("Invalid split fractions")
        if min(self.test_event_floor, self.validation_event_floor) < 1:
            raise ValueError("Positive-event reserve floors required")
        if not self.adaptation_budgets or any(p < 2 or n < 2 for p, n in self.adaptation_budgets):
            raise ValueError("Positive and negative adaptation labels must be budgeted")


def aggregate_budget_plan(events: int, nonevents: int, policy: PublicLockPolicy,
                          budgets: tuple[tuple[int, int], ...] = ((10, 30), (25, 75), (50, 150))) -> dict:
    """Count-only arithmetic corresponding to the future stratified lock."""
    if events < 0 or nonevents < 0:
        raise ValueError("Negative cohort count")
    test_p = max(policy.test_event_floor, math.ceil(events * policy.test_fraction))
    test_n = max(2, round(nonevents * policy.test_fraction))
    dev_p, dev_n = events - test_p, nonevents - test_n
    val_p = max(policy.validation_event_floor,
                math.ceil(max(0, dev_p) * policy.validation_fraction_of_development))
    val_n = max(2, round(max(0, dev_n) * policy.validation_fraction_of_development))
    adapt_p, adapt_n = dev_p - val_p, dev_n - val_n
    possible = dev_p >= 1 and dev_n >= 2 and adapt_p >= 1 and adapt_n >= 2
    return {"cohort_events": events, "cohort_nonevents": nonevents,
            "test": {"events": test_p, "nonevents": test_n},
            "validation": {"events": val_p, "nonevents": val_n},
            "adaptation_pool": {"events": adapt_p, "nonevents": adapt_n},
            "budget_feasible": {f"{p}_positive_{n}_negative": bool(possible and adapt_p >= p and adapt_n >= n)
                                for p, n in budgets},
            "actual_participants_allocated": False,
            "caveat": "Planning arithmetic only; floors and split governance still require approval."}


def schema_digest(cohort: PublicV2Cohort) -> str:
    payload = {"version": cohort.report["schema_version"],
               "views": {k: list(v) for k, v in cohort.views.items()}}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def validate_public_inputs(source: PublicV2Cohort, target: PublicV2Cohort,
                           policy: PublicLockPolicy) -> dict:
    """Check identity and leakage before a participant partition can be made."""
    expected = {"source": "HAALSI Wave 1", "target": "MHAS Wave 3/2012 examination"}
    if source.report.get("cohort") != expected["source"] or target.report.get("cohort") != expected["target"]:
        raise ValueError("Public source/target identity mismatch")
    if any(c.report.get("protocol_version") != PUBLIC_V2_VERSION for c in (source, target)):
        raise ValueError("Historical or unknown protocol cannot use public lock")
    if any(c.report.get("schema_version") != policy.schema_version for c in (source, target)):
        raise ValueError("Public predictor schema/version mismatch")
    expected_views = (VIEWS_TEN if policy.schema_version == SCHEMA_VERSIONS["ten_doctor_report"]
                      else VIEWS_NINE)
    if source.views != expected_views or target.views != expected_views:
        raise ValueError("Public predictor views differ from frozen versioned schema")
    if schema_digest(source) != schema_digest(target):
        raise ValueError("Source/target view schema mismatch")
    if target.report.get("diagnostics", {}).get("landmark", {}).get("window_days") != policy.target_window_days:
        raise ValueError("Target examination landmark mismatch")
    allowed_metadata = {"participant_id", "endpoint_status", "label"}
    for name, cohort, prefix in (("source", source, "HAALSI:"), ("target", target, "MHAS:")):
        frame = cohort.canonical
        ids = frame.participant_id.astype("string")
        if ids.isna().any() or ids.duplicated().any() or not ids.str.startswith(prefix).all():
            raise ValueError(f"{name} participant IDs invalid or nonunique")
        if not frame.label.isin([0, 1]).all() or frame.label.isna().any():
            raise ValueError(f"{name} endpoint must be observed and binary")
        if not frame.endpoint_status.isin(["positive", "known_negative"]).all():
            raise ValueError(f"{name} unknown/contradictory outcome cannot enter lock")
        if not (frame.label.eq(1) == frame.endpoint_status.eq("positive")).all():
            raise ValueError(f"{name} label and outcome status disagree")
        features = {field for fields in cohort.views.values() for field in fields}
        if len(features) != sum(len(fields) for fields in cohort.views.values()):
            raise ValueError("Duplicate public predictor across views")
        if set(frame.columns) != features | allowed_metadata or features & allowed_metadata:
            raise ValueError("Unexpected metadata/future field in public predictors")
        if frame.loc[:, list(features)].isna().any().any():
            raise ValueError(f"{name} selected predictor missing")
        if cohort.report.get("training_performed") or cohort.report.get("publication_split_created"):
            raise ValueError("Prelock input already trained or split")
    if set(source.canonical.participant_id) & set(target.canonical.participant_id):
        raise ValueError("Cross-cohort participant identity overlap")
    def content_digest(frame: pd.DataFrame) -> str:
        ordered = frame.sort_values("participant_id").loc[:, sorted(frame.columns)]
        return hashlib.sha256(ordered.to_csv(index=False).encode()).hexdigest()
    return {"source_n": len(source.canonical), "source_events": int(source.canonical.label.sum()),
            "target_n": len(target.canonical), "target_events": int(target.canonical.label.sum()),
            "schema_sha256": schema_digest(source),
            "source_canonical_sha256": content_digest(source.canonical),
            "target_canonical_sha256": content_digest(target.canonical),
            "participant_ids_serialized": False}


def _take(ids: list[str], count: int, seed: int) -> tuple[set[str], set[str]]:
    if count > len(ids):
        raise ValueError("Impossible split allocation")
    ordered = np.asarray(sorted(ids), dtype=object)
    chosen = set(np.random.default_rng(seed).permutation(ordered)[:count].tolist())
    return chosen, set(ids) - chosen


def target_partition_in_memory(target: PublicV2Cohort, policy: PublicLockPolicy) -> dict[str, set[str]]:
    """Deterministic one-seed stratification. Use on real data only after approval."""
    frame = target.canonical
    if frame.participant_id.isna().any() or frame.participant_id.duplicated().any():
        raise ValueError("Target participants must be unique")
    if not frame.label.isin([0, 1]).all():
        raise ValueError("Target labels must be observed binary values")
    positive = frame.loc[frame.label.eq(1), "participant_id"].astype(str).tolist()
    negative = frame.loc[frame.label.eq(0), "participant_id"].astype(str).tolist()
    test_p = max(policy.test_event_floor, math.ceil(len(positive) * policy.test_fraction))
    test_n = max(2, round(len(negative) * policy.test_fraction))
    if test_p >= len(positive) or test_n >= len(negative):
        raise ValueError("Test reserve leaves no development class")
    test_pos, dev_pos = _take(positive, test_p, policy.seed)
    test_neg, dev_neg = _take(negative, test_n, policy.seed + 1)
    val_p = max(policy.validation_event_floor,
                math.ceil(len(dev_pos) * policy.validation_fraction_of_development))
    val_n = max(2, round(len(dev_neg) * policy.validation_fraction_of_development))
    if val_p >= len(dev_pos) or val_n >= len(dev_neg):
        raise ValueError("Validation reserve leaves no adaptation class")
    val_pos, adapt_pos = _take(list(dev_pos), val_p, policy.seed + 2)
    val_neg, adapt_neg = _take(list(dev_neg), val_n, policy.seed + 3)
    parts = {"target_test": test_pos | test_neg,
             "target_validation": val_pos | val_neg,
             "target_adaptation_pool": adapt_pos | adapt_neg}
    if (sum(map(len, parts.values())) != len(frame) or
            any(left & right for i, left in enumerate(parts.values())
                for right in list(parts.values())[i + 1:])):
        raise AssertionError("Target partitions overlap or omit participants")
    for positives, negatives in policy.adaptation_budgets:
        if len(adapt_pos) < positives or len(adapt_neg) < negatives:
            raise ValueError(f"Impossible adaptation allocation: {positives} positive + {negatives} negative")
    return parts


def source_partition_in_memory(source: PublicV2Cohort, seed: int) -> dict[str, set[str]]:
    """Separate deterministic 60/20/20 stratified source partition."""
    frame = source.canonical
    if frame.participant_id.isna().any() or frame.participant_id.duplicated().any():
        raise ValueError("Source participants must be unique")
    groups = {value: frame.loc[frame.label.eq(value), "participant_id"].astype(str).tolist()
              for value in (0, 1)}
    if min(map(len, groups.values())) < 5:
        raise ValueError("Too few source observations for three two-class partitions")
    parts = {"source_train": set(), "source_validation": set(), "source_test": set()}
    for label, ids in groups.items():
        test, rest = _take(ids, max(1, round(len(ids) * .2)), seed + 10 + label * 3)
        validation, train = _take(list(rest), max(1, round(len(ids) * .2)), seed + 11 + label * 3)
        parts["source_train"].update(train)
        parts["source_validation"].update(validation)
        parts["source_test"].update(test)
    if sum(map(len, parts.values())) != len(frame) or any(
            left & right for i, left in enumerate(parts.values())
            for right in list(parts.values())[i + 1:]):
        raise AssertionError("Source partitions overlap or omit participants")
    return parts


def adaptation_draw(target: PublicV2Cohort, partitions: dict[str, set[str]], *,
                    positives: int, negatives: int, seed: int, repetition: int = 0) -> set[str]:
    """Nested exact-budget draw from one class-wise permutation per repetition.

    The permutation is independent of the requested budget. Therefore 10+30
    is a subset of 25+75 for the same seed and repetition, without sampling a
    target test or validation participant.
    """
    if repetition < 0 or positives < 2 or negatives < 2:
        raise ValueError("Invalid draw or two-class adaptation budget")
    if any(left & right for i, left in enumerate(partitions.values())
           for right in list(partitions.values())[i + 1:]):
        raise ValueError("Leaking target partition overlap")
    pool = target.canonical[target.canonical.participant_id.isin(partitions["target_adaptation_pool"])]
    pos = pool.loc[pool.label.eq(1), "participant_id"].astype(str).tolist()
    neg = pool.loc[pool.label.eq(0), "participant_id"].astype(str).tolist()
    if len(pos) < positives or len(neg) < negatives:
        raise ValueError("Impossible target adaptation label budget")
    pos_rng = np.random.default_rng(np.random.SeedSequence([seed, repetition, 1]))
    neg_rng = np.random.default_rng(np.random.SeedSequence([seed, repetition, 0]))
    result = set(pos_rng.permutation(sorted(pos))[:positives].tolist())
    result |= set(neg_rng.permutation(sorted(neg))[:negatives].tolist())
    if result & (partitions["target_test"] | partitions["target_validation"]):
        raise AssertionError("Adaptation draw accessed validation/test")
    return result


def comparator_bindings(draw: set[str]) -> dict[str, str | None]:
    """Fingerprint the single shared adaptation set; source-only receives none."""
    digest = hashlib.sha256(json.dumps(sorted(draw)).encode()).hexdigest()
    return {SOURCE_ONLY: None, **{name: digest for name in COMPARATORS_USING_TARGET}}


def comparator_adaptation_sets(draw: set[str]) -> dict[str, frozenset[str] | None]:
    """Return the same immutable labeled target set to every transfer comparator."""
    shared = frozenset(draw)
    return {SOURCE_ONLY: None, **{name: shared for name in COMPARATORS_USING_TARGET}}


def aggregate_partition_metadata(target: PublicV2Cohort,
                                 partitions: dict[str, set[str]]) -> dict:
    """Return counts only; IDs and per-person hashes never enter public reports."""
    frame = target.canonical.set_index("participant_id")
    return {name: {"n": len(ids), "events": int(frame.loc[list(ids), "label"].sum()),
                   "nonevents": int(len(ids) - frame.loc[list(ids), "label"].sum())}
            for name, ids in partitions.items()}


def project_sensitivity_on_primary_lock(primary_partitions: dict[str, set[str]],
                                        sensitivity: PublicV2Cohort) -> dict[str, set[str]]:
    """Intersect a narrower/alternative cohort with the sole primary lock.

    Participants absent from the primary cohort receive no new test assignment.
    This function never creates a second random split.
    """
    if set(primary_partitions) != {"target_test", "target_validation", "target_adaptation_pool"}:
        raise ValueError("Primary target lock partitions incomplete")
    if any(left & right for i, left in enumerate(primary_partitions.values())
           for right in list(primary_partitions.values())[i + 1:]):
        raise ValueError("Primary target lock overlaps")
    eligible = set(sensitivity.canonical.participant_id.astype(str))
    return {name: ids & eligible for name, ids in primary_partitions.items()}


def _write_lock_once(snapshot: dict, lock_root: Path) -> Path:
    """Create the sole protocol lock file; exclusive open rejects any repeat."""
    lock_path = lock_root / PUBLIC_V2_VERSION / "target_lock.json"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("x") as output:
        output.write(json.dumps(snapshot, indent=2, allow_nan=False) + "\n")
    return lock_path


def _delegated_methodology_record_valid(approval: dict) -> bool:
    """Verify the versioned public-only alternative without claiming a signature.

    This checks project documents and provenance, not institutional clearance.
    Separate real-lock authorization remains mandatory in _validate_approval.
    """
    decisions = approval.get("reported_supervisor_decisions")
    return (
        approval.get("approval_basis") == "student_reported_supervisor_delegation" and
        delegated_review_documents_valid(approval) and
        approval.get("written_supervisor_approval_received") is False and
        approval.get("independent_clinical_review_received") is False and
        approval.get("clinical_review_disposition") == "not_required_documented" and
        approval.get("reported_final_protocol_approval") is True and
        approval.get("reported_routine_methodology_delegation") is True and
        isinstance(decisions, list) and len(decisions) == 10 and
        {item.get("id") for item in decisions if isinstance(item, dict)} == REPORTED_DECISION_IDS and
        all(isinstance(item, dict) and item.get("response") == "YES (student-reported)"
            for item in decisions))


def validate_public_use_records(approval: dict) -> dict:
    """Verify file-bound use evidence without claiming server-side acceptance.

    HAALSI has a downloaded ICPSR terms record. MHAS acceptance is a user's
    first-person attestation and must remain labelled as such.
    """
    terms = approval.get("release_use_terms")
    if not isinstance(terms, dict):
        raise ValueError("Public release-use evidence required")
    haalsi = Path(terms.get("haalsi_local_terms_path", ""))
    mhas = Path(terms.get("mhas_user_attestation_path", ""))
    if (not haalsi.is_file() or not terms.get("haalsi_local_terms_sha256") or
            file_sha256(haalsi) != terms["haalsi_local_terms_sha256"]):
        raise ValueError("HAALSI ICPSR terms record missing or changed")
    if (not mhas.is_file() or not terms.get("mhas_user_attestation_sha256") or
            file_sha256(mhas) != terms["mhas_user_attestation_sha256"]):
        raise ValueError("MHAS user attestation missing or changed")
    attestation = json.loads(mhas.read_text())
    document = Path(attestation.get("attestation_document_path", ""))
    if (attestation.get("record_version") != MHAS_USER_ATTESTATION_VERSION or
            not attestation.get("recorded_date") or
            attestation.get("exact_statement") != MHAS_USER_ATTESTATION_STATEMENT or
            "ChatGPT conversation" not in attestation.get("source", "") or
            not all(attestation.get(field) is True for field in (
                "user_confirms_registration_or_signin",
                "user_confirms_download_through_own_account",
                "user_confirms_applicable_terms_acceptance")) or
            any(attestation.get(field) is not False for field in (
                "independent_account_or_server_verification_performed",
                "credentials_requested_or_stored", "institutional_ethics_exemption_claimed",
                "real_lock_execution_authorized")) or
            not document.is_file() or
            file_sha256(document) != attestation.get("attestation_document_sha256")):
        raise ValueError("MHAS conversation attestation provenance or content invalid")
    return {"haalsi_icpsr_terms_file_verified": True,
            "mhas_user_attestation_file_verified": True,
            "mhas_acceptance_evidence_class": "first_person_conversation_attestation",
            "independent_mhas_account_verification": False,
            "credentials_stored": False}


def public_runner_review_valid(approval: dict) -> bool:
    """Bind the already-required technical runner review to a dated record."""
    review = approval.get("public_runner_review_record")
    if not isinstance(review, dict) or approval.get("public_runner_review") != "approved":
        return False
    path = Path(review.get("path", ""))
    return bool(review.get("reviewed_by") and review.get("reviewed_date") and
                review.get("sha256") and path.is_file() and
                file_sha256(path) == review["sha256"])


def _validate_approval(approval: dict, evidence: dict, config: dict, policy: PublicLockPolicy) -> None:
    if (approval.get("template_status") == "UNAPPROVED_TEMPLATE_DO_NOT_EXECUTE" or
            approval.get("approval_status") != APPROVED_FLAG or
            approval.get("protocol_version") != PUBLIC_V2_VERSION or
            approval.get("evidence_digest") != evidence.get("evidence_digest") or
            approval.get("config_sha256") != evidence.get("file_sha256", {}).get("public_config")):
        raise ValueError("Missing or mismatched explicit public one-time approval")
    if not approval.get("recorded_by") or not approval.get("recorded_date"):
        raise ValueError("Approval provenance required")
    if (approval.get("written_supervisor_approval_received") is not True and
            not _delegated_methodology_record_valid(approval)):
        raise ValueError("Written or versioned delegated supervisor methodology record required")
    validate_public_use_records(approval)
    required = ("medication_route", "schema_choice", "adaptation_budget", "event_reserves",
                "one_time_test_governance", "public_runner_review")
    if any(approval.get(name) != "approved" for name in required):
        raise ValueError("Concrete public protocol approvals incomplete")
    if not public_runner_review_valid(approval):
        raise ValueError("Dated public runner review record missing or changed")
    if approval.get("schema_version") != policy.schema_version or approval.get("target_window_days") != policy.target_window_days:
        raise ValueError("Approved schema/landmark mismatch")
    if (approval.get("clinical_review_disposition") != config.get("clinical_endpoint_signoff") or
            approval.get("clinical_review_disposition") not in {"approved", "not_required_documented"}):
        raise ValueError("Clinical review disposition is unresolved")
    if (not isinstance(approval.get("documentation"), dict) or
            not REQUIRED_DOCUMENTS.issubset(approval["documentation"])):
        raise ValueError("Frozen documentation inventory required")
    for item in approval["documentation"].values():
        if (not isinstance(item, dict) or not item.get("version") or
                not item.get("path") or not item.get("sha256") or
                file_sha256(Path(item["path"])) != item["sha256"]):
            raise ValueError("Documentation version/hash mismatch")
    if any(config.get(field) != "approved" for field in (
            "statistical_event_reserve_signoff", "final_schema_signoff", "public_publication_lock")):
        raise ValueError("Public configuration approval gates remain pending")
    if approval.get("lock_execution_authorized") is not True:
        raise ValueError("Separate real-lock authorization required")


def _verified_evidence(evidence: dict, config_path: Path, root: Path,
                       master_file: Path, questionnaire: Path) -> dict:
    stable = {k: v for k, v in evidence.items() if k not in {"created_utc", "evidence_digest"}}
    calculated = hashlib.sha256(json.dumps(stable, sort_keys=True, allow_nan=False).encode()).hexdigest()
    if calculated != evidence.get("evidence_digest") or evidence.get("protocol_version") != PUBLIC_V2_VERSION:
        raise ValueError("Aggregate evidence digest or protocol mismatch")
    config = json.loads(config_path.read_text())
    if config != evidence.get("configuration"):
        raise ValueError("Public configuration changed after aggregate evidence")
    source_map = Path(config["source_mapping"])
    target_map = Path(config["target_mapping"])
    source, target = json.loads(source_map.read_text()), json.loads(target_map.read_text())
    paths = {"haalsi": root / source["files"]["main"],
             "mhas_harmonized": root / target["files"]["main"],
             "mhas_biomarker": root / target["files"]["biomarker"],
             "mhas_eol": root / target["files"]["eol"],
             "mhas_master_2024": master_file,
             "source_mapping": source_map, "target_mapping": target_map,
             "public_config": config_path,
             "primary_feature_schema": Path(config["primary_feature_schema_config"]),
             "sensitivity_feature_schema": Path(config["sensitivity_feature_schema_config"]),
             "haalsi_baseline_questionnaire": questionnaire}
    module_dir = Path(__file__).resolve().parent
    paths.update({
        "code_public_v2": module_dir / "data/public_v2.py",
        "code_public_cohorts": module_dir / "data/public_cohorts.py",
        "code_public_reconciliation": module_dir / "data/public_reconciliation.py",
        "code_wave_endpoint": module_dir / "data/wave_endpoint.py",
        "code_real_cohorts": module_dir / "data/real_cohorts.py",
        "code_public_v2_readiness": module_dir / "public_v2_readiness.py",
        "code_public_lock": module_dir / "public_lock.py",
    })
    hashes = evidence.get("file_sha256", {})
    if set(paths) - set(hashes):
        raise ValueError("Aggregate evidence lacks mandatory release/document hashes")
    if any(file_sha256(path) != hashes[name] for name, path in paths.items()):
        raise ValueError("Dataset, mapping, questionnaire or configuration hash changed")
    expected = config.get("expected_input_sha256")
    if expected is not None and (not isinstance(expected, dict) or any(
            hashes.get(name) != digest for name, digest in expected.items())):
        raise ValueError("Frozen public input hashes no longer match evidence")
    return config


def execute_real_lock(*, root: Path, master_file: Path, questionnaire: Path,
                      config_path: Path, evidence_path: Path, approval_path: Path,
                      lock_root: Path, policy: PublicLockPolicy) -> Path:
    """Future-only one-time action; current proposed config/approval cannot pass."""
    repo_root = Path(__file__).resolve().parents[2]
    if policy.target_window_days != 30:
        raise ValueError("One-time primary lock uses the approved 0–30-day cohort; 0–14 is a sensitivity")
    if lock_root.resolve().is_relative_to(repo_root):
        raise ValueError("Real private lock directory must be outside the repository")
    lock_path = lock_root / PUBLIC_V2_VERSION / "target_lock.json"
    if lock_path.exists():
        raise FileExistsError("Public target test already locked; repeat lock prohibited")
    evidence = json.loads(evidence_path.read_text())
    config = _verified_evidence(evidence, config_path, root, master_file, questionnaire)
    approval = json.loads(approval_path.read_text())
    _validate_approval(approval, evidence, config, policy)
    if (config.get("protocol_version") != PUBLIC_V2_VERSION or
            config.get("protocol_stage") != "approved_for_lock" or
            config.get("source") != "HAALSI Wave 1" or
            config.get("target") != "MHAS Wave 3/2012 examination" or
            config.get("endpoint_version") != "public-wave-doctor-reported-ha-or-stroke-v2" or
            approval.get("release_identities") != config.get("release_identities") or
            not isinstance(config.get("release_identities"), dict) or
            set(config["release_identities"]) != {"haalsi", "mhas_harmonized", "mhas_biomarker", "mhas_eol", "mhas_master"} or
            config.get("primary_selector") != "calibrated_logical" or
            config.get("selector_ablations") != ["legacy_topk", "calibrated_threshold"] or
            config.get("source_split_fractions_proposed") != {"train": .6, "validation": .2, "test": .2} or
            config.get("proposed_primary_schema") != policy.schema_version or
            config.get("target_test_fraction_proposed") != policy.test_fraction or
            config.get("target_validation_fraction_of_development_proposed") != policy.validation_fraction_of_development or
            config.get("test_event_floor_proposed") != policy.test_event_floor or
            config.get("validation_event_floor_proposed") != policy.validation_event_floor or
            set(tuple(x) for x in approval.get("adaptation_budgets", [])) != set(policy.adaptation_budgets) or
            approval.get("seed") != policy.seed):
        raise ValueError("Approved public lock policy/configuration mismatch")
    hmap = json.loads(Path(config["source_mapping"]).read_text())
    mmap = json.loads(Path(config["target_mapping"]).read_text())
    if (hmap.get("public_model_mapping_version") != config.get("source_public_mapping_version") or
            mmap.get("public_model_mapping_version") != config.get("target_public_mapping_version")):
        raise ValueError("Public mapping overlay versions changed")
    hraw, hlabels, _ = _haalsi_raw(root, hmap)
    mraw, mlabels, _ = _mhas_raw(root, master_file, mmap)
    schema = "ten_doctor_report" if policy.schema_version == SCHEMA_VERSIONS["ten_doctor_report"] else "nine_no_diabetes"
    source = construct_haalsi_v2(hraw, hmap, hlabels, schema=schema)
    target = construct_mhas_v2(mraw, mmap, mlabels, schema=schema, max_days=policy.target_window_days)
    checks = validate_public_inputs(source, target, policy)
    source_key = "haalsi_ten_doctor" if schema == "ten_doctor_report" else "haalsi_nine"
    target_key = f"mhas_{'ten' if schema == 'ten_doctor_report' else 'nine'}_0_{policy.target_window_days}"
    for cohort, key in ((source, source_key), (target, target_key)):
        if cohort.report["after_v2_rules"] != evidence["cohorts"][key]["after_v2_rules"]:
            raise ValueError("Current canonical cohort differs from approved aggregate evidence")
    readiness = readiness_evidence(config, source.report, target.report,
                                   provenance_ok=True, locked_runner_reviewed=True)
    require_public_v2_ready({"readiness": readiness})
    partitions = target_partition_in_memory(target, policy)
    counts = aggregate_partition_metadata(target, partitions)
    source_parts = source_partition_in_memory(source, policy.seed)
    source_counts = aggregate_partition_metadata(source, source_parts)
    # The actual assignment remains reproducible from seed + content-bound
    # cohort; public reports contain only aggregate counts. A private digest
    # detects drift without serializing participant identifiers.
    target_test_digest = hashlib.sha256(json.dumps(sorted(partitions["target_test"])).encode()).hexdigest()
    snapshot = {"protocol_version": PUBLIC_V2_VERSION,
                "endpoint_version": config["endpoint_version"],
                "source_public_mapping_version": config["source_public_mapping_version"],
                "target_public_mapping_version": config["target_public_mapping_version"],
                "schema_version": policy.schema_version,
                "release_identities": config["release_identities"],
                "primary_selector": config["primary_selector"],
                "selector_versions": {name: SELECTOR_VERSIONS[name] for name in
                                      [config["primary_selector"], *config["selector_ablations"]]},
                "schema_sha256": checks["schema_sha256"], "source": config["source"],
                "target": config["target"], "evidence_digest": evidence["evidence_digest"],
                "config_sha256": evidence["file_sha256"]["public_config"],
                "raw_mapping_document_sha256": evidence["file_sha256"],
                "approved_documentation": {name: {"version": item["version"], "sha256": item["sha256"]}
                                           for name, item in approval["documentation"].items()},
                "seed": policy.seed, "test_fraction": policy.test_fraction,
                "validation_fraction_of_development": policy.validation_fraction_of_development,
                "test_event_floor": policy.test_event_floor,
                "validation_event_floor": policy.validation_event_floor,
                "adaptation_budgets": [list(x) for x in policy.adaptation_budgets],
                "target_window_days": policy.target_window_days,
                "cohort_counts": checks, "partition_counts": counts,
                "source_partition_counts": source_counts,
                "private_target_test_digest": target_test_digest,
                "participant_ids_serialized": False, "training_performed": False,
                "split_stage": "one_time_target_lock_before_fitting"}
    return _write_lock_once(snapshot, lock_root)


def verify_locked_target(snapshot: dict, source: PublicV2Cohort,
                         target: PublicV2Cohort, policy: PublicLockPolicy) -> dict[str, set[str]]:
    """Reconstruct and verify the immutable test from the private snapshot."""
    checks = validate_public_inputs(source, target, policy)
    if (snapshot.get("protocol_version") != PUBLIC_V2_VERSION or
            snapshot.get("schema_version") != policy.schema_version or
            snapshot.get("schema_sha256") != checks["schema_sha256"] or
            snapshot.get("seed") != policy.seed or
            snapshot.get("target_window_days") != policy.target_window_days or
            snapshot.get("cohort_counts") != checks):
        raise ValueError("Locked public cohort or policy changed")
    parts = target_partition_in_memory(target, policy)
    digest = hashlib.sha256(json.dumps(sorted(parts["target_test"])).encode()).hexdigest()
    if snapshot.get("private_target_test_digest") != digest:
        raise ValueError("Immutable public target test membership changed")
    if snapshot.get("partition_counts") != aggregate_partition_metadata(target, parts):
        raise ValueError("Locked partition counts changed")
    if snapshot.get("source_partition_counts") != aggregate_partition_metadata(
            source, source_partition_in_memory(source, policy.seed)):
        raise ValueError("Locked source partitions changed")
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-real-lock", action="store_true", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--master-file", type=Path, required=True)
    parser.add_argument("--questionnaire", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--evidence-json", type=Path, required=True)
    parser.add_argument("--approval-json", type=Path, required=True)
    parser.add_argument("--lock-root", type=Path, required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--target-window-days", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--test-fraction", type=float, required=True)
    parser.add_argument("--validation-fraction", type=float, required=True)
    parser.add_argument("--test-event-floor", type=int, required=True)
    parser.add_argument("--validation-event-floor", type=int, required=True)
    parser.add_argument("--adaptation-budget", nargs=2, type=int, action="append", required=True,
                        metavar=("POSITIVE", "NEGATIVE"))
    args = parser.parse_args()
    policy = PublicLockPolicy(args.schema_version, args.target_window_days, args.seed,
                              args.test_fraction, args.validation_fraction,
                              args.test_event_floor, args.validation_event_floor,
                              tuple(tuple(x) for x in args.adaptation_budget))
    path = execute_real_lock(root=args.data_root, master_file=args.master_file,
        questionnaire=args.questionnaire, config_path=args.config,
        evidence_path=args.evidence_json, approval_path=args.approval_json,
        lock_root=args.lock_root, policy=policy)
    print(f"One-time public target lock written to controlled directory: {path}")


if __name__ == "__main__":
    main()
