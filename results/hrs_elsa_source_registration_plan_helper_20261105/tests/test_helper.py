"""Temporary invented files only; no actual private paths or clinical archives."""
import copy
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import prepare_plan as h
import check_readiness as c


@pytest.fixture
def sample(tmp_path):
    parent = tmp_path / 'invented_run'
    parent.mkdir(mode=0o700)
    tools = tmp_path / 'invented_count_tools'
    tools.mkdir()
    for name in ('run_counts.py', 'read_release.py', 'RELEASE_MANIFEST.json'):
        (tools / name).write_text('INVENTED_PUBLIC_TOOL_PLACEHOLDER')
    archive = tmp_path / '5050stata_invented_V1.zip'
    archive.write_bytes(b'INVENTED_ARCHIVE_NOT_TO_BE_OPENED_BY_HELPER')
    plan = {'schema': h.SCHEMA, 'mode': 'independent_local_only',
            'source_use_review': 'UNRESOLVED_NOT_AUTHORIZED', 'reviewed_scope': [],
            'count_tool_root': str(tools), 'register_measurements': False,
            'input_archives': [{'archive_id': 'invented_archive', 'archive_path': h.PLACEHOLDER,
              'verification_mode': 'first_local_registration', 'expected_archive_sha256': None,
              'study_id': 'UKDS_SN5050', 'archive_edition': 'UNRESOLVED'}],
            'invented_scientific_bindings': {'protocol_sha256': 'a'*64, 'unchanged': ['x', 7, False]}}
    p = parent / 'registration.reviewed.json'
    original = (json.dumps(plan, separators=(',', ':')) + '\n').encode()
    p.write_bytes(original)
    p.chmod(0o600)
    return p, archive, tools, plan, original


def run(s):
    return h.prepare(s[0], s[1], s[2])


def expect_stop(s, issue):
    with pytest.raises(h.Stop, match='^' + issue + '$'):
        run(s)
    assert s[0].read_bytes() == s[4]


def test_success_only_one_field_changes_and_backup_is_exact(sample):
    p, archive, _, before, raw = sample
    assert run(sample) == 'PLAN_ARCHIVE_PATH_UPDATED'
    after = json.loads(p.read_bytes())
    expected = copy.deepcopy(before)
    expected['input_archives'][0]['archive_path'] = str(archive.resolve())
    assert after == expected
    assert (p.parent / (p.name + h.BACKUP_SUFFIX)).read_bytes() == raw
    for f in (p, p.parent / (p.name + h.BACKUP_SUFFIX)):
        assert stat.S_IMODE(f.stat().st_mode) == 0o600
    assert sorted(x.name for x in p.parent.iterdir()) == sorted([p.name, p.name + h.BACKUP_SUFFIX])


def test_archive_contents_never_opened(sample, monkeypatch):
    original = Path.open
    def guarded(p, *a, **kw):
        assert p != sample[1], 'Attempt to read archive contents'
        return original(p, *a, **kw)
    monkeypatch.setattr(Path, 'open', guarded)
    assert run(sample) == 'PLAN_ARCHIVE_PATH_UPDATED'
    assert c.readiness(sample[0], sample[2])[2] == 'ARCHIVE_FILE: PRESENT'


def test_already_configured_is_byte_preserving(sample):
    run(sample)
    before = {p.name: p.read_bytes() for p in sample[0].parent.iterdir()}
    assert run(sample) == 'PLAN_ALREADY_CONFIGURED'
    assert before == {p.name: p.read_bytes() for p in sample[0].parent.iterdir()}


def test_different_existing_path_refused(sample):
    p, _, _, plan, _ = sample
    plan['input_archives'][0]['archive_path'] = str(p.parent / 'invented_other_V1.zip')
    p.write_text(json.dumps(plan))
    before = p.read_bytes()
    with pytest.raises(h.Stop, match='DIFFERENT_EXISTING_ARCHIVE_PATH'):
        run(sample)
    assert p.read_bytes() == before
    assert len(list(p.parent.iterdir())) == 1


def test_missing_archive(sample):
    sample[1].unlink()
    expect_stop(sample, 'ARCHIVE_FILE_MISSING_OR_NOT_REGULAR')


def test_archive_directory_not_file(sample):
    sample[1].unlink()
    sample[1].mkdir()
    expect_stop(sample, 'ARCHIVE_FILE_MISSING_OR_NOT_REGULAR')


def test_archive_symlink(sample):
    archive = sample[1]
    real = archive.with_name('invented_link_target')
    archive.rename(real)
    archive.symlink_to(real)
    expect_stop(sample, 'SYMLINK_REFUSED')


def test_relative_archive(sample):
    with pytest.raises(h.Stop, match='ABSOLUTE_PATH_REQUIRED'):
        h.prepare(sample[0], 'invented_relative_V1.zip', sample[2])


@pytest.mark.parametrize('name', ['5050stata_invented_V1(1).zip', 'wrong_V1.zip', '5050stata_invented_V2.zip'])
def test_wrong_basename(sample, name):
    p = sample[1].with_name(name)
    sample[1].rename(p)
    with pytest.raises(h.Stop, match='ARCHIVE_BASENAME_NOT_EXPECTED_V1'):
        h.prepare(sample[0], p, sample[2])


@pytest.mark.parametrize('name', ['registration.authorization.json', 'auth.json', 'alternate.authorization.private.json'])
def test_existing_authorization_refusal_without_reading(sample, monkeypatch, name):
    auth = sample[0].parent / name
    auth.write_bytes(b'INVENTED_DO_NOT_READ_AUTHORIZATION')
    original = Path.open
    def guard(p, *a, **kw):
        assert p != auth
        return original(p, *a, **kw)
    monkeypatch.setattr(Path, 'open', guard)
    expect_stop(sample, 'AUTHORIZATION_ALREADY_PRESENT')


@pytest.mark.parametrize('marker', ['operation_started.private.json', 'completion.private.json'])
@pytest.mark.parametrize('nested', [False, True])
def test_execution_markers_preserved(sample, marker, nested):
    root = sample[0].parent
    if nested:
        root = root / 'registration_output'
        root.mkdir()
    evidence = root / marker
    evidence.write_bytes(b'INVENTED_CONSUMED_EVIDENCE')
    expect_stop(sample, 'CONSUMED_OPERATION_PRESENT')
    assert evidence.read_bytes() == b'INVENTED_CONSUMED_EVIDENCE'


def test_existing_empty_output_refused(sample):
    (sample[0].parent / 'registration_output').mkdir()
    expect_stop(sample, 'EXECUTION_OUTPUT_ALREADY_PRESENT')


def test_unknown_sibling_refused_without_opening(sample):
    (sample[0].parent / 'unrecognized_invented_artifact').write_bytes(b'invented')
    expect_stop(sample, 'RUN_DIRECTORY_NOT_PRISTINE')


def test_explicit_external_authorization_refused(sample, tmp_path):
    auth = tmp_path / 'invented_external_auth.json'
    auth.write_bytes(b'invented')
    with pytest.raises(h.Stop, match='AUTHORIZATION_ALREADY_PRESENT'):
        h.prepare(sample[0], sample[1], sample[2], authorization=auth)


def test_existing_backup_refused_without_overwrite(sample):
    b = sample[0].with_name(sample[0].name + h.BACKUP_SUFFIX)
    b.write_bytes(b'INVENTED_PREVIOUS_BACKUP')
    expect_stop(sample, 'PLAN_BACKUP_ALREADY_EXISTS')
    assert b.read_bytes() == b'INVENTED_PREVIOUS_BACKUP'


def test_stale_helper_lock_refused(sample):
    (sample[0].parent / h.LOCK_NAME).write_bytes(b'invented lock')
    expect_stop(sample, 'HELPER_LOCK_ALREADY_PRESENT')


@pytest.mark.parametrize('field,value,issue', [
    ('schema', 'invented_invalid_schema', 'PLAN_SCHEMA_OR_MODE_INVALID'),
    ('register_measurements', True, 'MEASUREMENT_SETTING_CHANGED'),
    ('source_use_review', h.REVIEW, 'SOURCE_REVIEW_FIELDS_MUST_REMAIN_UNRESOLVED'),
    ('reviewed_scope', h.SCOPE, 'SOURCE_REVIEW_FIELDS_MUST_REMAIN_UNRESOLVED')])
def test_safeguards_not_changed(sample, field, value, issue):
    p, _, _, plan, _ = sample
    plan[field] = value
    p.write_text(json.dumps(plan))
    before = p.read_bytes()
    with pytest.raises(h.Stop, match=issue):
        run(sample)
    assert p.read_bytes() == before


@pytest.mark.parametrize('field,value', [('verification_mode', 'verify_existing_local_pin'),
    ('expected_archive_sha256', 'b'*64), ('archive_edition', '45')])
def test_source_fields_not_normalized_or_approved(sample, field, value):
    p, _, _, plan, _ = sample
    plan['input_archives'][0][field] = value
    p.write_text(json.dumps(plan))
    before = p.read_bytes()
    with pytest.raises(h.Stop, match='SOURCE_SETTINGS_CHANGED'):
        run(sample)
    assert p.read_bytes() == before


def test_count_tool_missing(sample):
    (sample[2] / 'run_counts.py').unlink()
    expect_stop(sample, 'COUNT_TOOL_INSTALLATION_INCOMPLETE')


def test_count_tool_binding_mismatch_not_rewritten(sample, tmp_path):
    p, _, _, plan, _ = sample
    plan['count_tool_root'] = str(tmp_path / 'invented_other')
    p.write_text(json.dumps(plan))
    before = p.read_bytes()
    with pytest.raises(h.Stop, match='COUNT_TOOL_LOCATION_MISMATCH'):
        run(sample)
    assert p.read_bytes() == before


def test_atomic_replace_failure_preserves_original_and_backup(sample, monkeypatch):
    def fail(*_):
        raise OSError('INVENTED_SENSITIVE_PATH_MUST_NOT_BE_PRINTED')
    monkeypatch.setattr(h.os, 'replace', fail)
    with pytest.raises(OSError):
        run(sample)
    assert sample[0].read_bytes() == sample[4]
    backup = sample[0].with_name(sample[0].name + h.BACKUP_SUFFIX)
    assert backup.read_bytes() == sample[4]
    assert not list(sample[0].parent.glob('*.tmp'))
    assert not (sample[0].parent / h.LOCK_NAME).exists()


def test_authorization_appearing_during_update_blocks_commit(sample, monkeypatch):
    original = h.tempfile.mkstemp
    def concurrent(*a, **kw):
        result = original(*a, **kw)
        (sample[0].parent / 'registration.authorization.json').write_bytes(b'invented')
        return result
    monkeypatch.setattr(h.tempfile, 'mkstemp', concurrent)
    expect_stop(sample, 'AUTHORIZATION_ALREADY_PRESENT')


def test_unique_explicit_local_pattern_and_duplicate_suffix_ignored(sample):
    ignored = sample[1].with_name('5050stata_invented_V1(1).zip')
    ignored.write_bytes(b'invented')
    assert h.select_archive(str(sample[1].parent / '5050stata_*_V1.zip')) == sample[1]


def test_ambiguous_pattern_refused(sample):
    sample[1].with_name('5050stata_other_V1.zip').write_bytes(b'invented')
    with pytest.raises(h.Stop, match='ARCHIVE_PATTERN_MUST_MATCH_EXACTLY_ONE_FILE'):
        h.select_archive(str(sample[1].parent / '5050stata_*_V1.zip'))


def test_empty_pattern_refused(sample):
    sample[1].unlink()
    with pytest.raises(h.Stop, match='ARCHIVE_PATTERN_MUST_MATCH_EXACTLY_ONE_FILE'):
        h.select_archive(str(sample[1].parent / '5050stata_*_V1.zip'))


def test_readiness_after_patch_is_not_registration_authorization(sample):
    run(sample)
    before = {x.name: x.read_bytes() for x in sample[0].parent.iterdir()}
    assert c.readiness(sample[0], sample[2]) == [
        'REGISTRATION_PLAN: INCOMPLETE', 'ARCHIVE_PATH: CONFIGURED', 'ARCHIVE_FILE: PRESENT',
        'SOURCE_REVIEW: UNRESOLVED', 'AUTHORIZATION: NOT_RECORDED', 'CONSUMED_ATTEMPT: NO']
    assert before == {x.name: x.read_bytes() for x in sample[0].parent.iterdir()}


def test_readiness_established_review_can_be_ready(sample):
    run(sample)
    plan = json.loads(sample[0].read_text())
    # Invented independently established review, not generated by production helper.
    plan.update(source_use_review=h.REVIEW, reviewed_scope=h.SCOPE)
    sample[0].write_text(json.dumps(plan))
    result = c.readiness(sample[0], sample[2])
    assert result[0] == 'REGISTRATION_PLAN: READY'
    assert result[3] == 'SOURCE_REVIEW: ESTABLISHED'


def test_readiness_marks_presence_without_reading_receipts(sample):
    output = sample[0].parent / 'registration_output'
    output.mkdir()
    (output / 'operation_started.private.json').write_bytes(b'invented')
    (sample[0].parent / 'registration.authorization.json').write_bytes(b'invented')
    result = c.readiness(sample[0], sample[2])
    assert result[4:] == ['AUTHORIZATION: RECORDED', 'CONSUMED_ATTEMPT: YES']
    assert result[0] == 'REGISTRATION_PLAN: INCOMPLETE'


@pytest.mark.parametrize('script', ['prepare_plan.py', 'check_readiness.py'])
def test_agent_cli_refuses_before_access_and_no_path_leak(script, tmp_path):
    nonexistent = str(tmp_path / 'INVENTED_SECRET_SENTINEL')
    args = [sys.executable, '-B', str(ROOT / script), '--plan', nonexistent, '--count-tools', nonexistent]
    if script == 'prepare_plan.py':
        args += ['--archive', nonexistent]
    result = subprocess.run(args, env={**os.environ, 'CODEX_SESSION_ID': 'invented-agent'}, capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == 'STOP ISSUE=INDEPENDENT_LOCAL_OPERATOR_REQUIRED\n'
    assert result.stderr == ''


def test_bad_cli_does_not_echo_paths(tmp_path):
    sentinel = str(tmp_path / 'INVENTED_SECRET_SENTINEL')
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'prepare_plan.py'), '--bad', sentinel], capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == 'STOP ISSUE=INVALID_COMMAND_LINE\n' and not result.stderr


def test_cli_synthetic_dispatch_success(sample, monkeypatch, capsys):
    monkeypatch.setattr(h, 'require_operator', lambda: None)  # Invented fixture boundary only.
    monkeypatch.setattr(sys, 'argv', ['prepare_plan.py', '--plan', str(sample[0]),
        '--count-tools', str(sample[2]), '--archive-pattern', str(sample[1].parent / '5050stata_*_V1.zip')])
    assert h.main() == 0
    assert capsys.readouterr().out == 'PLAN_ARCHIVE_PATH_UPDATED\n'


def test_unexpected_failure_is_sanitized(sample, monkeypatch, capsys):
    monkeypatch.setattr(h, 'require_operator', lambda: None)
    monkeypatch.setattr(sys, 'argv', ['prepare_plan.py', '--plan', str(sample[0]), '--count-tools', str(sample[2]), '--archive', str(sample[1])])
    def fail(*_):
        raise OSError('INVENTED_PRIVATE_MESSAGE')
    monkeypatch.setattr(h, 'prepare', fail)
    assert h.main() == 2
    result = capsys.readouterr()
    assert result.out == 'STOP ISSUE=LOCAL_PLAN_UPDATE_NOT_COMPLETED\n' and not result.err


@pytest.mark.parametrize('bad', ['{"schema":1,"schema":2}', '{"bad":NaN}', '{not json'])
def test_invalid_or_duplicate_json_rejected_without_rewrite(sample, bad):
    p = sample[0]
    p.write_text(bad)
    before = p.read_bytes()
    with pytest.raises(h.Stop):
        run(sample)
    assert p.read_bytes() == before
    assert len(list(p.parent.iterdir())) == 1


def test_missing_plan_refused(sample):
    sample[0].unlink()
    with pytest.raises(h.Stop, match='REGISTRATION_PLAN_MISSING'):
        run(sample)
    assert not list(sample[0].parent.iterdir())


def test_plan_symlink_refused(sample):
    p = sample[0]
    target = p.with_name('invented_plan_target')
    p.rename(target)
    p.symlink_to(target)
    with pytest.raises(h.Stop, match='SYMLINK_REFUSED'):
        run(sample)
    assert target.read_bytes() == sample[4]


def test_nonprivate_run_parent_refused(sample):
    sample[0].parent.chmod(0o755)
    expect_stop(sample, 'PRIVATE_RUN_DIRECTORY_PERMISSIONS_REQUIRED')


def test_count_directory_missing(sample):
    for f in sample[2].iterdir():
        f.unlink()
    sample[2].rmdir()
    expect_stop(sample, 'COUNT_TOOL_INSTALLATION_MISSING')


def test_unknown_operation_artifact_makes_readiness_undetermined(sample):
    (sample[0].parent / 'invented_alternate_output').mkdir()
    with pytest.raises(h.Stop, match='UNRECOGNIZED_RUN_ARTIFACT_READINESS_UNDETERMINED'):
        c.readiness(sample[0], sample[2])


def test_missing_plan_readiness(sample):
    sample[0].unlink()
    assert c.readiness(sample[0], sample[2]) == [
        'REGISTRATION_PLAN: INCOMPLETE', 'ARCHIVE_PATH: MISSING', 'ARCHIVE_FILE: MISSING',
        'SOURCE_REVIEW: UNRESOLVED', 'AUTHORIZATION: NOT_RECORDED', 'CONSUMED_ATTEMPT: NO']


def test_existing_authorization_refuses_even_already_configured(sample):
    run(sample)
    before = sample[0].read_bytes()
    (sample[0].parent / 'registration.authorization.json').write_bytes(b'invented')
    with pytest.raises(h.Stop, match='AUTHORIZATION_ALREADY_PRESENT'):
        run(sample)
    assert sample[0].read_bytes() == before


def test_atomic_replace_really_uses_complete_private_temp_and_prior_backup(sample, monkeypatch):
    original = h.os.replace
    def checked(src, dst):
        p = sample[0]
        assert p.read_bytes() == sample[4]
        assert p.with_name(p.name + h.BACKUP_SUFFIX).read_bytes() == sample[4]
        assert stat.S_IMODE(Path(src).stat().st_mode) == 0o600
        assert json.loads(Path(src).read_bytes())['input_archives'][0]['archive_path'] == str(sample[1])
        return original(src, dst)
    monkeypatch.setattr(h.os, 'replace', checked)
    assert run(sample) == 'PLAN_ARCHIVE_PATH_UPDATED'
