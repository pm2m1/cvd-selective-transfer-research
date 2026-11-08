"""Independent-human, new-purpose, one-attempt status-only diagnostic."""
from pathlib import Path
import hashlib
import json
import re
import sys
from local_execution import (cli, require_local, need, descriptor, load_json, write_json,
                             sha, code_hashes, Rejected)
from diagnostic_engine import summarize
from status_reader import read_status

ROOT = Path(__file__).resolve().parent
PURPOSE = 'elsa_interview_participation_status_only_v1_20261106'
REVIEW = 'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_STATUS_ONLY_OPERATION'
SCOPE = ['READ_REGISTERED_SOURCE_AND_INTEGRITY_METADATA', 'HASH_REGISTERED_SOURCE_BYTES',
         'READ_LINKAGE_AND_INTERVIEW_STATUS_COLUMNS_ONLY', 'WRITE_PRIVATE_AGGREGATE_STATUS_DIAGNOSTICS']


def validate_config(config):
    expected_keys = {'schema', 'mode', 'source_use_review', 'reviewed_scope', 'no_models',
                     'no_event_counts', 'protocol_sha256', 'mapping_sha256', 'source_registration', 'sources'}
    need(isinstance(config, dict) and set(config) == expected_keys, 'STATUS_CONFIG_INVALID')
    need(config['schema'] == 'elsa-status-diagnostic-local-config-v1'
         and config['mode'] == 'independent_local_only', 'STATUS_CONFIG_INVALID')
    need(config['no_models'] is True and config['no_event_counts'] is True, 'STATUS_ONLY_CONTRACT_REQUIRED')
    need(config['source_use_review'] == REVIEW and config['reviewed_scope'] == SCOPE,
         'NEW_STATUS_ONLY_SCOPE_NOT_ESTABLISHED')
    need(config['protocol_sha256'] == sha(ROOT/'DIAGNOSTIC_PROTOCOL.json')
         and config['mapping_sha256'] == sha(ROOT/'references/frozen_mapping.json'), 'STATUS_PUBLIC_BINDING_MISMATCH')
    evidence = load_json(ROOT/'references/PUBLIC_EVIDENCE.json')
    need(set(config['sources']) == set(evidence['required_products']), 'EXACT_TEN_STATUS_SOURCES_REQUIRED')
    for role, d in [('registration', config['source_registration']), *config['sources'].items()]:
        keys = {'path', 'sha256'} if role == 'registration' else {'path', 'sha256', 'dataset_basename', 'claimed_archive_edition'}
        need(isinstance(d, dict) and set(d) == keys and isinstance(d['path'], str)
             and Path(d['path']).is_absolute() and isinstance(d['sha256'], str)
             and re.fullmatch('[0-9a-f]{64}', d['sha256']), 'STATUS_SOURCE_DESCRIPTOR_INVALID')
        if role != 'registration':
            need(d['dataset_basename'] == evidence['required_products'][role]
                 and d['claimed_archive_edition'] == 'UNRESOLVED', 'REGISTERED_PRODUCT_IDENTITY_MISMATCH')
    return evidence


def verify_registration(config, evidence):
    manifest = load_json(descriptor(config['source_registration']))
    need(manifest.get('schema') == 'elsa-private-source-registration-v1'
         and manifest.get('status') == 'REGISTERED_LOCAL_MEMBER_BINDINGS_ONLY_COUNT_NOT_AUTHORIZED'
         and manifest.get('attempt_consumed') is True, 'SOURCE_REGISTRATION_IDENTITY_INVALID')
    for name, expected in [('public_contract_sha256', evidence['registration_public_contract_sha256']),
        ('registration_protocol_sha256', evidence['registration_protocol_sha256']),
        ('registration_code_bindings', evidence['registration_code_bindings']),
        ('count_tool_release_sha256', evidence['count_tool_release_sha256']),
        ('count_mapping_sha256', evidence['frozen_mapping_sha256']),
        ('count_protocol_sha256', evidence['frozen_protocol_sha256'])]:
        need(manifest.get(name) == expected, 'SOURCE_REGISTRATION_PUBLIC_BINDING_MISMATCH')
    members = manifest.get('members')
    need(isinstance(members, list), 'REGISTRATION_MEMBERS_INVALID')
    registered = {}
    for entry in members:
        role = entry.get('role')
        need(role not in registered and role in set(evidence['required_products']) | {'nurse4', 'nurse6'},
             'REGISTRATION_MEMBER_AMBIGUOUS')
        registered[role] = entry
    for role, d in config['sources'].items():
        need(role in registered and registered[role].get('materialized_file') == d
             and registered[role].get('uncompressed_member_sha256') == d['sha256'],
             'SOURCE_NOT_EXACTLY_REGISTERED')
    return manifest


def execute(config, output):
    require_local()  # Guard direct calls before private metadata/file access.
    from verify_public import verify
    verify()
    evidence = validate_config(config)
    verify_registration(config, evidence)
    mapping = load_json(ROOT/'references/frozen_mapping.json')
    # Verify EVERY explicit input before any status column read.
    paths = {role: descriptor(d) for role, d in config['sources'].items()}
    tables, quality = {}, {}
    try:
        for role, path in paths.items():
            tables[role], quality[role] = read_status(path, role)
            write = {'schema': 'elsa-status-input-validation-v1', 'linkage_quality': quality,
                     'participant_rows_or_keys_written': False}
            # No progressively overwritten reports: final quality is written once below.
    except Rejected as exc:
        write_json(output/'input_validation.private.json', {'schema': 'elsa-status-input-validation-v1',
            'issue': exc.code, 'linkage_quality': quality, 'participant_rows_or_keys_written': False})
        raise
    write_json(output/'input_validation.private.json', write)
    need(not any(n for q in quality.values() for n in q.values()), 'INVALID_OR_DUPLICATE_STATUS_LINKAGE_NO_RETRY')
    need(bool(tables['harmonized']), 'EMPTY_HARMONIZED_STATUS_UNIVERSE')
    report = summarize(tables['harmonized'], {w: tables['core'+str(w)] for w in range(1, 10)}, mapping)
    # Reverify the same manifest/data bytes before publishing a private report.
    descriptor(config['source_registration'])
    for d in config['sources'].values():
        descriptor(d)
    report['bindings'] = {'source_registration_sha256': config['source_registration']['sha256'],
        'sources': {k: {'sha256': d['sha256'], 'dataset_basename': d['dataset_basename']} for k, d in config['sources'].items()},
        'protocol_sha256': config['protocol_sha256'], 'mapping_sha256': config['mapping_sha256'],
        'code_bindings': code_hashes()}
    write_json(output/'status_diagnostic.private.json', report)
    need(not report['source_domain_error_observed'], 'STATUS_DOMAIN_INCOMPATIBILITY_DIAGNOSTIC_PRESERVED')
    from importlib.metadata import version
    write_json(output/'diagnostic_integrity.private.json', {
        'schema': 'elsa-status-result-integrity-v1', 'purpose': PURPOSE,
        'outputs': {n: sha(output/n) for n in ('status_diagnostic.private.json', 'input_validation.private.json')},
        'python': sys.version, 'pandas': version('pandas'), 'numpy': version('numpy')})
    # Identical for all successful diagnostic findings; no data-conditioned verdict.
    write_json(output/'operational_summary.json', {
        'status': 'PRIVATE_STATUS_DIAGNOSTIC_WRITTEN_DISCLOSURE_REVIEW_REQUIRED',
        'scope': 'STATUS_ONLY', 'eligibility_changed': False, 'models_or_events_computed': False,
        'clinical_or_scientific_acceptance': 'NOT_GRANTED', 'attempt_consumed': True})


def safe_arguments(argv):
    """Sanitize malformed CLI before inherited argparse can echo private paths."""
    if argv == ['--help'] or argv == ['-h']:
        return True
    modes = {'--authorize-local', '--execute-local', '--synthetic-demo'}
    values = {'--config', '--authorization', '--output'}
    seen, count, index = set(), 0, 0
    while index < len(argv):
        token = argv[index]
        if token in seen:
            return False
        seen.add(token)
        if token in modes:
            count += 1
            index += 1
        elif token in values and index+1 < len(argv) and not argv[index+1].startswith('-'):
            index += 2
        else:
            return False
    return count == 1


def no_demo(_):
    raise Rejected('USE_INVENTED_FIXTURE_TEST_SUITE')


def main():
    if not safe_arguments(sys.argv[1:]):
        print('STOP ISSUE=INVALID_STATUS_DIAGNOSTIC_COMMAND')
        return 2
    # Preauthorization readiness reads only the NEW private config, not any sources.
    try:
        if '--authorize-local' in sys.argv:
            require_local()
            from verify_public import verify
            verify()
            import argparse
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument('--config', type=Path)
            args, _ = parser.parse_known_args()
            need(args.config is not None, 'NEW_STATUS_CONFIG_REQUIRED')
            validate_config(load_json(args.config))
    except BaseException:
        print('STOP ISSUE=STATUS_CONFIG_NOT_READY_NO_AUTHORIZATION_RECORDED')
        return 2
    return cli(PURPOSE, execute, no_demo)


if __name__ == '__main__':
    raise SystemExit(main())
