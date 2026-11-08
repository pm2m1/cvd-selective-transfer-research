"""Invented records and public documentation only. No private result access."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from public_reference import references, verify_frozen
old, fixtures, M, P, candidate = references()


def v(p, w):
    return next(x for x in p['visits'] if x['wave'] == w)


def status(p, w, outcome, proxy):
    raw = v(p, w)['raw']
    raw['indoc' if w == 1 else f'w{w}indout'] = outcome
    raw['askpx1' if w < 3 else 'askpx'] = proxy


def rejection(engine, people):
    try:
        engine.validate_people(people, M)
    except engine.CountError as exc:
        return str(exc)
    return None


@pytest.mark.parametrize('w', [1, 2, 3, 4, 5, 6, 7, 8, 9])
def test_consistent_completed_personal_passes(w):
    p = fixtures.person(M)
    assert old.interview(v(p, w), M) == 'personal'
    assert rejection(old, [p]) is None
    assert old.analyze([p], M, P) == candidate.analyze([p], M, P)


@pytest.mark.parametrize('w', [4, 6, 7, 9])
@pytest.mark.parametrize('outcome,proxy,kind', [(11, 0, 'personal'), (21, 0, 'partial'),
          (13, 1, 'proxy'), (23, 1, 'proxy'), (24, 0, 'institutional'), (25, 1, 'proxy')])
@pytest.mark.parametrize('flag', [0, None, '.a'])
def test_exact_conflict_branch_for_all_targeted_responding_states(w, outcome, proxy, kind, flag):
    p = fixtures.person(M)
    status(p, w, outcome, proxy)
    p['participation'][str(w)] = flag
    assert old.interview(v(p, w), M) == kind
    assert rejection(old, [p]) == 'PARTICIPATION_INTERVIEW_CONFLICT'
    expected = 'PARTICIPATION_INTERVIEW_CONFLICT' if flag == 0 else 'PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED'
    assert rejection(candidate, [p]) == expected


@pytest.mark.parametrize('w', [4, 6, 7, 9])
@pytest.mark.parametrize('outcome,proxy', [(13, 1), (21, 0), (23, 1), (24, 0), (25, 1)])
def test_legitimate_responding_states_are_not_contradictions_when_inw_one(w, outcome, proxy):
    p = fixtures.person(M)
    status(p, w, outcome, proxy)
    assert rejection(old, [p]) is None
    if w in (4, 6):
        result = old.analyze([p], M, P)['designs'][f'W{w}_W{w+3}']
        assert result['flow_ordered']['excluded_nonpersonal_baseline'] == 1
        assert result['flow_ordered']['verified_MI_stroke_free'] == 0
    assert old.analyze([p], M, P) == candidate.analyze([p], M, P)


@pytest.mark.parametrize('missing', [None, '.', '.a', '.z', float('nan')])
def test_missing_inw_shares_original_code_and_stays_blocked(missing):
    p = fixtures.person(M)
    p['participation']['6'] = missing
    assert rejection(old, [p]) == 'PARTICIPATION_INTERVIEW_CONFLICT'
    assert rejection(candidate, [p]) == 'PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED'


@pytest.mark.parametrize('invalid', [-1, -8, -9, 2])
def test_nonbinary_harmonized_values_fail_earlier(invalid):
    p = fixtures.person(M)
    p['participation']['6'] = invalid
    assert rejection(old, [p]) == 'PARTICIPATION_CODE_INVALID'
    assert rejection(candidate, [p]) == 'PARTICIPATION_CODE_INVALID'


@pytest.mark.parametrize('w', [4, 6, 7, 9])
def test_absent_core_with_inw_zero_and_reentry_is_not_conflict(w):
    p = fixtures.person(M)
    p['visits'] = [x for x in p['visits'] if x['wave'] != w]
    p['participation'][str(w)] = 0
    assert rejection(old, [p]) is None
    assert old.analyze([p], M, P) == candidate.analyze([p], M, P)
    if w == 4:
        assert old.reference(p, 5) == ('interval', 3)
    if w == 7:
        assert old.reference(p, 8) == ('interval', 6)
        assert old.followup(p, 6, 9, 'mi', M, 'wave_window') == 'OBSERVED_NONEVENT'


@pytest.mark.parametrize('w', [4, 6])
def test_absent_core_but_inw_one_goes_to_missing_core_baseline_exclusion(w):
    p = fixtures.person(M)
    p['visits'] = [x for x in p['visits'] if x['wave'] != w]
    assert rejection(old, [p]) is None
    result = old.analyze([p], M, P)['designs'][f'W{w}_W{w+3}']
    assert result['flow_ordered']['excluded_missing_core'] == 1


@pytest.mark.parametrize('w', [4, 6, 7, 9])
@pytest.mark.parametrize('outcome', [None, -1, -8, -9])
def test_unknown_core_with_no_proxy_flag_not_interviewed_or_nonevent(w, outcome):
    p = fixtures.person(M)
    status(p, w, outcome, -1)
    p['participation'][str(w)] = 0
    assert old.interview(v(p, w), M) == 'unknown'
    assert rejection(old, [p]) is None
    assert old.observation(v(p, w), 'mi', M) == 'not_personal'
    assert old.analyze([p], M, P) == candidate.analyze([p], M, P)


@pytest.mark.parametrize('outcome', [None, -1, -8, -9, 31, 43, 95])
def test_proxy_flag_precedence_can_route_ambiguous_or_nonresponse_outcome_to_conflict(outcome):
    # Each scalar is in its own W6 dictionary domain or missing; joint legitimacy
    # is NOT asserted. This exposes precedence, not evidence of a real observation.
    p = fixtures.person(M)
    status(p, 6, outcome, 1)
    p['participation']['6'] = 0
    assert old.interview(v(p, 6), M) == 'proxy'
    assert rejection(old, [p]) == 'PARTICIPATION_INTERVIEW_CONFLICT'
    assert rejection(candidate, [p]) == 'PARTICIPATION_INTERVIEW_CONFLICT'


@pytest.mark.parametrize('outcome', [31, 43, 44, 57, 71, 95])
def test_documented_nonresponse_with_no_proxy_does_not_trigger_target_check(outcome):
    p = fixtures.person(M)
    status(p, 9, outcome, -1)
    p['participation']['9'] = 0
    assert rejection(old, [p]) is None
    assert old.interview(v(p, 9), M) == ('death_status' if outcome == 95 else 'unknown')
    assert old.followup(p, 6, 9, 'mi', M, 'wave_window') != 'OBSERVED_NONEVENT'


def test_wave1_proxy_no_code_is_two_not_zero():
    p = fixtures.person(M)
    assert old.interview(v(p, 1), M) == 'personal'
    status(p, 1, 11, 0)
    assert rejection(old, [p]) == 'CODE_OUTSIDE_OFFICIAL_DOMAIN'


def test_wave_specific_codes_not_copied_across_waves():
    p = fixtures.person(M)
    status(p, 3, 26, 0)
    assert old.interview(v(p, 3), M) == 'partial'
    status(p, 4, 26, 0)
    assert rejection(old, [p]) == 'CODE_OUTSIDE_OFFICIAL_DOMAIN'


def test_institutional_label_71_is_not_completed_institutional_24():
    p = fixtures.person(M)
    status(p, 6, 71, -1)
    p['participation']['6'] = 0
    assert old.interview(v(p, 6), M) == 'unknown'
    assert rejection(old, [p]) is None


def test_multiple_conflicts_original_fails_first_not_whole_inventory():
    p = fixtures.person(M)
    p['participation']['4'] = None
    p['participation']['6'] = 0
    assert rejection(old, [p]) == 'PARTICIPATION_INTERVIEW_CONFLICT'
    assert rejection(candidate, [p]) == 'PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED'
    p['visits'] = [x for x in p['visits'] if x['wave'] != 4]
    assert rejection(candidate, [p]) == 'PARTICIPATION_INTERVIEW_CONFLICT'


def test_conflicts_before_baseline_or_after_w7_still_abort_global_validation():
    for w in (1, 8, 9):
        p = fixtures.person(M)
        p['participation'][str(w)] = 0
        with pytest.raises(old.CountError, match='PARTICIPATION_INTERVIEW_CONFLICT'):
            old.analyze([p], M, P)


def test_conflict_in_age_ineligible_person_is_not_skipped():
    p = fixtures.person(M)
    v(p, 4)['raw']['indager'] = v(p, 6)['raw']['indager'] = 49
    p['participation']['9'] = 0
    with pytest.raises(old.CountError, match='PARTICIPATION_INTERVIEW_CONFLICT'):
        old.analyze([p], M, P)


def test_unknown_interview_and_proxy_not_personal_negative():
    p = fixtures.person(M)
    status(p, 9, 13, 1)
    assert old.followup(p, 6, 9, 'stroke', M, 'wave_window') == 'UNKNOWN_PROXY'
    status(p, 9, None, -1)
    assert old.followup(p, 6, 9, 'stroke', M, 'wave_window') != 'OBSERVED_NONEVENT'


def test_exact_frozen_wrapper_issue_and_consumed_receipt_synthetic_only(tmp_path, monkeypatch):
    import run_counts
    import read_release
    import local_execution
    p = fixtures.person(M)
    p['participation']['6'] = 0
    # Mock environment and source I/O only with an invented in-memory population.
    monkeypatch.setattr(run_counts, 'require_local', lambda: None)
    monkeypatch.setattr(read_release, 'load_people', lambda *_: ([p], {}, {}))
    config = {'schema': 'elsa-final-count-local-config-v1', 'mode': 'independent_local_only',
              'no_models': True, 'source_use_review': 'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION',
              'protocol_sha256': local_execution.sha(run_counts.ROOT / 'PROTOCOL.json'),
              'mapping_sha256': local_execution.sha(run_counts.ROOT / 'official_variable_map.json')}
    output = tmp_path / 'INVENTED_CONSUMED_OUTPUT'
    with pytest.raises(local_execution.Rejected) as exc:
        with local_execution.exclusive_output(output):
            run_counts.execute(config, output)
    assert exc.value.code == 'ELIGIBILITY_PROCESSING_PARTICIPATION_INTERVIEW_CONFLICT'
    receipt = json.loads((output / 'completion.private.json').read_text())
    assert receipt == {'status': 'FAILED_NO_RETRY',
                       'issue': 'ELIGIBILITY_PROCESSING_PARTICIPATION_INTERVIEW_CONFLICT', 'attempt_consumed': True}
    assert not (output / 'final_counts.private.json').exists()
    with pytest.raises(local_execution.Rejected, match='OUTPUT_ALREADY_EXISTS_NO_RETRY'):
        with local_execution.exclusive_output(output):
            pass


def test_candidate_does_not_fix_or_admit_any_failed_person():
    for flag in (0, None, '.a'):
        p = fixtures.person(M)
        p['participation']['6'] = flag
        assert rejection(old, [p]) is not None and rejection(candidate, [p]) is not None


def test_candidate_is_exact_two_statement_observability_change():
    base = verify_frozen()
    before = (base / 'count_engine.py').read_text()
    after = (ROOT / 'proposal/count_engine_observability_v1.py').read_text()
    before_block = "                need(code(p['participation'][str(w)])==1,'PARTICIPATION_INTERVIEW_CONFLICT')"
    after_block = "                flag=code(p['participation'][str(w)])\n                need(flag is not None,'PARTICIPATION_INTERVIEW_STATUS_UNRESOLVED')\n                need(flag==1,'PARTICIPATION_INTERVIEW_CONFLICT')"
    assert before.replace(before_block, after_block) == after


def test_public_manual_explicitly_covers_partial_proxy_institutional():
    base = verify_frozen()
    text = (base / 'public_documentation/harmonized_elsa_H.txt').read_text()
    assert 'or partial interview either in person, through a proxy, or at an institution are considered to have responded.' in text
    assert 'inw6, inw7, inw8, inw9, and' in text


def test_synthetic_reproducer_cannot_accept_external_input():
    r = subprocess.run([sys.executable, '-B', str(ROOT / 'reproduce_conflict.py'), '--config',
                        'INVENTED_NOT_READ'], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr == ''
    assert r.stdout == 'STOP ISSUE=SYNTHETIC_REPRODUCER_ACCEPTS_NO_EXTERNAL_INPUTS\n'


def test_synthetic_reproducer_has_no_clinical_claims():
    r = subprocess.run([sys.executable, '-B', str(ROOT / 'reproduce_conflict.py')], capture_output=True, text=True)
    assert r.returncode == 0 and r.stderr == ''
    assert len(r.stdout.splitlines()) == 6
    assert all(line.startswith('SYNTHETIC_ONLY ') for line in r.stdout.splitlines())


def test_original_public_files_unchanged():
    assert verify_frozen().is_dir()


@pytest.mark.parametrize('wave,flag,outcome,proxy,expected', [
    (6, 0, 11, 0, 'KNOWN_RESPONSE_FLAG_DISAGREEMENT'),
    (6, '.a', 11, 0, 'RESPONSE_FLAG_UNRESOLVED'),
    (9, 0, 95, -1, 'NO_TARGET_CONFLICT'),
    (4, 1, 13, 1, 'NO_TARGET_CONFLICT'),
    (4, 0, 26, 0, 'SOURCE_INPUT_DOMAIN_ERROR'),
    (6, -8, 11, 0, 'PARTICIPATION_INPUT_DOMAIN_ERROR')])
def test_minimal_pure_diagnostic_classification(wave, flag, outcome, proxy, expected):
    from diagnostic_classifier import classify_observation
    r = classify_observation(old, M, wave, flag, outcome, proxy)
    assert r['disposition'] == expected
    assert set(r) == {'wave', 'disposition', 'decoder_kind', 'decoder_basis'}
    assert 'token' not in r and 'individual_outcome' not in r and 'participation' not in r


def test_diagnostic_detects_proxy_fallback_without_labeling_it_legitimate():
    from diagnostic_classifier import classify_observation
    r = classify_observation(old, M, 6, 0, None, 1)
    assert r['decoder_basis'] == 'PROXY_FLAG_FALLBACK'
    assert r['disposition'] == 'KNOWN_RESPONSE_FLAG_DISAGREEMENT'
