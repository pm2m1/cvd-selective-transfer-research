"""Human-only reanalysis of existing aggregate evidence, never respondent data.

Reuses the completed private assessment and its five original integrity inputs.
Does not replay the audit, diagnostic or original assessment writer. Only a new
exclusive private comparison is written; no execution/approval record changes.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import warnings

sys.dont_write_bytecode=True
VERSION="phase2b_feasibility_redesign_v1"
LOCK="phase2b_feasibility_redesign_v1.source_lock.json"
DEST="phase2b_feasibility_redesign_v1.private.json"
ACK="REVIEW ISSUE=PRIVATE_REDESIGN_COMPARISON_WRITTEN_DISCLOSURE_REVIEW_REQUIRED"
OLD_LOCK='WITHHELD_REFERENCE_BINDING'


class EvidenceError(ValueError):pass


def require(condition):
    if not condition:raise EvidenceError("EXISTING_AGGREGATE_EVIDENCE_BINDING_INVALID")


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def public_context(project, expected):
    source=project/"phase2/phase2b_public";p=source/LOCK
    require(re.fullmatch(r"[0-9a-f]{64}",expected or "") is not None and not p.is_symlink() and sha(p)==expected)
    lock=json.loads(p.read_bytes());require(lock["identity"]==VERSION+"_source_lock")
    for relative,digest in lock["public_files"].items():
        f=project/relative
        require(f.resolve(strict=True)==f and not f.is_symlink() and sha(f)==digest)
    audit=project/"phase2/phase2a_6_wave_based_audit";sys.path.insert(0,str(audit))
    old=importlib.import_module("human_stage_c_postrun_feasibility_review")
    require(Path(old.__file__).resolve()==audit/"human_stage_c_postrun_feasibility_review.py")
    recovery,boot,policy,arithmetic,contract=old.verify_sources(audit,OLD_LOCK)
    return old,recovery,boot,policy,arithmetic,contract


def existing_evidence(root, project, expected):
    old,recovery,boot,policy,arithmetic,contract=public_context(project,expected)
    _,_,q,_,patch,qualified,_,lock=boot
    require(root.is_absolute() and root.resolve(strict=True)==root and not root.stat().st_mode & 0o077 and
        root!=project and root not in project.parents and project not in root.parents)
    existing=root/"output"/old.REPORT;q.private_file(existing,root)
    prior=q.json_read(existing);integrity=prior.get("integrity",{})
    require(prior.get("identity")==old.VERSION and integrity.get("receipt_bindings_verified") is True and
        integrity.get("review_source_lock_sha256")==OLD_LOCK and prior.get("disclosure_status")=="PRIVATE_UNRELEASED" and
        prior.get("scientific_acceptance_granted") is False and prior.get("phase2b_real_data")=="NO_GO")
    files={k:p for k,p in recovery.paths(root).items() if k!="detail"}
    files.update(authorization=root/"config"/(recovery.VERSION+".authorization.json"),config=root/q.INPUTS["config"])
    require(set(integrity.get("existing_input_sha256",{}))==set(files))
    for k,p in files.items():q.private_file(p,root);require(q.digest(p)==integrity["existing_input_sha256"][k])
    records={k:q.json_read(p) for k,p in files.items()}
    b=integrity.get("completed_run_bindings",{})
    recovery.validate_authorization(records["authorization"],b)
    recovery.fixed_bindings(lock,lock_hash:=b.get("recovery_lock_sha256"),b)
    require(lock_hash==q.digest(project/"phase2/phase2a_6_wave_based_audit/stage_c_elsa_recovery_v1.lock.json") and
        all(b.get(k)==v for k,v in qualified["trusted_inputs"].items()) and
        integrity["existing_input_sha256"]["config"]==b["config_sha256"])
    start,result,aggregate=(records[k] for k in ("started","result","output"))
    env={k:v for k,v in start.items() if k not in {"identity","status"}}
    require(start.get("identity")==recovery.VERSION+"_started" and start.get("status")=="STARTED_NO_RETRY" and
        result.get("identity")==recovery.VERSION+"_result" and env.get("bindings")==b and
        all(result.get(k)==v for k,v in env.items()) and
        (result.get("status"),result.get("stage"),result.get("substage"),result.get("code"),result.get("category"),result.get("returncode"))==
        ("COMPLETED_PRIVATE_REVIEW_PENDING","NONE","NONE","NONE","NONE",0) and type(result["returncode"]) is int and
        env.get("attempt_consumed") is True and env.get("phase2b_authorized") is False and
        env.get("recovery_authorization_sha256")==integrity["existing_input_sha256"]["authorization"] and
        env.get("controller_sha256")==b["recovery_controller_sha256"] and env.get("protocol_id")==recovery.PROTOCOL and
        env.get("evidence_tier")=="QUALIFIED_LOCAL_ARCHIVE_PROVENANCE" and
        all(env.get(k) is False for k in ("v1_retried","cause_diagnostic_retried","independent_distributor_authentication","independent_human_scientific_approval")) and
        hashlib.sha256(json.dumps(env.get("dependency_environment"),sort_keys=True).encode()).hexdigest()==b["recovery_environment_sha256"] and
        result.get("private_aggregates_sha256")==integrity["existing_input_sha256"]["output"] and
        aggregate.get("execution_decision_provenance")==env)
    config=deepcopy(records["config"])
    config["cohorts"]["ELSA"],amendment=patch.correct_interview_maps(config["cohorts"]["ELSA"])
    require(recovery.fingerprint(config)==b["corrected_config_sha256"] and
        recovery.fingerprint(amendment)==b["correction_record_sha256"] and aggregate.get("configuration_amendment")==amendment)
    # Pure aggregate consistency only. No original reviewer write, engine import,
    # source dataset read, preflight or consumed procedure is invoked.
    checked=old.assess(aggregate,config,policy,arithmetic,contract)
    require(checked["technical_decision"]==prior["technical_decision"]=="AUTOMATED_TECHNICAL_ACCEPT_AGGREGATE_CONSISTENCY_ONLY" and
        checked["audited_private_aggregate_evidence"]==prior["audited_private_aggregate_evidence"])
    files["prior_assessment"]=existing
    hashes={k:q.digest(p) for k,p in files.items()}
    destination=root/"output"/DEST
    require(not destination.exists() and not destination.is_symlink())
    return {"root":root,"q":q,"files":files,"hashes":hashes,"aggregate":aggregate,
        "destination":destination,"source_lock_sha256":expected,"bindings":b}


def assessment(ctx, *, precision=True):
    from .feasibility_recovery import compare
    result=compare(ctx["aggregate"])
    result.update(disclosure_status="PRIVATE_UNRELEASED",source_lock_sha256=ctx["source_lock_sha256"],
        existing_evidence_sha256=ctx["hashes"],formal_gate_changed=False,
        actual_restricted_cohort_processing=False,existing_attempts_consumed_and_preserved=True)
    if precision:
        from .precision_simulation import simulate
        target=result["cohorts"]["ELSA"]
        populations={"current_sensitivity":target["final_counts"],
            "mi_common_baseline":target["components"]["heart_attack"],
            "stroke_common_baseline":target["components"]["stroke"],
            "oracle_predictor_recovery_ceiling":target["imputation_only_oracle_envelope"]}
        estimated={}
        for i,(name,c) in enumerate(populations.items()):
            events,negative=c["events"],c["negatives"]
            if events==0 or negative==0:
                estimated[name]={"status":"NOT_ESTIMABLE_MISSING_CLASS","not_actual_model_performance":True};continue
            estimated[name]=[]
            for fraction in (.3,.5,1.):
                n=int((events+negative)*fraction)
                if n<2:continue
                scenario=dict(id=name+"_hypothetical_test_"+str(fraction),n=n,prevalence=events/(events+negative),
                    auc_a=.70,auc_b=.72,within_class_score_correlation=.8,logit_offset_b=0.,logit_scale_b=1.,
                    replicates=400,seed=810000+i*10+int(fraction*10))
                simulated=simulate(scenario)
                simulated["fraction_interpretation"]="1.0 IS ZERO_SHOT_ALL_TARGET_ONLY_NO_ADAPTATION; OTHER_FRACTIONS_ARE_CANDIDATES_NOT_SPLITS"
                estimated[name].append(simulated)
        result["private_count_conditioned_hypothetical_precision_not_actual_performance"]=estimated
    return result


def write_once(ctx,result):
    from .precision_simulation import exclusive_json
    for k,p in ctx["files"].items():ctx["q"].private_file(p,ctx["root"]);require(ctx["q"].digest(p)==ctx["hashes"][k])
    require(not ctx["destination"].exists() and not ctx["destination"].is_symlink())
    exclusive_json(ctx["destination"],result)
    return ACK


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        print("BLOCKED ISSUE=PRIVATE_REDESIGN_ARGUMENT_INVALID");raise SystemExit(2)


def main(argv=None):
    parser=SafeParser(description="Independent existing-aggregate redesign comparison; no cohort processing")
    parser.add_argument("--private-root",required=True);parser.add_argument("--expected-source-lock-sha256",required=True)
    args=parser.parse_args(argv)
    if os.environ.get("HRS_HUMAN_RUN")!="YES" or any(os.environ.get(k) for k in
        ("CODEX_HOME","CODEX_SESSION_ID","CODEX_THREAD_ID","CI","GITHUB_ACTIONS")):
        print("BLOCKED ISSUE=LOCAL_HUMAN_ENVIRONMENT_REQUIRED");return 2
    try:
        with warnings.catch_warnings(record=True) as observed:
            warnings.simplefilter("always")
            ctx=existing_evidence(Path(args.private_root),Path(__file__).resolve().parents[2],args.expected_source_lock_sha256)
            result=assessment(ctx)
            result["private_numeric_warning_categories_only"]=sorted({type(w.message).__name__ for w in observed})
            acknowledgment=write_once(ctx,result)
        print(acknowledgment);return 0
    except (Exception,KeyboardInterrupt,SystemExit):
        print("BLOCKED ISSUE=PRIVATE_REDESIGN_EVIDENCE_OR_DESTINATION_INVALID_PRESERVE_INPUTS");return 2


if __name__=="__main__":raise SystemExit(main())
