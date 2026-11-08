"""Public frozen functions, public dictionaries and INVENTED records only.

Run in the source checkout with the named original public packages present.
No private configuration/data loader or authorization operation is invoked.
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import pytest

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
COUNT = REPO / 'results/hrs_elsa_final_count_feasibility_20261105'
FAST = REPO / 'results/hrs_elsa_training_fasttrack_20261106'
sys.path.insert(0, str(COUNT))
import count_engine as engine
import synthetic_fixture as invented

MAPPING = json.loads((COUNT / 'official_variable_map.json').read_text())


@pytest.mark.parametrize('wave', [4, 6, 7, 9])
@pytest.mark.parametrize('participation', [0, None, '.a'])
def test_zero_and_unknown_still_blocked(wave, participation):
    person = invented.person(MAPPING)
    person['participation'][str(wave)] = participation
    with pytest.raises(engine.CountError, match='PARTICIPATION_INTERVIEW_CONFLICT'):
        engine.validate_people([person], MAPPING)


@pytest.mark.parametrize('outcome', [None, -1, 31, 95])
def test_proxy_fallback_is_exposed_not_repaired(outcome):
    person = invented.person(MAPPING)
    visit = next(v for v in person['visits'] if v['wave'] == 6)
    visit['raw'].update(w6indout=outcome, askpx=1)
    person['participation']['6'] = 0
    assert engine.interview(visit, MAPPING) == 'proxy'
    with pytest.raises(engine.CountError, match='PARTICIPATION_INTERVIEW_CONFLICT'):
        engine.validate_people([person], MAPPING)


@pytest.mark.parametrize('wave', [4, 6, 7, 9])
def test_consistent_personal_state_unchanged(wave):
    person = invented.person(MAPPING)
    visit = next(v for v in person['visits'] if v['wave'] == wave)
    assert engine.interview(visit, MAPPING) == 'personal'
    engine.validate_people([person], MAPPING)


def test_wave_specific_domains_and_missing_w9_field():
    assert 'hedacmi' not in MAPPING['waves']['9']['fields']
    assert '26' in MAPPING['waves']['3']['fields']['w3indout']['values']
    assert '26' not in MAPPING['waves']['4']['fields']['w4indout']['values']
    assert MAPPING['waves']['1']['fields']['askpx1']['values']['2'].lower() == 'no'


def test_public_evidence_subset_exactly_preserves_dictionary():
    evidence = json.loads((HERE / 'ELSA_DICTIONARY_EVIDENCE.json').read_text())
    assert evidence['wave9_MI_confirmation_field_present'] is False
    assert evidence['source_mapping_sha256'] == hashlib.sha256((COUNT / 'official_variable_map.json').read_bytes()).hexdigest()
    for wave, item in evidence['waves'].items():
        for name, section in item['fields'].items():
            assert section == MAPPING['waves'][wave]['fields'][name]


def test_citations_and_conditional_mapping_not_strict_endpoint():
    with (HERE / 'OFFICIAL_VARIABLE_MAPPING.csv').open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 23
    assert all(row['official_citations'].startswith('https://') for row in rows)
    assert next(r for r in rows if r['topic'] == 'incident_MI')['readiness'] == 'SENSITIVITY_ONLY_HRS'
    assert next(r for r in rows if r['topic'] == 'Wave9_MI_confirmation')['readiness'] == 'DOCUMENTED_ABSENCE'


def test_original_readiness_not_approved():
    template = json.loads((FAST / 'configs/readiness.UNADOPTED.template.json').read_text())
    flags = [v for v in template.values() if type(v) is bool]
    assert len(flags) == 8 and not any(flags)
    assert template['approved_manifest_sha256'] is None


def test_no_historical_public_bytes_modified():
    pins = json.loads((HERE / 'PRESERVATION_BINDINGS.json').read_text())['files']
    for name, expected in pins.items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == expected


def test_no_active_corrected_counter_or_real_controller_added():
    assert not (HERE / 'count_engine.py').exists()
    assert not (HERE / 'run_counts.py').exists()
    assert 'NO EXECUTION' in (HERE / 'COUNT_RELEASE_DECISION.md').read_text()


def test_public_verifier_rejects_tampering_and_escape(tmp_path):
    spec = importlib.util.spec_from_file_location('public_package_verify', HERE / 'verify_public_package.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    file = tmp_path / 'INVENTED_PUBLIC.txt'; file.write_text('invented')
    manifest = {'scope': 'PUBLIC_DOCUMENTATION_TESTS_AND_INVENTED_AGGREGATES_ONLY',
                'files': {file.name: hashlib.sha256(file.read_bytes()).hexdigest()}}
    mf = tmp_path / 'RELEASE_MANIFEST.json'; mf.write_text(json.dumps(manifest))
    assert mod.verify(tmp_path) == 1
    unrelated = tmp_path / 'INVENTED_UNRELATED.txt'; unrelated.write_text('not registered')
    with pytest.raises(ValueError, match='UNREGISTERED_PUBLIC_PACKAGE_FILE'): mod.verify(tmp_path)
    unrelated.unlink()
    file.write_text('changed')
    with pytest.raises(ValueError, match='PUBLIC_CHECKSUM_MISMATCH'): mod.verify(tmp_path)
    manifest['files'] = {'../INVENTED_OTHER.txt': '0' * 64}; mf.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='PUBLIC_LAYOUT_INVALID'): mod.verify(tmp_path)
