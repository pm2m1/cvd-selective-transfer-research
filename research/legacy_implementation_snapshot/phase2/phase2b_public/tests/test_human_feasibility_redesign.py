"""Existing-evidence integration uses only invented temporary private files."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import warnings

import pytest
from phase2.phase2b_public import human_feasibility_redesign as h

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/"phase2/phase2a_6_wave_based_audit"
sys.path.insert(0,str(AUDIT/"tests"));sys.path.insert(0,str(AUDIT))
import human_stage_c_postrun_feasibility_review as old
from test_stage_c_postrun_feasibility_review import completed, recovery_case, diagnostic_case, execution_case, case
import stage_c_elsa_recovery_v1 as recovery
from test_feasibility_recovery import invented_cohort


@pytest.fixture
def existing(completed,monkeypatch):
    x=completed;project=x["source"].parents[1]
    correct_audit=project/"phase2/phase2a_6_wave_based_audit";correct_audit.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(x["source"]/"stage_c_elsa_recovery_v1.lock.json",correct_audit/"stage_c_elsa_recovery_v1.lock.json")
    # Preserve the verified synthetic context provided by existing fixtures.
    context=old.verify_sources(x["source"],"a"*64)
    monkeypatch.setattr(h,"public_context",lambda *_:(old,*context))
    ctx=old.bound_inputs(x["source"],x["root"],"a"*64)
    ctx["source_lock_sha256"]=h.OLD_LOCK  # Synthetic record explicitly bound to this interface token.
    assert old.review_once(ctx)==old.ACK
    x["project"]=project
    return x


def test_reanalysis_reads_aggregate_only_and_never_mutates_evidence(existing,capsys):
    x=existing
    before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in x["root"].rglob("*") if p.is_file()}
    ctx=h.existing_evidence(x["root"],x["project"],"a"*64)
    assert len(ctx["files"])==6 and "detail" not in ctx["files"]
    result=h.assessment(ctx,precision=False)
    assert result["all_real_modeling_designs"]=="NO_GO"
    assert h.write_once(ctx,result)==h.ACK
    assert all((p.read_bytes(),p.stat().st_mtime_ns)==v for p,v in before.items())
    assert set(p for p in x["root"].rglob("*") if p.is_file())-set(before)=={ctx["destination"]}
    assert ctx["destination"].stat().st_mode & 0o777 == 0o600
    with pytest.raises(h.EvidenceError):h.write_once(ctx,result)
    assert capsys.readouterr().out==""


@pytest.mark.parametrize("kind", ["old_report_hash","completed_result","config","aggregate","authorization"])
def test_tamper_preserves_no_go_and_no_output(existing,kind):
    x=existing
    if kind=="old_report_hash":
        p=x["root"]/"output"/old.REPORT;r=json.loads(p.read_text());r["integrity"]["existing_input_sha256"]["output"]="f"*64;p.write_text(json.dumps(r))
    else:
        paths=recovery.paths(x["root"])
        p=paths["result"] if kind=="completed_result" else paths["output"] if kind=="aggregate" else x["root"]/x["q"].INPUTS["config"] if kind=="config" else x["root"]/"config"/(recovery.VERSION+".authorization.json")
        p.write_bytes(p.read_bytes()+b"\n")
    with pytest.raises(Exception):h.existing_evidence(x["root"],x["project"],"a"*64)
    assert not (x["root"]/"output"/h.DEST).exists()


@pytest.mark.parametrize("agent", ["CODEX_HOME","CODEX_THREAD_ID","CODEX_SESSION_ID","CI","GITHUB_ACTIONS"])
def test_guard_before_private_read(agent,monkeypatch,capsys):
    monkeypatch.setenv(agent,"SYNTHETIC_TEST")
    monkeypatch.setattr(h,"existing_evidence",lambda *_:pytest.fail("private boundary crossed"))
    assert h.main(["--private-root","/INVENTED","--expected-source-lock-sha256","a"*64])==2
    assert capsys.readouterr().out=="BLOCKED ISSUE=LOCAL_HUMAN_ENVIRONMENT_REQUIRED\n"


def test_wrong_public_source_lock_rejects():
    with pytest.raises(h.EvidenceError):h.public_context(ROOT,"0"*64)


def test_count_dependent_findings_never_print(existing,capsys):
    x=existing;ctx=h.existing_evidence(x["root"],x["project"],"a"*64)
    result=h.assessment(ctx,precision=True)
    assert result["private_count_conditioned_hypothetical_precision_not_actual_performance"]["stroke_common_baseline"]["status"]=="NOT_ESTIMABLE_MISSING_CLASS"
    assert h.write_once(ctx,result)==h.ACK
    assert capsys.readouterr().out==""


def test_public_context_never_imports_cohort_engine_or_pandas():
    expected=h.sha(ROOT/"phase2/phase2b_public"/h.LOCK)
    code="""import sys
from pathlib import Path
from phase2.phase2b_public import human_feasibility_redesign as h
h.public_context(Path(sys.argv[1]),sys.argv[2])
assert 'pandas' not in sys.modules
assert 'stage_c_multifield_workflow' not in sys.modules
assert 'wave_based_aggregate_audit' not in sys.modules
print('PUBLIC_LOCKS_ONLY_PASS')
"""
    result=subprocess.run([sys.executable,"-B","-c",code,str(ROOT),expected],capture_output=True,text=True,cwd=ROOT)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout=="PUBLIC_LOCKS_ONLY_PASS\n"


def test_private_count_conditioned_simulation_is_labelled_hypothetical_and_never_prints(capsys):
    c=invented_cohort()
    ctx={"aggregate":{"analyses":{"screening_assumed_negative_sensitivity":{"cohorts":{"HRS":c,"ELSA":c}}}},
        "source_lock_sha256":"a"*64,"hashes":{}}
    result=h.assessment(ctx,precision=True)
    simulations=result["private_count_conditioned_hypothetical_precision_not_actual_performance"]
    assert simulations["stroke_common_baseline"]["status"]=="NOT_ESTIMABLE_MISSING_CLASS"
    for s in simulations["current_sensitivity"]:
        assert s["synthetic_only"] and s["real_modeling"]=="NO_GO"
        assert s["training_adaptation_imputation_uncertainty_included"] is False
    assert capsys.readouterr().out==""


def test_concurrent_change_and_existing_destination_block(existing):
    x=existing;ctx=h.existing_evidence(x["root"],x["project"],"a"*64);result=h.assessment(ctx,precision=False)
    p=ctx["files"]["output"];before=p.read_bytes();p.write_bytes(before+b"\n")
    with pytest.raises(h.EvidenceError):h.write_once(ctx,result)
    assert not ctx["destination"].exists()


def test_cli_warning_context_is_never_released(monkeypatch,capsys):
    # Synthetic environment object, not a human attestation or real CLI run.
    from types import SimpleNamespace
    monkeypatch.setattr(h,"os",SimpleNamespace(environ={"HRS_HUMAN_RUN":"YES"}))
    monkeypatch.setattr(h,"existing_evidence",lambda *_:{"INVENTED":True})
    def synthetic_assessment(_):
        warnings.warn("INVENTED_PRIVATE_CONTEXT_MUST_NOT_BE_PRINTED",RuntimeWarning)
        return {"all_real_modeling_designs":"NO_GO"}
    monkeypatch.setattr(h,"assessment",synthetic_assessment)
    def write(ctx,result):
        assert result["private_numeric_warning_categories_only"]==["RuntimeWarning"]
        return h.ACK
    monkeypatch.setattr(h,"write_once",write)
    assert h.main(["--private-root","/INVENTED_NOT_REAL","--expected-source-lock-sha256","a"*64])==0
    captured=capsys.readouterr()
    assert captured.out==h.ACK+"\n" and captured.err==""
