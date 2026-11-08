"""Only new adjudication logic on invented pre-existing assessment fixtures.

Never run the original reviewer, redesign comparison, simulation or cohort
engine, even to construct these fixtures. No actual research volume is used.
"""
from copy import deepcopy
import hashlib
import itertools
import json
import math
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys

import pytest
from phase2.phase2b_public import human_scientific_adjudication as a

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/"phase2/phase2b_public"
AUDIT = ROOT/"phase2/phase2a_6_wave_based_audit"
FRAMEWORK = json.loads((SOURCE/a.FRAMEWORK).read_text())


def pair(events=20, nonevents=100, *, initial_empty=False):
    observed={}; cohorts={}; reviewed={}
    for name in ("HRS", "ELSA"):
        e,z = (500,1000) if name=="HRS" else (events,nonevents)
        b=e+z; stages=[b+60,b+50,b+40,b+30,b+20,b]
        if initial_empty: e=z=b=0;stages=[0]*6
        raw=dict(zip(a.STAGES,stages))
        raw.update(eight_feature_reported_positive=e,eight_feature_screening_or_observed_negative=z,
            negative_analysis="screening_assumed_negative_sensitivity",scientific_approval="AI_SCIENTIFIC_DECISION_ADOPTED",independent_human_approval=False)
        components={k:{"participants":e+z,"events":e,"negatives":z,
            "baseline_scope":"COMMON_BOTH_DISEASE_FREE_BASELINE_NOT_COMPONENT_SPECIFIC_BASELINE"} for k in ("heart_attack","stroke")}
        raw["eight_feature_component_binary"]={k:{"reported_positive":e,a.NEGATIVE:z,"binary_eligible":e+z} for k in components}
        op,oz = (0,0) if initial_empty else (e+2,z+3)
        raw["outcome_states"]={"composite":{"reported_positive":op,a.NEGATIVE:oz}}
        cohorts[name]={"waterfall":[{"stage":k,"retained":v} for k,v in zip(a.STAGES,stages)],
            "final_counts":{"participants":b,"events":e,"negatives":z},"components":components,
            "imputation_only_oracle_envelope":{"events":op,"negatives":oz,"participants_with_known_binary_outcomes":op+oz,"not_empirical_imputation_result":True}}
        observed[name]=raw;reviewed[name]={"initial":stages[0],"final_n":b,"events":e,"negatives":z}
    prior={"identity":"stage_c_postrun_feasibility_review_v1","technical_decision":"AUTOMATED_TECHNICAL_ACCEPT_AGGREGATE_CONSISTENCY_ONLY",
        "disclosure_status":"PRIVATE_UNRELEASED","phase2b_real_data":"NO_GO","scientific_acceptance_granted":False,
        "reviewed_counts":reviewed,"audited_private_aggregate_evidence":{"cohorts":observed}}
    comparison={"identity":"phase2b-feasibility-recovery-v1","disclosure_status":"PRIVATE_UNRELEASED",
        "source_lock_sha256":a.REDESIGN_LOCK,"all_real_modeling_designs":"NO_GO","clinical_incidence_claim":False,
        "actual_test_split_created":False,"formal_gate_changed":False,"actual_restricted_cohort_processing":False,
        "cohorts":cohorts,"strategies":{k:{"empirical_counts":None} for k in ("original_strict","longer_followup","expanded_baseline_and_landmark")},
        "candidate_random_test_reserve_plans":[{"test_fraction_candidate":f,"test_size_candidate":math.floor(cohorts['ELSA']['final_counts']['participants']*f),
            "adaptation_events":budget,"test_event_reserve":200,"test_nonevent_screen_only":100,"validation_events":50,"development_nonevent_ratio_assumption":3,
            "precision_or_execution_authorized":False,"actual_people_or_test_lock_created":False,
            "simultaneous_test_and_remaining_development_reserve_probability":0.0} for f in (.3,.5) for budget in (10,25,50)]}
    return prior,comparison


@pytest.mark.parametrize("events", [0,20,99,100,199,200,1000])
def test_scientific_choice_does_not_confuse_event_count_with_complete_feasibility(events):
    prior,comparison=pair(events)
    r=a.decide(prior,comparison,FRAMEWORK)
    assert r["decision"]=="C_RESTRICT_TO_EXPLORATORY_RESEARCH"
    assert not r["A_retain_design_established"] and not r["B_viable_redesign_established"]
    failed=r["candidate_decisions"]["current_sensitivity_composite"]["necessary_count_failures"]
    assert ("CURRENT_TARGET_TOTAL_CANNOT_SUPPLY_FIXED_TEST_EVENT_AIM" in failed)==(events<200)
    assert r["real_modeling_authorized"] is False and r["formal_gate_changed"] is False
    assert [p["events_left_for_separate_validation"] for p in r["target_event_reserve_arithmetic_not_a_split"]]==[events-200-a for a in (10,25,50)]


def test_observed_description_requires_nonempty_source_target_evidence():
    r=a.decide(*pair(initial_empty=True),FRAMEWORK)
    assert r["decision"]=="D_CURRENT_DATA_INSUFFICIENT"


def test_favorable_hypothetical_precision_and_oracle_never_establish_real_redesign():
    prior,comparison=pair(1000,10000)
    comparison["private_count_conditioned_hypothetical_precision_not_actual_performance"]={"all_widths":0.000001,"synthetic_only":True}
    r=a.decide(prior,comparison,FRAMEWORK)
    assert r["decision"].startswith("C_") and not r["B_viable_redesign_established"]
    assert r["candidate_decisions"]["predictor_only_recovery"]["B_status"].startswith("EVIDENCE_INSUFFICIENT")
    assert r["hypothetical_simulation_can_satisfy_formal_precision_gate"] is False


@pytest.mark.parametrize("mutation", [
    lambda p,c:c["cohorts"]["ELSA"]["final_counts"].update(events=999),
    lambda p,c:p["reviewed_counts"]["ELSA"].update(events=999),
    lambda p,c:c["cohorts"]["ELSA"]["waterfall"][0].update(retained=999),
    lambda p,c:c["cohorts"]["ELSA"]["components"]["stroke"].update(events=999),
    lambda p,c:c["cohorts"]["ELSA"]["imputation_only_oracle_envelope"].update(events=999),
    lambda p,c:p["audited_private_aggregate_evidence"]["cohorts"]["ELSA"].update(negative_analysis="strict_observed_negative"),
    lambda p,c:p["audited_private_aggregate_evidence"]["cohorts"]["ELSA"].update(eight_feature_observed_negative=1),
    lambda p,c:c["candidate_random_test_reserve_plans"][0].update(test_event_reserve=100),
    lambda p,c:c["candidate_random_test_reserve_plans"][0].update(precision_or_execution_authorized=True),
    lambda p,c:c["strategies"]["longer_followup"].update(empirical_counts={"events":500}),
    lambda p,c:c.update(source_lock_sha256="f"*64),
])
def test_inconsistent_evidence_threshold_changes_and_sensitivity_promotion_reject(mutation):
    prior,comparison=pair();mutation(prior,comparison)
    with pytest.raises((a.EvidenceError,KeyError)):a.decide(prior,comparison,FRAMEWORK)


@pytest.mark.parametrize("field,value", [("default_target_test_events",100),("real_modeling_authorized",True),("identity","UNKNOWN")])
def test_framework_cannot_silently_weaken_contract(field,value):
    framework=deepcopy(FRAMEWORK);framework[field]=value
    with pytest.raises(a.EvidenceError):a.decide(*pair(),framework)


@pytest.mark.parametrize("e,z,n", [(0,8,4),(3,5,1),(3,5,4),(3,5,8),(1,9,3),(4,4,2)])
def test_both_class_probability_matches_exhaustive_enumeration(e,z,n):
    combos=list(itertools.combinations(range(e+z),n))
    expected=sum(0<sum(i<e for i in c)<n for c in combos)/len(combos)
    assert a.both_classes_probability(e,z,n)==pytest.approx(expected,abs=1e-12)


def test_bootstrap_single_class_failures_are_not_ignored():
    assert a.bootstrap_both_classes(0,10)==0
    assert a.bootstrap_both_classes(1,9)==pytest.approx(1-.1**10-.9**10)


@pytest.fixture
def bound(tmp_path,monkeypatch):
    sys.path.insert(0,str(AUDIT))
    import stage_c_elsa_recovery_v1 as recovery
    import stage_c_qualified_preflight_v1 as q
    project=tmp_path/"public_project";root=tmp_path/"INVENTED_PRIVATE_ROOT"
    root.mkdir(mode=0o700);(root/"config").mkdir(mode=0o700);(root/"output").mkdir(mode=0o700)
    (project/"phase2/phase2a_6_wave_based_audit").mkdir(parents=True)
    lockfile=project/"phase2/phase2a_6_wave_based_audit/stage_c_elsa_recovery_v1.lock.json"
    lockfile.write_bytes((AUDIT/lockfile.name).read_bytes());lock=json.loads(lockfile.read_text())
    original={"cohorts":{"HRS":{},"ELSA":{"INVENTED_CONFIGURATION_NO_DATA":True}}}
    amendment={"INVENTED_PURE_METADATA_AMENDMENT":True}
    configfile=root/q.INPUTS["config"]
    def save(p,v):p.write_text(json.dumps(v,sort_keys=True)+"\n");p.chmod(0o600)
    save(configfile,original)
    b={k+"_sha256":"a"*64 for k in ["manifest","diagnostics","stage_a_started","stage_a_result","metadata_evidence","config","delegated_record","recovery","recovery_result","source_lock","historical_v1_authorization","historical_v1_started","historical_v1_result","consumed_diagnostic_authorization","consumed_diagnostic_started","consumed_diagnostic_result"]}
    b.update({k:"a"*64 for k in recovery.EXTRA_BINDINGS})
    b.update(config_sha256=q.digest(configfile),recovery_lock_sha256=q.digest(lockfile),source_lock_sha256=lock["original_runtime_lock_sha256"],
        corrected_config_sha256=recovery.fingerprint(original),correction_record_sha256=recovery.fingerprint(amendment))
    for key,name in {"recovery_controller_sha256":"stage_c_elsa_recovery_v1.py","recovery_protocol_sha256":"STAGE_C_ELSA_MAPPING_RECOVERY_PROTOCOL_V1.md","recovery_decision_sha256":"PHASE2A_STAGE_C_ELSA_RECOVERY_DECISION_V1.json","correction_source_sha256":"elsa_interview_status_mapping_v2.py","official_map_sha256":"ELSA_INTERVIEW_OUTCOME_OFFICIAL_MAP_V1.json"}.items():b[key]=lock["files"][name]
    environment={"INVENTED_EXECUTION_ENVIRONMENT":True};b["recovery_environment_sha256"]=hashlib.sha256(json.dumps(environment,sort_keys=True).encode()).hexdigest()
    auth={"identity":recovery.AUTH,"decision":recovery.DECISION,"protocol_id":recovery.PROTOCOL,"author_kind":"HUMAN_OPERATOR",
        "operator":"INVENTED_TEST_OPERATOR_NOT_A_REAL_SIGNOFF","authorized_at_utc":"2000-01-01T00:00:00Z","acknowledgment":recovery.ACK,"scope_acknowledgment":recovery.SCOPE_ACK,
        "bindings":b,"scope":recovery.SCOPE,"provider_and_institutional_scope_confirmed":True,"independent_completed_dictionary_match_confirmed":True,
        "private_failure_context_scope":"CANONICAL_NONKEY_FAULT_OR_RAND_PAIR_ONLY_NO_IDS_OR_FREE_TEXT","ai_respondent_processing_authorized":False,
        "phase2b_authorized":False,"independent_distributor_authentication":False,"approved_analyses":recovery.ANALYSES}
    files={"authorization":root/"config"/(recovery.VERSION+".authorization.json"),"config":configfile,
        "started":recovery.paths(root)["started"],"result":recovery.paths(root)["result"]}
    save(files["authorization"],auth)
    env={"bindings":b,"attempt_consumed":True,"phase2b_authorized":False,"recovery_authorization_sha256":q.digest(files["authorization"]),
        "protocol_id":recovery.PROTOCOL,"controller_sha256":b["recovery_controller_sha256"],"evidence_tier":"QUALIFIED_LOCAL_ARCHIVE_PROVENANCE",
        "v1_retried":False,"cause_diagnostic_retried":False,"independent_distributor_authentication":False,"independent_human_scientific_approval":False,"dependency_environment":environment}
    save(files["started"],{"identity":recovery.VERSION+"_started","status":"STARTED_NO_RETRY",**env})
    save(files["result"],{"identity":recovery.VERSION+"_result","status":"COMPLETED_PRIVATE_REVIEW_PENDING","stage":"NONE","substage":"NONE","code":"NONE","category":"NONE","returncode":0,"private_aggregates_sha256":"a"*64,**env})
    prior,comparison=pair();hashes={k:q.digest(p) for k,p in files.items()};hashes["output"]="a"*64
    prior["integrity"]={"completed_run_bindings":b,"existing_input_sha256":hashes,"review_source_lock_sha256":'WITHHELD_REFERENCE_BINDING',"receipt_bindings_verified":True}
    p=root/"output/stage_c_elsa_recovery_v1_private_feasibility_assessment_v1.json";save(p,prior)
    comparison["existing_evidence_sha256"]={**hashes,"prior_assessment":q.digest(p)}
    cp=root/"output/phase2b_feasibility_redesign_v1.private.json";save(cp,comparison)
    previous=SimpleNamespace(OLD_LOCK=prior["integrity"]["review_source_lock_sha256"],DEST=cp.name)
    old=SimpleNamespace(REPORT=p.name)
    patch=SimpleNamespace(correct_interview_maps=lambda spec:(deepcopy(spec),amendment))
    boot=(None,None,q,None,patch,{"trusted_inputs":{"config_sha256":b["config_sha256"]}},None,lock)
    monkeypatch.setattr(a,"public_context",lambda *_:(previous,old,recovery,boot,FRAMEWORK))
    return root,project,files


def test_reads_only_two_assessments_and_four_metadata_files_no_raw_aggregate(bound,monkeypatch,capsys):
    root,project,metadata=bound
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()}
    original=Path.open
    def guard(path,*args,**kwargs):
        if root in path.parents:assert path in before
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,"open",guard)
    ctx=a.read_evidence(root,project,"a"*64)
    assert len(ctx["files"])==6 and not (root/"output/stage_c_elsa_recovery_v1_private_aggregates.json").exists()
    result=a.decide(ctx["prior"],ctx["comparison"],FRAMEWORK)
    assert a.write_once(ctx,result)==a.ACK
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())
    assert set(p for p in root.rglob("*") if p.is_file())-set(before)=={ctx["destination"]}
    assert ctx["destination"].stat().st_mode & 0o777==0o600
    with pytest.raises(FileExistsError):a.write_once(ctx,result)
    assert capsys.readouterr().out==""


@pytest.mark.parametrize("key", ["assessment","comparison","authorization","started","result","config"])
def test_changed_binding_or_source_record_blocks_without_repair(bound,key):
    root,project,metadata=bound
    path=metadata[key] if key in metadata else root/"output"/("stage_c_elsa_recovery_v1_private_feasibility_assessment_v1.json" if key=="assessment" else "phase2b_feasibility_redesign_v1.private.json")
    data=json.loads(path.read_text())
    if key=="assessment":data["integrity"]["review_source_lock_sha256"]="f"*64
    elif key=="comparison":data["existing_evidence_sha256"]["prior_assessment"]="f"*64
    else:data["INVENTED_TAMPER"]=True
    path.write_text(json.dumps(data))
    with pytest.raises(Exception):a.read_evidence(root,project,"a"*64)
    assert not (root/"output"/a.DEST).exists()


@pytest.mark.parametrize("marker", ["CODEX_HOME","CODEX_SESSION_ID","CODEX_THREAD_ID","CI","GITHUB_ACTIONS"])
def test_agent_refusal_before_access(marker,monkeypatch,capsys):
    monkeypatch.setenv(marker,"INVENTED_AGENT")
    monkeypatch.setattr(a,"read_evidence",lambda *_:pytest.fail("private boundary crossed"))
    assert a.main(["--private-root","/INVENTED","--expected-source-lock-sha256","a"*64])==2
    assert capsys.readouterr().out==a.NOT_COMPLETED+"\n"


@pytest.mark.parametrize("case", ["C","D","insufficient"])
def test_every_completed_empirical_verdict_has_same_public_ack(bound,case,monkeypatch,capsys):
    root,project,_=bound;ctx=a.read_evidence(root,project,"a"*64)
    if case=="D":ctx["prior"],ctx["comparison"]=pair(initial_empty=True)
    if case=="insufficient":ctx["comparison"]["cohorts"]={}
    monkeypatch.setattr(a,"os",SimpleNamespace(environ={"HRS_HUMAN_RUN":"YES"},open=__import__('os').open,fdopen=__import__('os').fdopen,fsync=__import__('os').fsync,O_WRONLY=__import__('os').O_WRONLY,O_CREAT=__import__('os').O_CREAT,O_EXCL=__import__('os').O_EXCL))
    monkeypatch.setattr(a,"read_evidence",lambda *_:ctx)
    assert a.main(["--private-root","/INVENTED","--expected-source-lock-sha256","a"*64])==0
    assert capsys.readouterr().out==a.ACK+"\n"
    decision=json.loads(ctx["destination"].read_text())["decision"]
    assert decision=={"C":"C_RESTRICT_TO_EXPLORATORY_RESEARCH","D":"D_CURRENT_DATA_INSUFFICIENT","insufficient":"EVIDENCE_INSUFFICIENT"}[case]


def test_public_bootstrap_no_old_analysis_or_engine_imports():
    expected=a.sha(SOURCE/a.LOCK)
    code="""import sys
from pathlib import Path
from phase2.phase2b_public import human_scientific_adjudication as a
a.public_context(Path(sys.argv[1]),sys.argv[2])
assert 'pandas' not in sys.modules
assert 'stage_c_multifield_workflow' not in sys.modules
assert 'phase2.phase2b_public.precision_simulation' not in sys.modules
assert 'phase2.phase2b_public.feasibility_recovery' not in sys.modules
print('PUBLIC_METADATA_BOOTSTRAP_PASS')
"""
    p=subprocess.run([sys.executable,"-B","-c",code,str(ROOT),expected],text=True,capture_output=True,cwd=ROOT)
    assert p.returncode==0,p.stdout+p.stderr
    assert p.stdout=="PUBLIC_METADATA_BOOTSTRAP_PASS\n"


def test_wrong_adjudication_lock_fails_before_private_access():
    with pytest.raises(a.EvidenceError):a.public_context(ROOT,"0"*64)


def test_interrupted_new_decision_preserves_partial_file_and_all_inputs(bound,monkeypatch):
    root,project,_=bound;ctx=a.read_evidence(root,project,"a"*64)
    before={p:p.read_bytes() for p in ctx["files"].values()}
    def interrupted(result,stream,**kwargs):
        stream.write('{"INVENTED_PARTIAL":');stream.flush();raise KeyboardInterrupt()
    monkeypatch.setattr(a.json,"dump",interrupted)
    with pytest.raises(KeyboardInterrupt):a.write_once(ctx,a.decide(ctx["prior"],ctx["comparison"],FRAMEWORK))
    partial=ctx["destination"].read_bytes();assert partial
    with pytest.raises(FileExistsError):a.write_once(ctx,{"decision":"EVIDENCE_INSUFFICIENT"})
    assert ctx["destination"].read_bytes()==partial and all(p.read_bytes()==v for p,v in before.items())
