"""Stream/hash selected ELSA ZIP members; never parse participant observations.

Independent human entry point is register_sources.py. Tests call this module with
invented ZIPs only. Public metadata describes expected products, not authenticated data.
"""
from contextlib import ExitStack
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import stat
import zipfile

from local_execution import need, sha, write_json, load_json, code_hashes
from config_generation import generate_count_configuration

ROOT = Path(__file__).resolve().parent
PURPOSE = 'elsa_source_registration_v1_20261105'
REVIEW = 'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_REGISTRATION_OPERATION'
SCOPE = ['READ_AND_HASH_ARCHIVE_BYTES', 'DECOMPRESS_AND_HASH_SELECTED_MEMBERS',
         'MATERIALIZE_SELECTED_RESTRICTED_FILES_IN_PRIVATE_STORAGE']
MAX_MEMBER = 16 * 1024**3
MAX_TOTAL = 64 * 1024**3
# Filled from public reference files, never from protected data.
PUBLIC_PINS = {'PUBLIC_SOURCE_CONTRACT.json': 'f92f18d41f4b57d74f11977f64cca0ca8882be4e49baf5d25502edf4b6870b26', 'REGISTRATION_PROTOCOL.json': '3d5b3554763ee6bf3f2c92a606c86d1539f16be1e0e527c0acde3b9f67e33e79', 'references/count_config.template.json': '897aaf342cca11521e82820e050f81669f03a358e0c526b317fa04962f0d3816', 'references/count_tool_release_manifest.json': 'e1026e76d8d96560eb6973cbf13a3d528ea30ed9356c60dd72febfc60faa4373'}


def public_file(root, name):
    rel = PurePosixPath(name)
    need(not rel.is_absolute() and '..' not in rel.parts and '\\' not in name, 'PUBLIC_PATH_INVALID')
    p = root / name
    need(not p.is_symlink() and p.resolve().is_relative_to(root.resolve()) and p.is_file(), 'PUBLIC_FILE_MISSING_OR_UNSAFE')
    return p


def verify_public():
    need(bool(PUBLIC_PINS), 'PUBLIC_REFERENCE_PINS_MISSING')
    for name, expected in PUBLIC_PINS.items():
        need(sha(public_file(ROOT, name)) == expected, 'PUBLIC_REFERENCE_BINDING_MISMATCH')
    return load_json(ROOT / 'PUBLIC_SOURCE_CONTRACT.json')


def verify_count_installation(root, contract):
    root = Path(root)
    need(root.is_absolute() and not root.is_symlink() and root.is_dir(), 'COUNT_PUBLIC_INSTALLATION_REQUIRED')
    release = public_file(root, 'RELEASE_MANIFEST.json')
    need(sha(release) == contract['count_release_manifest_sha256'], 'COUNT_RELEASE_BINDING_MISMATCH')
    manifest = load_json(release)
    for name, digest in manifest['files'].items():
        need(sha(public_file(root, name)) == digest, 'COUNT_PUBLIC_FILE_BINDING_MISMATCH')
    for name, key in [('config.template.json', 'count_config_template_sha256'),
                      ('official_variable_map.json', 'count_mapping_sha256'),
                      ('PROTOCOL.json', 'count_protocol_sha256')]:
        need(sha(public_file(root, name)) == contract[key], 'COUNT_CONTRACT_BINDING_MISMATCH')
    return sha(release)


def validate_plan(plan, contract):
    need(isinstance(plan, dict) and set(plan) == {'schema', 'mode', 'source_use_review',
         'reviewed_scope', 'count_tool_root', 'register_measurements', 'input_archives'}, 'REGISTRATION_PLAN_INVALID')
    need(plan['schema'] == 'elsa-source-registration-plan-v1' and plan['mode'] == 'independent_local_only', 'REGISTRATION_PLAN_INVALID')
    need(plan['source_use_review'] == REVIEW and plan['reviewed_scope'] == SCOPE, 'REGISTRATION_SOURCE_USE_REVIEW_REQUIRED')
    need(type(plan['register_measurements']) is bool, 'MEASUREMENT_SELECTION_INVALID')
    archives = plan['input_archives']
    need(isinstance(archives, list) and 1 <= len(archives) <= 12, 'EXPLICIT_ARCHIVES_REQUIRED')
    ids, paths = set(), set()
    for item in archives:
        need(isinstance(item, dict) and set(item) == {'archive_id', 'archive_path', 'verification_mode',
            'expected_archive_sha256', 'study_id', 'archive_edition'}, 'ARCHIVE_DESCRIPTOR_INVALID')
        ident = item['archive_id']
        need(isinstance(ident, str) and re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', ident) and ident not in ids, 'ARCHIVE_ID_INVALID_OR_DUPLICATE')
        ids.add(ident)
        need(item['study_id'] == 'UKDS_SN5050', 'UNEXPECTED_STUDY_IDENTITY')
        # Neither the historical reader nor documentation establishes acquired ZIP edition.
        need(item['archive_edition'] == 'UNRESOLVED', 'UNSUPPORTED_ARCHIVE_EDITION_CLAIM')
        raw = item['archive_path']
        need(isinstance(raw, str) and Path(raw).is_absolute() and 'SET_' not in raw, 'EXPLICIT_ABSOLUTE_ARCHIVE_REQUIRED')
        p = Path(raw)
        need(not p.is_symlink() and p.suffix == '.zip', 'ARCHIVE_PATH_UNSAFE_OR_UNEXPECTED')
        need(str(p.resolve()) not in paths, 'DUPLICATE_ARCHIVE_PATH')
        paths.add(str(p.resolve()))
        digest = item['expected_archive_sha256']
        if digest in contract['historical_code_fingerprints'].values():
            need(False, 'NON_ARCHIVE_HASH_USED_AS_ARCHIVE_PIN')
        mode = item['verification_mode']
        if mode == 'verify_existing_local_pin':
            need(isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'REVIEWED_ARCHIVE_PIN_REQUIRED')
        elif mode == 'first_local_registration':
            need(digest is None, 'FIRST_REGISTRATION_CANNOT_CLAIM_PRIOR_PIN')
            # Original selector only, never a claim of distributor authentication.
            need(p.name.startswith('5050stata_'), 'UNEXPECTED_UNPINNED_ARCHIVE_NAME')
        else:
            need(False, 'ARCHIVE_VERIFICATION_MODE_INVALID')
    return plan


def _stream_hash(stream):
    stream.seek(0)
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
    stream.seek(0)
    return h.hexdigest()


def _identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _safe_member(info):
    name = info.filename
    rel = PurePosixPath(name)
    need(name and '\\' not in name and '\x00' not in info.orig_filename and not rel.is_absolute()
         and '..' not in rel.parts and not stat.S_ISLNK(info.external_attr >> 16), 'UNSAFE_ZIP_MEMBER')
    return rel.name


def _stata_header(header):
    # File-format plausibility only: NOT product version, variables, rows or edition.
    xml = re.match(br'<stata_dta>\s*<header>\s*<release>(117|118|119)</release>', header)
    binary = len(header) >= 4 and header[0] in (104, 105, 108, 110, 111, 113, 114, 115) and header[1] in (1, 2) and header[2:4] == b'\x01\x00'
    need(bool(xml) or binary, 'SELECTED_MEMBER_NOT_RECOGNIZED_STATA_FORMAT')


def register(plan, output, *, contract=None, template=None):
    """Called AFTER independent authorization and consumed marker creation.

    Injected contract/template used only by synthetic unit fixtures; production CLI
    always supplies pinned public references through the defaults.
    """
    contract = verify_public() if contract is None else contract
    validate_plan(plan, contract)  # No ZIP bytes opened before scope validation.
    count_release = verify_count_installation(plan['count_tool_root'], contract)
    template = load_json(ROOT / 'references/count_config.template.json') if template is None else template
    output = Path(output)
    need(output.is_dir() and output.stat().st_mode & 0o077 == 0, 'PRIVATE_OUTPUT_PERMISSIONS_REQUIRED')
    needed = dict(contract['required_products'])
    if plan['register_measurements']:
        needed.update({'nurse' + w: b for w, b in contract['optional_measurements'].items()})
    selected = {name: [] for name in needed.values()}
    archive_records, opened, identities = [], [], []
    with ExitStack() as stack:
        for item in plan['input_archives']:
            p = Path(item['archive_path'])
            need(p.is_file() and not p.is_symlink(), 'ARCHIVE_FILE_MISSING_OR_UNSAFE')
            handle = stack.enter_context(p.open('rb'))
            identity = _identity(os.fstat(handle.fileno()))
            need(identity == _identity(p.stat()), 'ARCHIVE_CHANGED_DURING_REGISTRATION')
            digest = _stream_hash(handle)
            if item['verification_mode'] == 'verify_existing_local_pin':
                need(digest == item['expected_archive_sha256'], 'ARCHIVE_HASH_MISMATCH')
            try:
                z = stack.enter_context(zipfile.ZipFile(handle))
                members = z.infolist()
            except (zipfile.BadZipFile, OSError):
                need(False, 'ARCHIVE_CORRUPT_OR_UNREADABLE')
            need(len(members) <= 100000, 'ARCHIVE_RESOURCE_LIMIT')
            names = set()
            selected_in_archive = 0
            for info in members:
                basename = _safe_member(info)
                need(info.filename not in names, 'DUPLICATE_ZIP_MEMBER')
                names.add(info.filename)
                if basename in selected and not info.is_dir():
                    selected[basename].append((item['archive_id'], z, info, digest))
                    selected_in_archive += 1
            need(selected_in_archive > 0, 'ARCHIVE_HAS_NO_EXPECTED_PRODUCTS')
            archive_records.append({**item, 'observed_archive_sha256': digest,
                'fingerprint_domain': 'ZIP_CONTAINER_BYTES',
                'historical_archive_match': 'NOT_ESTABLISHED_NO_HISTORICAL_DATA_PIN',
                'distributor_authentication': 'NOT_ESTABLISHED'})
            opened.append((p, handle, digest))
            identities.append(identity)
        need(all(len(v) > 0 for v in selected.values()), 'REQUIRED_STATA_MEMBER_MISSING')
        need(all(len(v) == 1 for v in selected.values()), 'AMBIGUOUS_STATA_MEMBER')
        need(sum(v[0][2].file_size for v in selected.values()) <= MAX_TOTAL, 'ARCHIVE_RESOURCE_LIMIT')
        entries, descriptors = [], {}
        for role, basename in needed.items():
            archive_id, z, info, container_sha = selected[basename][0]
            need(not info.flag_bits & 1 and 0 < info.file_size <= MAX_MEMBER, 'ENCRYPTED_OR_OVERSIZE_MEMBER')
            folder = output / 'registered_inputs' / role
            folder.mkdir(parents=True, mode=0o700, exist_ok=False)
            os.chmod(folder.parent, 0o700)
            destination = folder / basename
            h, size, header = hashlib.sha256(), 0, b''
            try:
                with z.open(info) as source:
                    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(fd, 'wb') as target:
                        for block in iter(lambda: source.read(1024 * 1024), b''):
                            if not header:
                                header = block[:256]
                                _stata_header(header)
                            size += len(block)
                            need(size <= MAX_MEMBER and size <= info.file_size, 'ARCHIVE_RESOURCE_LIMIT')
                            h.update(block)
                            target.write(block)
                        target.flush()
                        os.fsync(target.fileno())
            except (zipfile.BadZipFile, EOFError, RuntimeError, NotImplementedError):
                need(False, 'MEMBER_CORRUPT_OR_UNREADABLE')
            need(size == info.file_size and sha(destination) == h.hexdigest(), 'MATERIALIZED_MEMBER_HASH_MISMATCH')
            d = {'path': str(destination.resolve()), 'sha256': h.hexdigest(),
                 'dataset_basename': basename, 'claimed_archive_edition': 'UNRESOLVED'}
            descriptors[role] = d
            entries.append({'role': role, 'archive_id': archive_id, 'archive_sha256': container_sha,
                'zip_member_name': info.filename, 'uncompressed_member_sha256': h.hexdigest(),
                'materialized_file': d, 'fingerprint_domain': 'UNCOMPRESSED_STATA_MEMBER_BYTES',
                'member_crc_verified': True, 'stata_check': 'FORMAT_HEADER_ONLY_NO_ROW_OR_VARIABLE_PARSING'})
        for (p, handle, digest), identity in zip(opened, identities):
            need(_identity(os.fstat(handle.fileno())) == identity and _identity(p.stat()) == identity
                 and _stream_hash(handle) == digest, 'ARCHIVE_CHANGED_DURING_REGISTRATION')
    sources = {r: descriptors[r] for r in contract['required_products']}
    measurements = ({w: descriptors['nurse' + w] for w in contract['optional_measurements']}
                    if plan['register_measurements'] else None)
    config_path = output / 'count_config.candidate.private.json'
    generate_count_configuration(template, sources, measurements, config_path)
    manifest = {'schema': 'elsa-private-source-registration-v1',
        'status': 'REGISTERED_LOCAL_MEMBER_BINDINGS_ONLY_COUNT_NOT_AUTHORIZED',
        'attempt_consumed': True, 'evidence_tier': contract['evidence_tier'],
        'source_use_review_scope': SCOPE, 'archives': archive_records, 'members': entries,
        'historical_data_identity': 'NOT_ESTABLISHED', 'archive_edition': 'UNRESOLVED',
        'count_tool_release_sha256': count_release,
        'count_protocol_sha256': contract['count_protocol_sha256'],
        'count_mapping_sha256': contract['count_mapping_sha256'],
        'public_contract_sha256': sha(ROOT / 'PUBLIC_SOURCE_CONTRACT.json'),
        'registration_protocol_sha256': sha(ROOT / 'REGISTRATION_PROTOCOL.json'),
        'registration_plan_values_sha256': hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'registration_code_bindings': code_hashes(),
        'count_candidate_sha256': sha(config_path),
        'measurement_files_registered': plan['register_measurements'],
        'clinical_rows_parsed': False, 'clinical_counts_executed': False,
        'registration_is_count_authorization': False}
    write_json(output / 'source_registration.private.json', manifest)
    return manifest
