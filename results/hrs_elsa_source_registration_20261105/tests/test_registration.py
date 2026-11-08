"""Invented temporary populations only. Never locate clinical input files."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import warnings
import zipfile

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import registration as r
from config_generation import generate_count_configuration
from local_execution import Rejected, exclusive_output, load_json, sha, write_json


def digest(b):
    return hashlib.sha256(b).hexdigest()


@pytest.fixture
def fixture(tmp_path):
    # These are valid invented Stata tables, not merely arbitrary header strings.
    stream = io.BytesIO()
    pd.DataFrame({'invented_record': [1, 2], 'invented_flag': [0, 1]}).to_stata(stream, write_index=False, version=118)
    data = stream.getvalue()
    contract = copy.deepcopy(r.verify_public())
    public = tmp_path / 'invented_public_count_installation'
    public.mkdir()
    template = load_json(ROOT / 'references/count_config.template.json')
    files = {'config.template.json': json.dumps(template).encode(), 'official_variable_map.json': b'{"invented":true}', 'PROTOCOL.json': b'{"invented_protocol":true}'}
    for name, contents in files.items():
        (public / name).write_bytes(contents)
    release = {'files': {k: digest(v) for k, v in files.items()}}
    (public / 'RELEASE_MANIFEST.json').write_text(json.dumps(release))
    contract.update(count_release_manifest_sha256=sha(public / 'RELEASE_MANIFEST.json'),
        count_config_template_sha256=sha(public / 'config.template.json'),
        count_mapping_sha256=sha(public / 'official_variable_map.json'),
        count_protocol_sha256=sha(public / 'PROTOCOL.json'))
    archive = tmp_path / '5050stata_invented.zip'
    items = [('invented/data/' + name, data) for name in contract['required_products'].values()]
    items.append(('unrelated/invented_secret.txt', b'UNRELATED_SYNTHETIC_NOT_TO_COPY'))
    def make(items_override=None):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED) as z:
                for name, content in (items if items_override is None else items_override):
                    z.writestr(name, content)
    make()
    plan = {'schema': 'elsa-source-registration-plan-v1', 'mode': 'independent_local_only',
        'source_use_review': r.REVIEW, 'reviewed_scope': r.SCOPE.copy(),
        'count_tool_root': str(public), 'register_measurements': False,
        'input_archives': [{'archive_id': 'invented', 'archive_path': str(archive),
           'verification_mode': 'first_local_registration', 'expected_archive_sha256': None,
           'study_id': 'UKDS_SN5050', 'archive_edition': 'UNRESOLVED'}]}
    parent = tmp_path / 'invented_private_parent'
    parent.mkdir(mode=0o700)
    output = parent / 'new_registration'
    return {'data': data, 'contract': contract, 'template': template, 'archive': archive,
            'items': items, 'make': make, 'plan': plan, 'output': output, 'public': public}


def execute(f):
    with exclusive_output(f['output']) as out:
        return r.register(f['plan'], out, contract=f['contract'], template=f['template'])


def fails(f, code):
    with pytest.raises(Rejected, match='^' + code + '$'):
        execute(f)
    receipt = load_json(f['output'] / 'completion.private.json')
    assert receipt == {'status': 'FAILED_NO_RETRY', 'issue': code, 'attempt_consumed': True}


def test_member_bytes_and_complete_configuration(fixture):
    f = fixture
    before = f['archive'].read_bytes()
    m = execute(f)
    assert len(m['members']) == 10
    assert f['archive'].read_bytes() == before
    assert m['archives'][0]['observed_archive_sha256'] == digest(before)
    for entry in m['members']:
        assert entry['uncompressed_member_sha256'] == digest(f['data'])
        assert entry['uncompressed_member_sha256'] != entry['archive_sha256']
        assert Path(entry['materialized_file']['path']).read_bytes() == f['data']
        assert entry['zip_member_name'].startswith('invented/data/')
    candidate = load_json(f['output'] / 'count_config.candidate.private.json')
    assert len(candidate['sources']) == 10
    assert candidate['source_use_review'] == 'UNRESOLVED_NOT_AUTHORIZED'
    assert candidate['measurement_sources'] is None
    assert candidate['feature_metadata'] is None
    assert candidate['no_models'] is True
    for key in set(candidate) - {'sources', 'measurement_sources'}:
        assert candidate[key] == f['template'][key]
    assert m['count_candidate_sha256'] == sha(f['output'] / 'count_config.candidate.private.json')
    assert m['clinical_rows_parsed'] is False and m['clinical_counts_executed'] is False
    assert m['historical_data_identity'] == 'NOT_ESTABLISHED'
    assert len(list((f['output'] / 'registered_inputs').rglob('*.dta'))) == 10
    assert not list(f['output'].rglob('invented_secret.txt'))


def test_private_permissions(fixture):
    f = fixture
    execute(f)
    for p in [f['output'], *f['output'].rglob('*')]:
        assert stat.S_IMODE(p.stat().st_mode) == (0o700 if p.is_dir() else 0o600)


def test_existing_local_archive_pin(fixture):
    f = fixture
    f['plan']['input_archives'][0].update(verification_mode='verify_existing_local_pin', expected_archive_sha256=sha(f['archive']))
    assert execute(f)['archives'][0]['verification_mode'] == 'verify_existing_local_pin'


def test_wrong_archive_hash(fixture):
    f = fixture
    f['plan']['input_archives'][0].update(verification_mode='verify_existing_local_pin', expected_archive_sha256='0'*64)
    fails(f, 'ARCHIVE_HASH_MISMATCH')
    assert not (f['output'] / 'registered_inputs').exists()


def test_historical_code_hash_is_not_archive_hash(fixture):
    f = fixture
    f['plan']['input_archives'][0].update(verification_mode='verify_existing_local_pin', expected_archive_sha256=next(iter(f['contract']['historical_code_fingerprints'].values())))
    fails(f, 'NON_ARCHIVE_HASH_USED_AS_ARCHIVE_PIN')


@pytest.mark.parametrize('edition', ['45', '50', 'H', 'July 2025', None])
def test_no_unsupported_edition_claim(fixture, edition):
    f = fixture
    f['plan']['input_archives'][0]['archive_edition'] = edition
    fails(f, 'UNSUPPORTED_ARCHIVE_EDITION_CLAIM')


@pytest.mark.parametrize('field,value,code', [
    ('source_use_review', 'UNRESOLVED_NOT_AUTHORIZED', 'REGISTRATION_SOURCE_USE_REVIEW_REQUIRED'),
    ('reviewed_scope', [], 'REGISTRATION_SOURCE_USE_REVIEW_REQUIRED'),
    ('mode', 'agent', 'REGISTRATION_PLAN_INVALID'),
    ('register_measurements', 'yes', 'MEASUREMENT_SELECTION_INVALID')])
def test_missing_review_scope_rejected_before_archive_read(fixture, monkeypatch, field, value, code):
    f = fixture
    f['plan'][field] = value
    original = Path.open
    def guarded(p, *args, **kwargs):
        assert p != f['archive'], 'Archive opened before permission validation'
        return original(p, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', guarded)
    fails(f, code)


def test_missing_member(fixture):
    f = fixture
    f['make'](f['items'][1:])
    fails(f, 'REQUIRED_STATA_MEMBER_MISSING')


def test_duplicate_full_member(fixture):
    f = fixture
    f['make'](f['items'] + [f['items'][0]])
    fails(f, 'DUPLICATE_ZIP_MEMBER')


def test_duplicate_basename(fixture):
    f = fixture
    f['make'](f['items'] + [('other/' + Path(f['items'][0][0]).name, f['data'])])
    fails(f, 'AMBIGUOUS_STATA_MEMBER')


def test_duplicate_across_archives(fixture):
    f = fixture
    other = f['archive'].with_name('5050stata_invented_other.zip')
    other.write_bytes(f['archive'].read_bytes())
    f['plan']['input_archives'].append({**f['plan']['input_archives'][0], 'archive_id': 'other', 'archive_path': str(other)})
    fails(f, 'AMBIGUOUS_STATA_MEMBER')


def test_non_zip_corruption(fixture):
    f = fixture
    f['archive'].write_bytes(b'INVENTED_CORRUPT_ARCHIVE')
    fails(f, 'ARCHIVE_CORRUPT_OR_UNREADABLE')


def test_member_crc_corruption(fixture):
    f = fixture
    raw = f['archive'].read_bytes()
    pos = raw.index(f['data']) + len(f['data']) - 2
    f['archive'].write_bytes(raw[:pos] + bytes([raw[pos] ^ 0xFF]) + raw[pos+1:])
    fails(f, 'MEMBER_CORRUPT_OR_UNREADABLE')


def test_not_stata(fixture):
    f = fixture
    f['make']([(name, b'INVENTED_NOT_STATA') if name.endswith('.dta') else (name, data) for name, data in f['items']])
    fails(f, 'SELECTED_MEMBER_NOT_RECOGNIZED_STATA_FORMAT')


@pytest.mark.parametrize('name', ['../outside', '/absolute', 'folder/../../outside', 'bad\\name'])
def test_unsafe_zip_paths(fixture, name):
    f = fixture
    f['make'](f['items'] + [(name, b'invented')])
    fails(f, 'UNSAFE_ZIP_MEMBER')


def test_zip_symlink(fixture):
    f = fixture
    with zipfile.ZipFile(f['archive'], 'a') as z:
        info = zipfile.ZipInfo('invented_symlink')
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        z.writestr(info, b'invented_target')
    fails(f, 'UNSAFE_ZIP_MEMBER')


def test_optional_nurse_products(fixture):
    f = fixture
    f['plan']['register_measurements'] = True
    f['make'](f['items'] + [('invented/' + name, f['data']) for name in f['contract']['optional_measurements'].values()])
    assert len(execute(f)['members']) == 12
    assert set(load_json(f['output'] / 'count_config.candidate.private.json')['measurement_sources']) == {'4', '6'}


def test_requested_measurements_do_not_silently_disappear(fixture):
    f = fixture
    f['plan']['register_measurements'] = True
    fails(f, 'REQUIRED_STATA_MEMBER_MISSING')


def test_modified_count_installation(fixture):
    f = fixture
    (f['public'] / 'PROTOCOL.json').write_text('invented tamper')
    fails(f, 'COUNT_PUBLIC_FILE_BINDING_MISMATCH')


def test_existing_destination_no_overwrite(fixture):
    f = fixture
    execute(f)
    snapshots = {p.relative_to(f['output']): p.read_bytes() for p in f['output'].rglob('*') if p.is_file()}
    with pytest.raises(Rejected, match='OUTPUT_ALREADY_EXISTS_NO_RETRY'):
        execute(f)
    assert snapshots == {p.relative_to(f['output']): p.read_bytes() for p in f['output'].rglob('*') if p.is_file()}


def test_failed_attempt_is_consumed(fixture):
    f = fixture
    f['make']([])
    fails(f, 'ARCHIVE_HAS_NO_EXPECTED_PRODUCTS')
    f['make']()
    with pytest.raises(Rejected, match='OUTPUT_ALREADY_EXISTS_NO_RETRY'):
        execute(f)


def test_interruption_recorded(fixture):
    f = fixture
    with pytest.raises(KeyboardInterrupt):
        with exclusive_output(f['output']):
            raise KeyboardInterrupt()
    assert load_json(f['output'] / 'completion.private.json')['status'] == 'INTERRUPTED_NO_RETRY'
    with pytest.raises(Rejected, match='OUTPUT_ALREADY_EXISTS_NO_RETRY'):
        execute(f)


def test_agent_cli_rejects_before_private_config_access(tmp_path):
    # Invented nonexistent config, sentinel path must never be printed.
    sentinel = str(tmp_path / 'INVENTED_PRIVATE_SENTINEL.json')
    env = {**os.environ, 'CODEX_SESSION_ID': 'synthetic-agent-fixture'}
    run = subprocess.run([sys.executable, '-B', str(ROOT / 'register_sources.py'), '--execute-local',
        '--config', sentinel, '--authorization', sentinel, '--output', sentinel], env=env,
        text=True, capture_output=True)
    assert run.returncode == 2
    assert run.stdout == 'REVIEW ISSUE=LOCAL_OPERATION_NOT_COMPLETED_INSPECT_PRIVATE_RECEIPT\n'
    assert not run.stderr and sentinel not in run.stdout
    assert not Path(sentinel).exists()


@pytest.mark.parametrize('field,value,code', [
    ('archive_path', 'relative.zip', 'EXPLICIT_ABSOLUTE_ARCHIVE_REQUIRED'),
    ('archive_edition', '50th', 'UNSUPPORTED_ARCHIVE_EDITION_CLAIM'),
    ('study_id', 'invented_other_study', 'UNEXPECTED_STUDY_IDENTITY'),
    ('verification_mode', 'pretend_authenticated', 'ARCHIVE_VERIFICATION_MODE_INVALID'),
    ('expected_archive_sha256', '1'*64, 'FIRST_REGISTRATION_CANNOT_CLAIM_PRIOR_PIN')])
def test_invalid_archive_descriptors(fixture, field, value, code):
    f = fixture
    f['plan']['input_archives'][0][field] = value
    fails(f, code)


def test_generated_configuration_refuses_tampered_materialized_file(fixture):
    f = fixture
    execute(f)
    candidate = load_json(f['output'] / 'count_config.candidate.private.json')
    Path(candidate['sources']['core1']['path']).write_bytes(b'invented tamper')
    with pytest.raises(Rejected, match='MATERIALIZED_MEMBER_HASH_MISMATCH'):
        generate_count_configuration(f['template'], candidate['sources'], None, f['output'] / 'another_candidate.json')
    assert not (f['output'] / 'another_candidate.json').exists()


def test_new_count_candidate_exclusive(fixture):
    f = fixture
    execute(f)
    config_path = f['output'] / 'count_config.candidate.private.json'
    before = config_path.read_bytes()
    c = load_json(config_path)
    with pytest.raises(FileExistsError):
        generate_count_configuration(f['template'], c['sources'], None, config_path)
    assert config_path.read_bytes() == before


def test_no_engine_or_dataset_loader_imports():
    import ast
    banned = {'pandas', 'pyreadstat', 'read_release', 'count_engine', 'run_counts'}
    for name in ['registration.py', 'register_sources.py', 'config_generation.py']:
        tree = ast.parse((ROOT / name).read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or '').split('.')[0])
        assert not (imported & banned)


def test_public_release_reference_integrity():
    contract = r.verify_public()
    release = load_json(ROOT / 'references/count_tool_release_manifest.json')
    assert release['files']['config.template.json'] == contract['count_config_template_sha256']
    assert release['files']['official_variable_map.json'] == contract['count_mapping_sha256']
    assert release['files']['PROTOCOL.json'] == contract['count_protocol_sha256']


def test_resource_limit_before_materialization(fixture, monkeypatch):
    f = fixture
    monkeypatch.setattr(r, 'MAX_TOTAL', 1)
    fails(f, 'ARCHIVE_RESOURCE_LIMIT')
    assert not (f['output'] / 'registered_inputs').exists()


def test_archive_mutation_detected(fixture, monkeypatch):
    f = fixture
    original = r._stream_hash
    calls = 0
    def changed(stream):
        nonlocal calls
        calls += 1
        result = original(stream)
        if calls == 1:
            # Invented ZIP only: a metadata mutation simulates concurrent input change.
            s = f['archive'].stat()
            os.utime(f['archive'], ns=(s.st_atime_ns, s.st_mtime_ns + 1000000000))
        return result
    monkeypatch.setattr(r, '_stream_hash', changed)
    fails(f, 'ARCHIVE_CHANGED_DURING_REGISTRATION')


def test_unpinned_unexpected_name(fixture):
    f = fixture
    other = f['archive'].with_name('unrelated_invented.zip')
    f['archive'].rename(other)
    f['plan']['input_archives'][0]['archive_path'] = str(other)
    fails(f, 'UNEXPECTED_UNPINNED_ARCHIVE_NAME')


def test_missing_expected_pin(fixture):
    f = fixture
    f['plan']['input_archives'][0]['verification_mode'] = 'verify_existing_local_pin'
    fails(f, 'REVIEWED_ARCHIVE_PIN_REQUIRED')


def test_missing_archive(fixture):
    f = fixture
    f['archive'].unlink()
    fails(f, 'ARCHIVE_FILE_MISSING_OR_UNSAFE')


def test_archive_symlink_rejected(fixture):
    f = fixture
    link = f['archive'].with_name('5050stata_invented_link.zip')
    link.symlink_to(f['archive'])
    f['plan']['input_archives'][0]['archive_path'] = str(link)
    fails(f, 'ARCHIVE_PATH_UNSAFE_OR_UNEXPECTED')


@pytest.mark.parametrize('mutation', ['purpose', 'config', 'code', 'destination'])
def test_authorization_cannot_be_reused_or_rebound(fixture, monkeypatch, capsys, mutation):
    import local_execution as le
    f = fixture
    cfg = f['output'].parent / 'invented_plan.json'
    cfg.write_text(json.dumps(f['plan']))
    auth = f['output'].parent / 'invented_auth.json'
    record = {'purpose': r.PURPOSE, 'authorized': True, 'scope_confirmed_by_operator': True,
              'operator': 'INVENTED_UNIT_TEST_OPERATOR', 'output_binding': str(f['output']),
              'config_sha256': sha(cfg), 'code_bindings': le.code_hashes()}
    if mutation == 'purpose':
        record['purpose'] = 'old_count_operation_not_registration'
    elif mutation == 'config':
        record['config_sha256'] = '0'*64
    elif mutation == 'code':
        record['code_bindings'] = {}
    else:
        record['output_binding'] = str(f['output'].parent / 'different_invented_destination')
    write_json(auth, record)
    # Mock environment boundary only for a completely invented unit-test contract.
    monkeypatch.setattr(le, 'require_local', lambda: None)
    monkeypatch.setattr(sys, 'argv', ['invented', '--execute-local', '--config', str(cfg),
        '--authorization', str(auth), '--output', str(f['output'])])
    def forbidden(*_):
        pytest.fail('Rejected authorization reached processing')
    assert le.cli(r.PURPOSE, forbidden, forbidden) == 2
    result = capsys.readouterr()
    assert result.out == 'REVIEW ISSUE=LOCAL_OPERATION_NOT_COMPLETED_INSPECT_PRIVATE_RECEIPT\n'
    assert not result.err and not f['output'].exists()


def test_permission_denied_private_parent(fixture):
    f = fixture
    os.chmod(f['output'].parent, 0o755)
    with pytest.raises(Rejected, match='PRIVATE_PARENT_PERMISSIONS_REQUIRED'):
        execute(f)
    assert not f['output'].exists()


def test_unexpected_exception_permanently_recorded(fixture):
    f = fixture
    with pytest.raises(RuntimeError):
        with exclusive_output(f['output']):
            raise RuntimeError('INVENTED_PRIVATE_EXCEPTION_NOT_FOR_PUBLIC_OUTPUT')
    receipt = load_json(f['output'] / 'completion.private.json')
    assert receipt['issue'] == 'UNEXPECTED_IMPLEMENTATION_EXCEPTION'
    assert receipt['status'] == 'FAILED_NO_RETRY'
    assert 'INVENTED_PRIVATE_EXCEPTION' not in json.dumps(receipt)


@pytest.mark.parametrize('version', [114, 118, 119])
def test_supported_stata_format_is_not_archive_edition(fixture, version):
    f = fixture
    stream = io.BytesIO()
    pd.DataFrame({'invented': [3, 4]}).to_stata(stream, write_index=False, version=version)
    f['make']([(n, stream.getvalue()) if n.endswith('.dta') else (n, b) for n, b in f['items']])
    manifest = execute(f)
    assert manifest['archive_edition'] == 'UNRESOLVED'
    assert all(e['materialized_file']['claimed_archive_edition'] == 'UNRESOLVED' for e in manifest['members'])


def test_distinct_members_bound_to_correct_roles(fixture):
    f = fixture
    items, expected = [], {}
    for index, (role, basename) in enumerate(f['contract']['required_products'].items()):
        stream = io.BytesIO()
        pd.DataFrame({'invented': [index]}).to_stata(stream, write_index=False, version=118)
        data = stream.getvalue()
        items.append(('invented/' + basename, data))
        expected[role] = digest(data)
    f['make'](items)
    result = execute(f)
    assert len(set(expected.values())) == 10
    assert {e['role']: e['uncompressed_member_sha256'] for e in result['members']} == expected


def test_two_explicit_nonoverlapping_archives(fixture):
    f = fixture
    f['make'](f['items'][:5])
    other = f['archive'].with_name('5050stata_invented_second.zip')
    with zipfile.ZipFile(other, 'w') as z:
        for name, content in f['items'][5:]:
            z.writestr(name, content)
    f['plan']['input_archives'].append({**f['plan']['input_archives'][0], 'archive_id': 'second', 'archive_path': str(other)})
    result = execute(f)
    assert len(result['archives']) == 2 and len(result['members']) == 10
    assert {e['archive_id'] for e in result['members']} == {'invented', 'second'}


def test_unrelated_archive_refused(fixture):
    f = fixture
    other = f['archive'].with_name('5050stata_invented_unrelated.zip')
    with zipfile.ZipFile(other, 'w') as z:
        z.writestr('invented_unrelated.txt', b'invented')
    f['plan']['input_archives'].append({**f['plan']['input_archives'][0], 'archive_id': 'unrelated', 'archive_path': str(other)})
    fails(f, 'ARCHIVE_HAS_NO_EXPECTED_PRODUCTS')
