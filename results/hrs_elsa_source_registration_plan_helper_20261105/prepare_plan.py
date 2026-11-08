#!/usr/bin/env python3
"""Local plan-only edit. Never opens archive bytes or authorizes registration."""
import argparse
import copy
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

SCHEMA = 'elsa-source-registration-plan-v1'
PLACEHOLDER = 'SET_ABSOLUTE_ARCHIVE_PATH_LOCALLY'
REVIEW = 'INDEPENDENTLY_ESTABLISHED_FOR_THIS_NEW_REGISTRATION_OPERATION'
SCOPE = ['READ_AND_HASH_ARCHIVE_BYTES', 'DECOMPRESS_AND_HASH_SELECTED_MEMBERS',
         'MATERIALIZE_SELECTED_RESTRICTED_FILES_IN_PRIVATE_STORAGE']
BACKUP_SUFFIX = '.before_archive_path.backup'
LOCK_NAME = '.prepare_plan.lock'


class Stop(Exception):
    pass


def need(condition, code):
    if not condition:
        raise Stop(code)


def require_operator():
    blocked = ('CODEX_HOME', 'CODEX_SESSION_ID', 'CODEX_THREAD_ID', 'CODEX_CI',
               'CI', 'GITHUB_ACTIONS', 'CHATGPT_SESSION_ID')
    need(not any(os.environ.get(k) for k in blocked) and sys.stdin.isatty(),
         'INDEPENDENT_LOCAL_OPERATOR_REQUIRED')


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop('INVALID_COMMAND_LINE')


def location(value):
    p = Path(value)
    need(p.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    # Metadata checks only, including dangling links and linked parent directories.
    need(not any(q.is_symlink() for q in (p, *p.parents)), 'SYMLINK_REFUSED')
    return p


def existing_file(value, issue):
    p = location(value)
    need(p.is_file() and stat.S_ISREG(p.stat().st_mode), issue)
    return p.resolve()


def archive_location(value):
    p = existing_file(value, 'ARCHIVE_FILE_MISSING_OR_NOT_REGULAR')
    need(p.name.startswith('5050stata_') and p.name.endswith('_V1.zip'),
         'ARCHIVE_BASENAME_NOT_EXPECTED_V1')
    return p


def select_archive(pattern):
    """Operator-supplied, one-directory metadata glob; no recursive discovery."""
    raw = Path(pattern)
    need(raw.is_absolute() and raw.name == '5050stata_*_V1.zip'
         and not any(c in str(raw.parent) for c in '*?[]'), 'ARCHIVE_PATTERN_INVALID')
    parent = location(raw.parent)
    need(parent.is_dir(), 'ARCHIVE_DIRECTORY_MISSING')
    matches = list(parent.glob(raw.name))
    need(len(matches) == 1, 'ARCHIVE_PATTERN_MUST_MATCH_EXACTLY_ONE_FILE')
    return archive_location(matches[0])


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _invalid_constant(_):
    raise Stop('INVALID_PLAN_JSON')


def load_plan(p):
    original = p.read_bytes()  # Plan only; never archive/receipt/dataset contents.
    try:
        value = json.loads(original, object_pairs_hook=_pairs, parse_constant=_invalid_constant)
    except (ValueError, UnicodeError):
        raise Stop('INVALID_PLAN_JSON') from None
    need(isinstance(value, dict), 'INVALID_PLAN_JSON')
    return original, value


def validate_structure(plan, count_tools):
    need(plan.get('schema') == SCHEMA and plan.get('mode') == 'independent_local_only',
         'PLAN_SCHEMA_OR_MODE_INVALID')
    need(plan.get('register_measurements') is False, 'MEASUREMENT_SETTING_CHANGED')
    archives = plan.get('input_archives')
    need(isinstance(archives, list) and len(archives) == 1 and isinstance(archives[0], dict),
         'EXACTLY_ONE_ARCHIVE_REQUIRED')
    item = archives[0]
    need(item.get('verification_mode') == 'first_local_registration'
         and 'expected_archive_sha256' in item and item['expected_archive_sha256'] is None
         and item.get('archive_edition') == 'UNRESOLVED'
         and item.get('study_id') == 'UKDS_SN5050', 'SOURCE_SETTINGS_CHANGED')
    need(isinstance(item.get('archive_path'), str), 'ARCHIVE_PATH_FIELD_INVALID')
    count = location(count_tools)
    need(count.is_dir(), 'COUNT_TOOL_INSTALLATION_MISSING')
    # Presence only, not a replacement for the registrar's complete hash verification.
    for name in ('run_counts.py', 'read_release.py', 'RELEASE_MANIFEST.json'):
        existing_file(count / name, 'COUNT_TOOL_INSTALLATION_INCOMPLETE')
    declared = plan.get('count_tool_root')
    need(isinstance(declared, str) and location(declared).resolve() == count.resolve(),
         'COUNT_TOOL_LOCATION_MISMATCH')


def source_review(plan):
    return plan.get('source_use_review') == REVIEW and plan.get('reviewed_scope') == SCOPE


def evidence_state(plan_path, authorization=None, output=None):
    """Inspect names/types only. Never reads any authorization or receipt contents.

    Only the explicit run directory and explicit/default operation destinations are
    in scope. Unknown siblings block editing; no unrelated directory search occurs.
    """
    parent = plan_path.parent
    auth = Path(authorization) if authorization is not None else parent / 'registration.authorization.json'
    out = Path(output) if output is not None else parent / 'registration_output'
    for p in (auth, out):
        need(p.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    present = lambda p: os.path.lexists(p)
    auth_present, out_present, consumed, unknown = present(auth), present(out), False, False
    markers = ('operation_started.private.json', 'completion.private.json')
    # Do not follow an output symlink even for marker inspection.
    if out_present and not out.is_symlink() and out.is_dir():
        consumed = any(present(out / name) for name in markers)
    allowed = {plan_path.name, plan_path.name + BACKUP_SUFFIX, LOCK_NAME}
    for entry in parent.iterdir():
        name = entry.name
        lower = name.lower()
        if name in markers:
            consumed = True
        if 'authorization' in lower or lower in ('auth.json', 'auth.private.json'):
            auth_present = True
        if entry == out:
            out_present = True
        elif name not in allowed and entry != auth and name not in markers:
            unknown = True
    return {'authorization': auth_present, 'output': out_present, 'consumed': consumed, 'unknown': unknown}


def refuse_operation_evidence(state):
    need(not state['consumed'], 'CONSUMED_OPERATION_PRESENT')
    need(not state['authorization'], 'AUTHORIZATION_ALREADY_PRESENT')
    need(not state['output'], 'EXECUTION_OUTPUT_ALREADY_PRESENT')
    need(not state['unknown'], 'RUN_DIRECTORY_NOT_PRISTINE')


def _identity(p):
    s = p.lstat()
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def prepare(plan_value, archive_value, count_tools, authorization=None, output=None):
    p = existing_file(plan_value, 'REGISTRATION_PLAN_MISSING')
    need(p.parent.stat().st_mode & 0o077 == 0, 'PRIVATE_RUN_DIRECTORY_PERMISSIONS_REQUIRED')
    archive = archive_location(archive_value)  # Metadata only.
    refuse_operation_evidence(evidence_state(p, authorization, output))
    need(not os.path.lexists(p.parent / LOCK_NAME), 'HELPER_LOCK_ALREADY_PRESENT')
    original, plan = load_plan(p)
    validate_structure(plan, count_tools)
    need(plan.get('source_use_review') == 'UNRESOLVED_NOT_AUTHORIZED'
         and plan.get('reviewed_scope') == [], 'SOURCE_REVIEW_FIELDS_MUST_REMAIN_UNRESOLVED')
    current = plan['input_archives'][0]['archive_path']
    if current != PLACEHOLDER:
        need(Path(current).is_absolute() and location(current).resolve() == archive,
             'DIFFERENT_EXISTING_ARCHIVE_PATH')
        return 'PLAN_ALREADY_CONFIGURED'
    backup = p.with_name(p.name + BACKUP_SUFFIX)
    need(not os.path.lexists(backup), 'PLAN_BACKUP_ALREADY_EXISTS')
    lock = p.parent / LOCK_NAME
    lock_fd = None
    temporary = None
    committed = False
    try:
        try:
            lock_fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise Stop('HELPER_LOCK_ALREADY_PRESENT') from None
        snapshot = _identity(p)
        need(p.read_bytes() == original, 'PLAN_CHANGED_CONCURRENTLY')
        # Exclusive, byte-exact, private backup is durable before editing anything.
        backup_fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(backup_fd, 'wb') as f:
            f.write(original)
            f.flush()
            os.fsync(f.fileno())
        # Persist the backup directory entry before replacing the original plan.
        directory_fd = os.open(p.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        candidate = copy.deepcopy(plan)
        candidate['input_archives'][0]['archive_path'] = str(archive)
        check = copy.deepcopy(candidate)
        check['input_archives'][0]['archive_path'] = current
        need(check == plan, 'UNEXPECTED_CONFIGURATION_CHANGE')
        encoded = (json.dumps(candidate, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
        fd, temporary = tempfile.mkstemp(prefix='.prepare_plan.', suffix='.tmp', dir=p.parent)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        refuse_operation_evidence(evidence_state(p, authorization, output) | {'unknown': _other_unknown(p, temporary, authorization, output)})
        need(not p.is_symlink() and _identity(p) == snapshot and p.read_bytes() == original,
             'PLAN_CHANGED_CONCURRENTLY')
        archive_location(archive)  # Recheck metadata; never read archive contents.
        os.replace(temporary, p)
        committed = True
        temporary = None
        directory_fd = os.open(p.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return 'PLAN_ARCHIVE_PATH_UPDATED'
    except BaseException:
        if committed:
            raise Stop('UPDATE_COMPLETION_UNCERTAIN_INSPECT_LOCALLY') from None
        raise
    finally:
        if temporary is not None:
            os.unlink(temporary)
        if lock_fd is not None:
            os.close(lock_fd)
            os.unlink(lock)  # Only this helper's own newly created lock.


def _other_unknown(p, temporary, authorization, output):
    # The helper's own new temp file is the sole additional allowed sibling.
    allowed = {p.name, p.name + BACKUP_SUFFIX, LOCK_NAME, Path(temporary).name}
    auth = Path(authorization) if authorization is not None else p.parent / 'registration.authorization.json'
    out = Path(output) if output is not None else p.parent / 'registration_output'
    return any(e.name not in allowed and e not in (auth, out)
               and e.name not in ('operation_started.private.json', 'completion.private.json')
               for e in p.parent.iterdir())


def arguments(description, archive=False):
    parser = SafeParser(description=description)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--count-tools', required=True)
    parser.add_argument('--authorization')
    parser.add_argument('--output')
    if archive:
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--archive')
        group.add_argument('--archive-pattern')
    return parser.parse_args()


def main():
    try:
        args = arguments(__doc__, archive=True)
        require_operator()  # Before private metadata, glob or plan access.
        existing_file(args.plan, 'REGISTRATION_PLAN_MISSING')
        archive = select_archive(args.archive_pattern) if args.archive_pattern else args.archive
        print(prepare(args.plan, archive, args.count_tools, args.authorization, args.output))
        return 0
    except Stop as exc:
        print('STOP ISSUE=' + str(exc))
    except SystemExit as exc:
        return exc.code
    except BaseException:
        print('STOP ISSUE=LOCAL_PLAN_UPDATE_NOT_COMPLETED')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
