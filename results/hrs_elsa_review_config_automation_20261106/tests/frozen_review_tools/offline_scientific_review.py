"""Human-only review of EXISTING aggregate metadata. Standard library only.

No clinical source loader, network, disease counter, model or adoption interface.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import local_execution as runtime
from review_logic import worksheet, require

ROOT = Path(__file__).resolve().parent
PURPOSE = 'elsa_existing_status_scientific_review_v1_20261106'
REVIEW = 'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OFFLINE_REVIEW'
ISOLATION = 'INDEPENDENTLY_REVIEWED_OUTSIDE_AI_AND_INDEXERS'
HEX = re.compile('[0-9a-f]{64}')


def public_json(name):
    return json.loads((ROOT / name).read_text())


def no_links(path):
    p = Path(path)
    require(p.is_absolute() and '..' not in p.parts)
    require(not any(part.is_symlink() for part in (p, *p.parents)))
    return p


def private_directory(path):
    p = no_links(path)
    mode = p.stat()
    require(stat.S_ISDIR(mode.st_mode) and mode.st_uid == os.getuid() and mode.st_mode & 0o077 == 0)
    require(not p.is_relative_to(ROOT))
    return p


def private_file(path, private_root):
    p = no_links(path)
    require(p.is_relative_to(private_root) and not p.is_relative_to(ROOT))
    s = p.stat()
    require(stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid() and s.st_mode & 0o077 == 0)
    # Every directory inside the independently designated private root is private.
    for parent in p.parents:
        if parent == private_root: break
        require(parent.stat().st_mode & 0o077 == 0 and parent.stat().st_uid == os.getuid())
    return p


def strict_json(data):
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result); result[k] = v
        return result
    return json.loads(data, object_pairs_hook=pairs, parse_constant=lambda _: require(False))


def bound_json(d, private_root):
    require(isinstance(d, dict) and set(d) == {'path','sha256'} and isinstance(d['path'],str)
            and isinstance(d['sha256'],str) and HEX.fullmatch(d['sha256']))
    p = private_file(d['path'], private_root)
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        s = os.fstat(f.fileno())
        require(stat.S_ISREG(s.st_mode) and s.st_size <= 16*1024*1024)
        content = f.read(16*1024*1024+1)
    require(len(content) <= 16*1024*1024 and hashlib.sha256(content).hexdigest() == d['sha256'])
    return strict_json(content)


def validate_config(c):
    require(isinstance(c, dict) and set(c) == {'schema','mode','source_use_review','reviewed_scope','isolation_review',
        'private_root','public_contract_sha256','no_raw_data','no_event_counts','no_models','evidence'})
    require(c['schema'] == 'elsa-offline-scientific-review-config-v1' and c['mode'] == 'independent_local_only')
    require(c['source_use_review'] == REVIEW and c['isolation_review'] == ISOLATION)
    scope = public_json('references/REVIEW_SCOPE.json')
    require(c['reviewed_scope'] == scope['required_scope'])
    require(all(c[k] is True for k in ('no_raw_data','no_event_counts','no_models')))
    require(c['public_contract_sha256'] == runtime.sha(ROOT/'references/PUBLIC_CONTRACT.json'))
    root = private_directory(c['private_root'])
    require(set(c['evidence']) == set(scope['input_roles']))
    paths = set()
    for d in c['evidence'].values():
        require(isinstance(d,dict) and set(d) == {'path','sha256'} and isinstance(d['sha256'],str)
                and HEX.fullmatch(d['sha256']) and isinstance(d['path'],str))
        p = private_file(d['path'],root)
        require(p.suffix == '.json' and p not in paths); paths.add(p)
    require(all(Path(c['evidence'][k]['path']).parent != root for k in ('diagnostic_completion','failed_count_completion')))
    return root


def check_authorization(auth, config_descriptor, purpose, bindings):
    require(auth.get('purpose') == purpose and auth.get('authorized') is True
            and auth.get('scope_confirmed_by_operator') is True and bool(auth.get('operator')))
    require(auth.get('config_sha256') == config_descriptor['sha256'] and auth.get('code_bindings') == bindings)
    require(isinstance(auth.get('output_binding'),str))
    return no_links(auth['output_binding'])


def verify_existing_evidence(c, root, out):
    """Read ten explicit JSON records only. NEVER dereference source descriptors."""
    v = {k: bound_json(d, root) for k,d in c['evidence'].items()}
    contract = public_json('references/PUBLIC_CONTRACT.json'); evidence = contract['source_evidence']
    dc, fc = v['diagnostic_config'], v['failed_count_config']
    doutput = check_authorization(v['diagnostic_authorization'], c['evidence']['diagnostic_config'],
                                  contract['diagnostic_purpose'], contract['diagnostic_code_bindings'])
    foutput = check_authorization(v['failed_count_authorization'], c['evidence']['failed_count_config'],
                                  contract['count_purpose'], contract['count_code_bindings'])
    require(doutput.is_relative_to(root) and foutput.is_relative_to(root) and doutput != foutput)
    require(not any(out.is_relative_to(p) or p.is_relative_to(out) for p in (doutput,foutput)))
    names = {'diagnostic_completion':'completion.private.json','diagnostic_integrity':'diagnostic_integrity.private.json',
             'diagnostic_report':'status_diagnostic.private.json','diagnostic_input_validation':'input_validation.private.json'}
    for role, name in names.items(): require(Path(c['evidence'][role]['path']) == doutput/name)
    require(Path(c['evidence']['failed_count_completion']['path']) == foutput/'completion.private.json')
    require(v['diagnostic_completion'].get('status') == 'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED'
            and v['diagnostic_completion'].get('attempt_consumed') is True)
    require(v['failed_count_completion'].get('status') == 'FAILED_NO_RETRY'
            and v['failed_count_completion'].get('issue') == 'ELIGIBILITY_PROCESSING_PARTICIPATION_INTERVIEW_CONFLICT'
            and v['failed_count_completion'].get('attempt_consumed') is True)
    integrity = v['diagnostic_integrity']
    require(integrity.get('schema') == 'elsa-status-result-integrity-v1' and integrity.get('purpose') == contract['diagnostic_purpose'])
    require(integrity.get('outputs') == {names[k]: c['evidence'][k]['sha256'] for k in ('diagnostic_report','diagnostic_input_validation')})
    require(dc.get('schema') == 'elsa-status-diagnostic-local-config-v1' and dc.get('mode') == 'independent_local_only'
            and dc.get('no_models') is True and dc.get('no_event_counts') is True)
    require(dc.get('source_use_review') == 'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_STATUS_ONLY_OPERATION'
            and dc.get('reviewed_scope') == ['READ_REGISTERED_SOURCE_AND_INTEGRITY_METADATA','HASH_REGISTERED_SOURCE_BYTES',
                'READ_LINKAGE_AND_INTERVIEW_STATUS_COLUMNS_ONLY','WRITE_PRIVATE_AGGREGATE_STATUS_DIAGNOSTICS'])
    require(dc.get('protocol_sha256') == contract['diagnostic_protocol_sha256']
            and dc.get('mapping_sha256') == evidence['frozen_mapping_sha256'])
    require(fc.get('schema') == 'elsa-final-count-local-config-v1' and fc.get('mode') == 'independent_local_only'
            and fc.get('no_models') is True and fc.get('source_format') == 'registered_stata_tables_v1')
    require(fc.get('source_use_review') == 'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_OPERATION')
    require(fc.get('mapping_sha256') == evidence['frozen_mapping_sha256'] and fc.get('protocol_sha256') == evidence['frozen_protocol_sha256'])
    required = evidence['required_products']
    require(set(dc.get('sources',{})) == set(fc.get('sources',{})) == set(required))
    for role, basename in required.items():
        a, b = dc['sources'][role], fc['sources'][role]
        require(set(a) == set(b) == {'path','sha256','dataset_basename','claimed_archive_edition'})
        require(a['dataset_basename'] == b['dataset_basename'] == basename
                and isinstance(a['sha256'],str) and HEX.fullmatch(a['sha256']) and a['sha256'] == b['sha256']
                and a['claimed_archive_edition'] == b['claimed_archive_edition'] == 'UNRESOLVED')
        # Paths can differ after a permitted relocation; content identities must not.
        # No stat/hash/open call is made on either clinical path.
        require(isinstance(a['path'],str) and Path(a['path']).is_absolute()
                and isinstance(b['path'],str) and Path(b['path']).is_absolute())
    report = v['diagnostic_report']
    require(report.get('bindings') == {'source_registration_sha256': c['evidence']['source_registration']['sha256'],
        'sources': {k: {'sha256':d['sha256'],'dataset_basename':d['dataset_basename']} for k,d in dc['sources'].items()},
        'protocol_sha256':dc['protocol_sha256'],'mapping_sha256':dc['mapping_sha256'],
        'code_bindings':contract['diagnostic_code_bindings']})
    require(dc.get('source_registration') == c['evidence']['source_registration'])
    registration = v['source_registration']
    require(registration.get('schema') == 'elsa-private-source-registration-v1'
            and registration.get('status') == 'REGISTERED_LOCAL_MEMBER_BINDINGS_ONLY_COUNT_NOT_AUTHORIZED'
            and registration.get('attempt_consumed') is True)
    for name, expected in [('public_contract_sha256',evidence['registration_public_contract_sha256']),
        ('registration_protocol_sha256',evidence['registration_protocol_sha256']),('registration_code_bindings',evidence['registration_code_bindings']),
        ('count_tool_release_sha256',evidence['count_tool_release_sha256']),('count_mapping_sha256',evidence['frozen_mapping_sha256']),
        ('count_protocol_sha256',evidence['frozen_protocol_sha256'])]: require(registration.get(name) == expected)
    members = registration.get('members'); require(isinstance(members,list)); registered = {}
    for entry in members:
        require(isinstance(entry,dict) and entry.get('role') in set(required)|{'nurse4','nurse6'} and entry['role'] not in registered)
        registered[entry['role']] = entry
    for role,d in dc['sources'].items():
        require(role in registered and registered[role].get('materialized_file') == d
                and registered[role].get('uncompressed_member_sha256') == d['sha256'])
    quality = v['diagnostic_input_validation']
    require(set(quality) == {'schema','linkage_quality','participant_rows_or_keys_written'}
            and quality['schema'] == 'elsa-status-input-validation-v1' and quality['participant_rows_or_keys_written'] is False)
    require(set(quality['linkage_quality']) == set(required))
    for q in quality['linkage_quality'].values():
        require(set(q) == {'MISSING_LINKAGE','INVALID_LINKAGE_STORAGE','INVALID_LINKAGE_VALUE','DUPLICATE_LINKAGE'})
        require(all(type(n) is int and n == 0 for n in q.values()))
    return report, {'reviewed_metadata': c['evidence'], 'history_sources': report['bindings']['sources'],
        'frozen_public_release_fingerprints': {k:contract[k] for k in ('diagnostic_release_manifest_sha256','count_release_manifest_sha256')},
        'scope_of_source_equivalence':'TEN_HISTORY_CONTENT_DESCRIPTORS_ONLY_NOT_RAW_BYTES_OR_NURSE_FEATURES',
        'claimed_archive_edition':'UNRESOLVED','distributor_authentication':'UNRESOLVED'}


def execute(c, output):
    runtime.require_local()
    from verify_public import verify
    verify(ROOT)
    root = validate_config(c); out = private_directory(output)
    require(out.is_relative_to(root) and out != root)
    require(runtime.load_json(out/'operation_started.private.json').get('status') == 'STARTED_CONSUMED')
    report, provenance = verify_existing_evidence(c, root, out)
    result, decision = worksheet(report, public_json('SCIENTIFIC_DECISION_TEMPLATE.json'), provenance)
    # Recheck the same explicit metadata snapshots before creating review artifacts.
    for d in c['evidence'].values(): bound_json(d,root)
    runtime.write_json(out/'scientific_evidence_worksheet.private.json',result)
    runtime.write_json(out/'reviewer_decision.UNRESOLVED.private.json',decision)
    runtime.write_json(out/'review_integrity.private.json',{'schema':'elsa-offline-review-integrity-v1',
        'purpose':PURPOSE,'outputs':{n:runtime.sha(out/n) for n in
            ('scientific_evidence_worksheet.private.json','reviewer_decision.UNRESOLVED.private.json')},
        'public_contract_sha256':c['public_contract_sha256'],'code_bindings':runtime.code_hashes(),
        'reviewer_decision_is_unsigned_unadopted_template':True})
    runtime.write_json(out/'operational_summary.json',{'status':'PRIVATE_REVIEW_ARTIFACT_CREATED',
        'scientific_status':'INDEPENDENT_SCIENTIFIC_DECISION_REQUIRED','count_execution':'NO_EXECUTION',
        'eligibility_changed':False,'models_or_events_computed':False})


class SafeParser(argparse.ArgumentParser):
    def error(self, message): raise ValueError('NO_EXECUTION')


def main():
    try:
        p = SafeParser(description=__doc__)
        mode = p.add_mutually_exclusive_group(required=True)
        for name in ('review','preflight','authorize-local','execute-local'): mode.add_argument('--'+name,action='store_true')
        p.add_argument('--config',type=Path,required=True);p.add_argument('--authorization',type=Path);p.add_argument('--output',type=Path)
        args = p.parse_args()
        runtime.require_local() # BEFORE even the new private review configuration.
        from verify_public import verify
        verify(ROOT)
        # Initial config is metadata; never open protected results before authorization.
        no_links(args.config)
        s = args.config.stat()
        require(args.config.suffix == '.json' and stat.S_ISREG(s.st_mode) and s.st_uid == os.getuid()
                and s.st_mode & 0o077 == 0 and s.st_size <= 16*1024*1024)
        c = strict_json(args.config.read_bytes()); root = validate_config(c)
        private_file(args.config,root)
        require(args.config not in {Path(d['path']) for d in c['evidence'].values()})
        if args.preflight:
            print('NO_EXECUTION'); return 0
        require(args.authorization is not None and args.output is not None)
        auth = no_links(args.authorization); out = no_links(args.output)
        require(auth.is_relative_to(root) and out.is_relative_to(root) and auth.parent != out)
        private_directory(auth.parent); private_directory(out.parent)
        require(auth != args.config and not out.exists())
        protected = {Path(d['path']) for d in c['evidence'].values()}
        require(auth not in protected and not args.config.is_relative_to(out)
                and not any(p.is_relative_to(out) or (p.parent != root and out.is_relative_to(p.parent)) for p in protected))
        if args.execute_local: private_file(auth,root)
        else: require(not auth.exists())
        def call(mode):
            sys.argv = [str(ROOT/'offline_scientific_review.py'),mode,'--config',str(args.config),
                        '--authorization',str(auth),'--output',str(out)]
            return runtime.cli(PURPOSE,execute,lambda _:require(False))
        if args.review or args.authorize_local:
            rc = call('--authorize-local')
            if rc or args.authorize_local: return rc
        rc = call('--execute-local')
        if rc == 0:
            print('PRIVATE_REVIEW_ARTIFACT_CREATED')
            print('INDEPENDENT_SCIENTIFIC_DECISION_REQUIRED')
        return rc
    except SystemExit as exc: return exc.code
    except BaseException:
        print('NO_EXECUTION'); return 2


if __name__ == '__main__': raise SystemExit(main())
