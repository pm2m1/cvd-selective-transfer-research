#!/usr/bin/env python3
"""Independent-terminal orchestration; never supplies authorization responses.

No input is read at import. Public installation is allowlisted; clinical integrity
is checked only by the original, separately authorized export operation.
"""
from __future__ import annotations
import argparse
import contextlib
import getpass
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import warnings

PUBLIC_MANIFEST_SHA = 'WITHHELD_REFERENCE_BINDING'
CONFIG_HELPER_SHA = 'WITHHELD_REFERENCE_BINDING'
CANDIDATES = ['matched_control', 'head_only', 'logical', 'compact_full',
              'target_lr_1e4', 'target_lr_3e4', 'target_logistic']
EXPORT_PURPOSE = 'new_private_development_export_no_target_test_v1'
TRAIN_PURPOSE = 'new_exploratory_development_training_no_test_v1'
COMPLETE = 'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED'
HELPERS = Path(__file__).resolve().parent


class Stop(Exception):
    def __init__(self, code):
        self.code = code


def need(condition, code):
    if not condition:
        raise Stop(code)


def regular_stream(path):
    path = Path(path)
    need(stat.S_ISREG(path.lstat().st_mode), 'EXPECTED_REGULAR_FILE')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    stream = os.fdopen(fd, 'rb')
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        stream.close()
        raise Stop('EXPECTED_REGULAR_FILE')
    return stream


def sha(path):
    h = hashlib.sha256()
    with regular_stream(path) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'JSON_STRUCTURE_REJECTED')
            result[key] = value
        return result
    def invalid(value):
        raise Stop('JSON_STRUCTURE_REJECTED')
    with regular_stream(path) as stream:
        return json.load(stream, object_pairs_hook=pairs, parse_constant=invalid)


def private_json(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def absolute(value):
    need(isinstance(value, str) and bool(value) and not any(c in value for c in '\x00\r\n<>${}'), 'PATH_REQUIRED')
    p = Path(value)
    need(p.is_absolute() and '..' not in p.parts, 'ABSOLUTE_PATH_REQUIRED')
    return p


def public_file(root, relative):
    rel = PurePosixPath(relative)
    need(not rel.is_absolute() and '..' not in rel.parts and '\\' not in relative, 'PUBLIC_PATH_REJECTED')
    p = root
    for part in rel.parts:
        p = p / part
        need(not p.is_symlink(), 'PUBLIC_SYMLINK_REJECTED')
    need(p.resolve().is_relative_to(root.resolve()) and p.is_file(), 'PUBLIC_FILE_MISSING')
    return p


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def public_inventory(root):
    """Read only the known public manifest and its 93 explicitly named files."""
    mp = public_file(root, 'PUBLIC_STAGING_MANIFEST.json')
    need(sha(mp) == PUBLIC_MANIFEST_SHA, 'PUBLIC_MANIFEST_MISMATCH')
    m = read_json(mp)
    need(len(m['public_source_files']) == 63 and len(m['additional_public_records']) == 5
         and len(m['experiment_tools']) == 25, 'PUBLIC_INVENTORY_REJECTED')
    files = {}
    for row in m['public_source_files']:
        name = row['path']
        need(name.startswith('src/dmv_mat_cvd/') and name.endswith('.py'), 'PUBLIC_INVENTORY_REJECTED')
        files['public_project/' + name] = row['expected_sha256']
    for row in m['additional_public_records']:
        need(row['path'].startswith('configs/') and row['path'].endswith('.json'), 'PUBLIC_INVENTORY_REJECTED')
        files['public_project/' + row['path']] = row['actual_sha256']
    for row in m['experiment_tools']:
        files['experiment_tools/' + row['path']] = row['source_sha256']
    need(len(files) == 93, 'PUBLIC_INVENTORY_REJECTED')
    for name, digest in files.items():
        need(sha(public_file(root, name)) == digest, 'PUBLIC_FILE_HASH_MISMATCH')
    return files


def helper_inventory(root):
    ledger = read_json(public_file(root, 'helpers/WORKFLOW_PUBLIC_BINDINGS.json'))
    need(ledger.get('schema') == 'workflow-public-helper-bindings-v1', 'HELPER_LEDGER_REJECTED')
    files = ledger['files']
    need(files.get('configure_export_local.py') == CONFIG_HELPER_SHA
         and 'run_development_workflow.py' in files and 'review_development_results_local.py' in files,
         'HELPER_LEDGER_REJECTED')
    for name, digest in files.items():
        need(sha(public_file(root / 'helpers', name)) == digest, 'WORKFLOW_HELPER_HASH_MISMATCH')
    return files


def verify_installation(root):
    public_inventory(root)
    helper_inventory(root)


def install_public(source, destination):
    """Add only verified public files. No private records or directory recursion."""
    source, destination = absolute(str(source)), absolute(str(destination))
    need(not source.resolve().is_relative_to(destination.resolve())
         and not destination.resolve().is_relative_to(source.resolve()), 'INSTALL_TREES_MUST_BE_SEPARATE')
    files = public_inventory(source)
    helpers = helper_inventory(source)
    copies = {**files, 'PUBLIC_STAGING_MANIFEST.json': PUBLIC_MANIFEST_SHA,
              **{'helpers/' + n: h for n, h in helpers.items()}}
    copies['helpers/WORKFLOW_PUBLIC_BINDINGS.json'] = sha(source/'helpers/WORKFLOW_PUBLIC_BINDINGS.json')
    existed = destination.exists()
    if existed:
        need(destination.is_dir() and not destination.is_symlink(), 'INSTALL_DESTINATION_REJECTED')
        need(stat.S_IMODE(destination.stat().st_mode) & 0o077 == 0, 'PRIVATE_INSTALLATION_PERMISSIONS_REQUIRED')
        # Existing core must already be complete. Helpers may be added, never overwritten.
        public_inventory(destination)
    else:
        need(destination.parent.is_dir(), 'INSTALL_PARENT_MISSING')
    # Inspect only known public destinations, not unrelated/private files in the tree.
    for name, digest in copies.items():
        p = destination / name
        for parent in [destination, *p.relative_to(destination).parents]:
            check = parent if parent == destination else destination / parent
            need(not check.is_symlink(), 'INSTALL_DESTINATION_REJECTED')
        if p.exists() or p.is_symlink():
            need(not p.is_symlink() and p.is_file() and sha(p) == digest, 'INSTALL_EXISTING_FILE_CONFLICT')
    if not existed:
        destination.mkdir(mode=0o700)
    for name, digest in copies.items():
        p = destination/name
        if p.exists():
            continue
        p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(public_file(source, name).read_bytes())
        need(sha(p) == digest, 'INSTALL_COPY_MISMATCH')
    verify_installation(destination)
    return 'PUBLIC_INSTALLATION_VERIFIED_NO_PRIVATE_TRANSFER'


def hidden(prompt):
    need(sys.stdin.isatty(), 'INDEPENDENT_TERMINAL_REQUIRED')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass(prompt + ' (hidden): ')


def independent_runtime(root):
    # The original boundary is used unchanged, before opening any private config/state.
    verify_installation(root)
    runtime = load_module('_workflow_original_local_runtime', root/'experiment_tools/local_execution.py')
    runtime.require_local()
    return runtime


def ensure_configured(helper, config_path, project):
    path, config, fingerprint = helper.load_config(str(config_path))
    contract, structure = helper._base_checks(config)
    need(contract and structure, 'EXPORT_CONFIGURATION_REJECTED')
    need(absolute(config['isolated_public_project']).resolve() == project.resolve(), 'PUBLIC_PROJECT_BINDING_MISMATCH')
    changed = False
    updated = dict(config)
    for key in helper.PATH_FIELDS:
        if config[key] is None or config[key] == '':
            updated[key] = hidden('Enter ' + key)
            changed = True
        else:
            # Invalid supplied paths stop; never silently substitute another location.
            helper._existing_path(config[key], directory=key == 'data_root')
    result = helper.assess(updated)
    helper._print_status(result)
    need(all(result.values()), 'LOCAL_CONFIGURATION_STOP')
    if changed:
        helper.atomic_save(path, updated, fingerprint)
    _, config, _ = helper.load_config(str(path))
    need(all(helper.assess(config).values()), 'CONFIGURATION_REVALIDATION_STOP')
    return config


def required_metadata(config, project):
    """Existence checks only; no private file is hashed/opened here."""
    public_config = read_json(project/'configs/public_haalsi_mhas_v2.ready_pending_execution_m5l.json')
    source = read_json(project/public_config['source_mapping'])
    target = read_json(project/public_config['target_mapping'])
    root = absolute(config['data_root'])
    names = [root/source['files']['main'], *[root/n for n in target['files'].values()],
             absolute(config['master_file']), absolute(config['questionnaire'])]
    # Constant paths are extracted from the original loader, not discovered by searching.
    import ast
    loader = ast.parse((project/'src/dmv_mat_cvd/real_baselines.py').read_text())
    evidence_relative = None
    for node in loader.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'EVIDENCE' for t in node.targets):
            evidence_relative = ast.literal_eval(node.value.args[0])
    need(isinstance(evidence_relative, str), 'ORIGINAL_EVIDENCE_LOCATION_UNRESOLVED')
    rel = PurePosixPath(evidence_relative)
    need(not rel.is_absolute() and '..' not in rel.parts, 'ORIGINAL_EVIDENCE_LOCATION_UNRESOLVED')
    names += [project/rel, root/'private_locks/public-haalsi-mhas-v2/target_lock.json',
              root/'private_locks/public-haalsi-mhas-v2/participant_assignments.private.json']
    need(all(p.is_file() and not p.is_symlink() for p in names), 'REQUIRED_ORIGINAL_INPUT_MISSING')
    return root/'private_locks/public-haalsi-mhas-v2/participant_assignments.private.json'


def source_state(root, config_path):
    return {'public_manifest_sha256': PUBLIC_MANIFEST_SHA,
            'helper_ledger_sha256': sha(root/'helpers/WORKFLOW_PUBLIC_BINDINGS.json'),
            'installation_root_sha256': hashlib.sha256(str(root.resolve()).encode()).hexdigest(),
            'export_config_sha256': sha(config_path)}


def private_workspace(path, create=False):
    path = absolute(str(path))
    need(not path.is_symlink(), 'WORKSPACE_REJECTED')
    if create and not path.exists():
        need(path.parent.is_dir(), 'WORKSPACE_PARENT_MISSING')
        path.mkdir(mode=0o700)
    need(path.is_dir() and stat.S_IMODE(path.stat().st_mode) & 0o077 == 0, 'PRIVATE_WORKSPACE_PERMISSIONS_REQUIRED')
    return path


def dependency_check():
    # Public module-discovery metadata only; no training or clinical input read.
    packages = ['numpy', 'pandas', 'torch', 'sklearn', 'scipy', 'matplotlib', 'joblib']
    need(all(importlib.util.find_spec(name) is not None for name in packages), 'RUNTIME_DEPENDENCY_MISSING')


def prepare(root, workspace, config_path, helper):
    dependency_check()
    workspace = private_workspace(workspace, create=True)
    need(not workspace.is_relative_to(root/'experiment_tools'), 'WORKSPACE_INSIDE_TOOL_TREE')
    need(not (workspace/'workflow.started.private.json').exists(), 'WORKFLOW_CONSUMED_NO_RETRY')
    state_path = workspace/'workflow.prepared.private.json'
    if state_path.exists():
        state = read_json(state_path)
        need(state['export_configuration'] == str(config_path)
             and state['bindings'] == source_state(root, config_path), 'PREPARATION_BINDING_MISMATCH')
        config = read_json(config_path)
        need(absolute(config['isolated_public_project']).resolve() == (root/'public_project').resolve(), 'PUBLIC_PROJECT_BINDING_MISMATCH')
        need(all(helper.assess(config).values()), 'LOCAL_CONFIGURATION_STOP')
        required_metadata(config, root/'public_project')
        return state
    for name in ['export.authorization.private.json', 'training.authorization.private.json', 'export', 'training', 'training.reviewed.private.json']:
        need(not (workspace/name).exists(), 'EXISTING_OPERATION_ARTIFACT_NO_RETRY')
    config = ensure_configured(helper, config_path, root/'public_project')
    required_metadata(config, root/'public_project')
    state = {'schema': 'development-workflow-prepared-v1', 'export_configuration': str(config_path),
             'bindings': source_state(root, config_path), 'public_dependencies': 'VERIFIED',
             'private_paths': 'CONFIGURED_METADATA_ONLY',
             'original_input_integrity': 'PENDING_ORIGINAL_AUTHORIZED_LOADER',
             'provider_institutional_permission': 'NOT_ESTABLISHED_BY_PREPARATION',
             'export_authorization': 'NOT_OBTAINED', 'training_authorization': 'NOT_OBTAINED'}
    private_json(state_path, state)
    return state


@contextlib.contextmanager
def private_log(path):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    saved = [os.dup(1), os.dup(2)]
    try:
        os.dup2(fd, 1); os.dup2(fd, 2)
        with os.fdopen(os.dup(fd), 'w') as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            try:
                yield
            except BaseException:
                import traceback
                traceback.print_exc(file=stream)  # Authorized private context only.
                raise
    finally:
        sys.stdout.flush(); sys.stderr.flush()
        os.dup2(saved[0], 1); os.dup2(saved[1], 2)
        for handle in saved + [fd]: os.close(handle)


def operation_completed(output):
    need(output.is_dir() and not output.is_symlink(), 'OPERATION_OUTPUT_MISSING')
    started = read_json(output/'operation_started.private.json')
    receipt = read_json(output/'completion.private.json')
    need(started.get('status') == 'STARTED_CONSUMED' and receipt.get('status') == COMPLETE
         and receipt.get('attempt_consumed') is True, 'OPERATION_NOT_COMPLETED_NO_RETRY')


def verify_memberships(data, assignments, trainer):
    trainer.validate_bundle(data, {'preprocessing_fit_role': 'source_train',
        'protocol': 'public-haalsi-mhas-v2', 'test_rows_included': False})
    for role in trainer.ROLES:
        group = assignments['source_partitions'] if role.startswith('source_') else assignments['target_partitions']
        key = 'target_adaptation_pool' if role == 'target_pool' else role
        need(set(data[role+'__ids'].tolist()) == set(group[key]), 'ORIGINAL_MEMBERSHIP_MISMATCH')
    for i in range(10):
        need(set(data['target_pool__ids'][data[f'draw_{i}']].tolist()) ==
             set(assignments['adaptation_draws'][str(i)]['primary_25_75']), 'ORIGINAL_DRAW_MISMATCH')


class FrozenBoundary:
    """Real operations are delegated to original CLIs with inherited terminal/env."""
    def __init__(self, root, runtime):
        self.root, self.runtime = root, runtime

    def command(self, script, mode, config, authorization, output):
        self.runtime.require_local()
        need(script in {'prepare_development_inputs.py', 'train_exploratory_candidates.py'}
             and mode in {'--authorize-local', '--execute-local'}, 'ORIGINAL_COMMAND_REJECTED')
        verify_installation(self.root)
        # No stdin pipes, scripted responses, PTY, environment changes or retry.
        result = subprocess.run([sys.executable, '-B', str(self.root/'experiment_tools'/script), mode,
            '--config', str(config), '--authorization', str(authorization), '--output', str(output)],
            cwd=self.root/'experiment_tools', check=False)
        return result.returncode

    def authorize(self, script, config, authorization, output):
        need(not authorization.exists() and not output.exists(), 'AUTHORIZATION_OR_OUTPUT_EXISTS_NO_RETRY')
        need(self.command(script, '--authorize-local', config, authorization, output) == 0,
             'INDEPENDENT_AUTHORIZATION_CANCELLED_OR_FAILED')

    def verify_authorization(self, purpose, config, authorization, output):
        self.runtime.require_local()
        need(authorization.is_file() and not authorization.is_symlink(), 'ORIGINAL_AUTHORIZATION_MISSING')
        auth = read_json(authorization)
        need(auth.get('purpose') == purpose and auth.get('authorized') is True
             and auth.get('scope_confirmed_by_operator') is True and bool(auth.get('operator'))
             and auth.get('output_binding') == str(output.resolve())
             and auth.get('config_sha256') == sha(config)
             and auth.get('code_bindings') == self.runtime.code_hashes(), 'ORIGINAL_AUTHORIZATION_BINDING_MISMATCH')

    def execute(self, script, config, authorization, output):
        need(self.command(script, '--execute-local', config, authorization, output) == 0,
             'ORIGINAL_OPERATION_FAILED_NO_RETRY')
        operation_completed(output)

    def trainer(self):
        tools = self.root/'experiment_tools'
        sys.path.insert(0, str(tools))
        import train_exploratory_candidates as trainer
        need(Path(trainer.__file__).resolve() == (tools/'train_exploratory_candidates.py').resolve(), 'IMPORTED_TRAINER_ORIGIN_MISMATCH')
        return trainer

    def validate_export(self, config_path, output):
        operation_completed(output)
        config = read_json(config_path)
        manifest = read_json(output/'development_manifest.private.json')
        trainer = self.trainer()
        need(manifest['bundle_sha256'] == sha(output/'development_bundle.private.npz')
             and manifest['preprocessor_sha256'] == sha(output/'source_preprocessing.private.json')
             and manifest['preparation_script_sha256'] == sha(self.root/'experiment_tools/prepare_development_inputs.py')
             and manifest['public_source_bindings'] == config['public_source_bindings'], 'EXPORT_MANIFEST_MISMATCH')
        project = self.root/'public_project'
        sys.path.insert(0, str(project/'src'))
        import dmv_mat_cvd.real_baselines as baseline
        need(Path(baseline.__file__).resolve() == (project/'src/dmv_mat_cvd/real_baselines.py').resolve(), 'IMPORTED_LOADER_ORIGIN_MISMATCH')
        assignments = absolute(config['data_root'])/'private_locks/public-haalsi-mhas-v2/participant_assignments.private.json'
        need(sha(assignments) == baseline.ASSIGNMENTS_SHA256 == manifest['source_assignments_sha256'], 'ASSIGNMENT_BINDING_MISMATCH')
        import numpy as np
        with np.load(output/'development_bundle.private.npz', allow_pickle=False) as bundle:
            data = {k: bundle[k].copy() for k in bundle.files}
        need(manifest['preprocessing_fit_role'] == 'source_train' and manifest['test_rows_included'] is False
             and manifest['protocol'] == 'public-haalsi-mhas-v2', 'EXPORT_CONTRACT_MISMATCH')
        verify_memberships(data, read_json(assignments), trainer)
        return assignments

    def training_config(self, export_output, assignments):
        c = read_json(self.root/'experiment_tools/exploratory_training_config.template.json')
        validate_training_plan(c)
        for key, path in [('development_manifest', export_output/'development_manifest.private.json'),
                          ('development_bundle', export_output/'development_bundle.private.npz'),
                          ('original_assignments', assignments)]:
            if key == 'original_assignments':
                need(c[key]['sha256'] == sha(path), 'ORIGINAL_ASSIGNMENT_IDENTITY_MISMATCH')
            c[key] = {'path': str(path.resolve()), 'sha256': sha(path)}
        return c

    def review(self, config, output, workspace, show):
        operation_completed(output)
        provenance = read_json(output/'execution_provenance.private.json')
        need(provenance['config'] == read_json(config)
             and provenance['script_sha256'] == sha(self.root/'experiment_tools/train_exploratory_candidates.py')
             and provenance['test_inference'] is False and provenance['disclosure_cleared'] is False,
             'TRAINING_PROVENANCE_MISMATCH')
        from review_development_results_local import write_review
        return write_review(output/'exploratory_development.private.json', workspace/'local_review', show)


def validate_training_plan(config):
    need(config['schema'] == 'exploratory-development-v1' and config['mode'] == 'independent_local_only'
         and config['phase'] == 1 and config['no_test_evaluation'] is True and config['candidates'] == CANDIDATES,
         'TRAINING_TEMPLATE_REJECTED')


def run_prepared(root, workspace, state, boundary, show=False):
    """One consumed orchestration; no implicit resumption, retries or reuse."""
    workspace = private_workspace(workspace)
    export_config = absolute(state['export_configuration'])
    need(state['bindings'] == source_state(root, export_config), 'PREPARATION_BINDING_MISMATCH')
    names = ['workflow.started.private.json', 'workflow.completion.private.json',
             'export.authorization.private.json', 'training.authorization.private.json', 'export', 'training',
             'training.reviewed.private.json', 'local_review']
    need(all(not (workspace/n).exists() and not (workspace/n).is_symlink() for n in names), 'WORKFLOW_CONSUMED_NO_RETRY')
    private_json(workspace/'workflow.started.private.json', {'status': 'STARTED_CONSUMED', 'bindings': state['bindings']})
    stage = 'EXPORT_AUTHORIZATION'
    try:
        export, training = workspace/'export', workspace/'training'
        export_auth, training_auth = workspace/'export.authorization.private.json', workspace/'training.authorization.private.json'
        boundary.authorize('prepare_development_inputs.py', export_config, export_auth, export)
        boundary.verify_authorization(EXPORT_PURPOSE, export_config, export_auth, export)
        need(state['bindings'] == source_state(root, export_config), 'PREPARATION_BINDING_MISMATCH')
        stage = 'AUTHORIZED_EXPORT'
        boundary.execute('prepare_development_inputs.py', export_config, export_auth, export)
        stage = 'EXPORT_OUTPUT_VALIDATION'
        with private_log(workspace/'post_export_validation.private.log'):
            assignments = boundary.validate_export(export_config, export)
            training_config = boundary.training_config(export, assignments)
            validate_training_plan(training_config)
            training_config_path = workspace/'training.reviewed.private.json'
            private_json(training_config_path, training_config)
            training_config_sha = sha(training_config_path)
        private_json(workspace/'export.verified.private.json', {
            'original_input_integrity': 'SATISFIED_BY_COMPLETED_ORIGINAL_LOADER',
            'provider_institutional_scope': 'OPERATOR_ATTESTED_IN_ORIGINAL_AUTHORIZATION_NOT_EXTERNALLY_VERIFIED',
            'export_authorization': 'ORIGINAL_RECORD_VERIFIED',
            'bundle_manifest_sha256': sha(export/'development_manifest.private.json'),
            'training_config_sha256': sha(training_config_path)})
        stage = 'TRAINING_AUTHORIZATION'
        boundary.authorize('train_exploratory_candidates.py', training_config_path, training_auth, training)
        boundary.verify_authorization(TRAIN_PURPOSE, training_config_path, training_auth, training)
        need(sha(training_config_path) == training_config_sha, 'TRAINING_CONFIGURATION_CHANGED')
        stage = 'AUTHORIZED_TRAINING'
        boundary.execute('train_exploratory_candidates.py', training_config_path, training_auth, training)
        stage = 'PRIVATE_RESULTS_REVIEW'
        with private_log(workspace/'results_review.private.log'):
            table = boundary.review(training_config_path, training, workspace, False)
        private_json(workspace/'workflow.completion.private.json', {'status': 'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED',
            'attempt_consumed': True, 'stage': 'NONE', 'issue': 'NONE',
            'export_manifest_sha256': sha(export/'development_manifest.private.json'),
            'training_report_sha256': sha(training/'exploratory_development.private.json'),
            'private_review_sha256': sha(workspace/'local_review/development_review.private.json'),
            'private_review_markdown_sha256': sha(workspace/'local_review/development_comparison.private.md'),
            'training_config_sha256': sha(training_config_path), 'bindings': state['bindings'],
            'real_test_evaluation': False, 'scientific_success_claim': False})
        if show:
            try:
                print(table)  # Explicit local-only request; no public or remote logging.
            except (OSError, ValueError):
                pass  # A display failure cannot rewrite a completed operation receipt.
        return 'WORKFLOW_COMPLETE_PRIVATE_REVIEW_ONLY'
    except BaseException as exc:
        if not (workspace/'workflow.completion.private.json').exists():
            private_json(workspace/'workflow.completion.private.json', {'status': 'INTERRUPTED_NO_RETRY' if isinstance(exc, KeyboardInterrupt) else 'FAILED_NO_RETRY',
                'attempt_consumed': True, 'stage': stage,
                'issue': exc.code if isinstance(exc, Stop) else 'UNEXPECTED_WORKFLOW_EXCEPTION'})
        raise


def status(workspace):
    if (workspace/'workflow.completion.private.json').is_file():
        value = read_json(workspace/'workflow.completion.private.json').get('status')
        need(value in {COMPLETE, 'FAILED_NO_RETRY', 'INTERRUPTED_NO_RETRY'}, 'WORKFLOW_RECEIPT_REJECTED')
        return value
    if (workspace/'workflow.started.private.json').exists():
        return 'STARTED_CONSUMED_NO_AUTOMATIC_RESUME'
    if (workspace/'workflow.prepared.private.json').exists():
        return 'PREPARED_NOT_AUTHORIZED'
    return 'NOT_PREPARED'


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Stop('ARGUMENTS_REJECTED')


def main(argv=None):
    try:
        p = Parser(prog='run_development_workflow.py')
        g = p.add_mutually_exclusive_group(required=True)
        for mode in ['prepare', 'run-authorized', 'status', 'validate-only']:
            g.add_argument('--'+mode, action='store_true')
        p.add_argument('--workspace'); p.add_argument('--export-config')
        p.add_argument('--install-from'); p.add_argument('--install-to')
        p.add_argument('--show-private-results', action='store_true')
        args = p.parse_args(argv)
        root = HELPERS.parent
        runtime = independent_runtime(root)  # Original gate before any private read.
        if args.install_from or args.install_to:
            need(args.prepare and args.install_from and args.install_to
                 and not args.workspace and not args.export_config, 'INSTALL_ARGUMENTS_REJECTED')
            print(install_public(absolute(args.install_from), absolute(args.install_to)))
            return 0
        helper = load_module('_workflow_config_helper', HELPERS/'configure_export_local.py')
        workspace = absolute(args.workspace or hidden('Enter private workflow workspace'))
        need(not workspace.resolve().is_relative_to(root/'experiment_tools'), 'WORKSPACE_INSIDE_TOOL_TREE')
        if args.status:
            print('WORKFLOW_STATUS: '+status(private_workspace(workspace)))
            return 0
        state_path = workspace/'workflow.prepared.private.json'
        if state_path.is_file():
            old = read_json(state_path)
            config_path = absolute(args.export_config or old['export_configuration'])
        else:
            config_path = absolute(args.export_config or hidden('Enter existing reviewed export configuration'))
        if args.validate_only:
            dependency_check()
            _, config, _ = helper.load_config(str(config_path))
            need(all(helper._base_checks(config)), 'EXPORT_CONFIGURATION_REJECTED')
            need(absolute(config['isolated_public_project']).resolve() == (root/'public_project').resolve(), 'PUBLIC_PROJECT_BINDING_MISMATCH')
            checks = helper.assess(config)
            helper._print_status(checks)
            need(all(checks.values()), 'LOCAL_CONFIGURATION_STOP')
            required_metadata(config, root/'public_project')
            print('ORIGINAL_INPUT_INTEGRITY: PENDING_ORIGINAL_AUTHORIZED_LOADER')
            print('INDEPENDENT_AUTHORIZATION: NOT_GRANTED_BY_VALIDATION')
            return 0
        state = prepare(root, workspace, config_path, helper)
        if args.prepare:
            print('PUBLIC_DEPENDENCIES: VERIFIED')
            print('PRIVATE_PATHS: CONFIGURED_METADATA_ONLY')
            print('ORIGINAL_INPUT_INTEGRITY: PENDING_ORIGINAL_AUTHORIZED_LOADER')
            print('EXPORT_AUTHORIZATION: REQUIRED_ORIGINAL_INTERACTIVE_CONTRACT')
            print('TRAINING_AUTHORIZATION: SEPARATELY_REQUIRED')
            return 0
        print(run_prepared(root, workspace, state, FrozenBoundary(root, runtime), args.show_private_results))
        return 0
    except BaseException as exc:
        if isinstance(exc, SystemExit) and exc.code == 0:
            return 0
        # These codes are produced internally; no exception text or path is printed.
        print('STOP ISSUE='+ (exc.code if isinstance(exc, Stop) else 'INDEPENDENT_WORKFLOW_NOT_COMPLETED'))
        return 2


if __name__ == '__main__':
    # Sibling review helpers must share this module's exception/binding identity.
    sys.modules.setdefault('run_development_workflow', sys.modules[__name__])
    sys.exit(main())
