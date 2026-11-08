"""Temporary invented files only; never inspect any actual research configuration."""
import ast
from contextlib import redirect_stdout, redirect_stderr
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'configure_export_local.py'
spec = importlib.util.spec_from_file_location('synthetic_configuration_helper', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
PRODUCTION_DIGEST = helper.EXPECTED_BINDINGS_SHA256


class ConfigHelperTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='invented_export_config_test_')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root/'invented_public_project'
        self.project.mkdir()
        self.bindings = {}
        for i in range(63):
            name = f'src/dmv_mat_cvd/invented_{i:02d}.py'
            content = f'# Entirely invented public source {i}\n'.encode()
            path = self.project/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            self.bindings[name] = hashlib.sha256(content).hexdigest()
        self.fixture_digest = hashlib.sha256(json.dumps(self.bindings, sort_keys=True,
            separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()
        # White-box fixture substitution only. Production has no pin override CLI.
        self.pin_patch = patch.object(helper, 'EXPECTED_BINDINGS_SHA256', self.fixture_digest)
        self.pin_patch.start(); self.addCleanup(self.pin_patch.stop)
        self.data = self.root/'invented_input_directory'; self.data.mkdir()
        self.master = self.root/'invented_master.file'; self.master.write_bytes(b'FABRICATED_NOT_CLINICAL')
        self.questionnaire = self.root/'invented_questionnaire.file'; self.questionnaire.write_bytes(b'FABRICATED_DOCUMENT')
        self.path = self.root/'invented_config.json'
        self.config = {'schema': helper.SCHEMA, 'mode': 'independent_local_only', 'no_test_rows': True,
            'isolated_public_project': str(self.project), 'public_source_bindings': self.bindings,
            'data_root': None, 'master_file': None, 'questionnaire': None,
            'unchanged_extra': {'integer': 7, 'flag': False, 'unicode': '\u03b1', 'nested': [1, None, 2.5]}}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.config, ensure_ascii=True)+'\n')

    def populated(self):
        self.config.update(data_root=str(self.data), master_file=str(self.master), questionnaire=str(self.questionnaire))
        self.save()

    def invoke(self, args=None, interactive=False, entries=None):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            if interactive:
                with patch.object(helper.sys.stdin, 'isatty', return_value=True), patch.object(
                        helper.getpass, 'getpass', side_effect=entries or [str(self.data), str(self.master), str(self.questionnaire)]):
                    rc = helper.main(args or [str(self.path)])
            else:
                rc = helper.main(args or [str(self.path), '--validate-only'])
        text = output.getvalue()
        self.assertEqual(len(text.splitlines()), 7)
        for label, line in zip(helper.STATUS_LABELS, text.splitlines()):
            self.assertIn(line, [f'{label}: PASS', f'{label}: STOP'])
        self.assertEqual(errors.getvalue(), '')
        self.assertNotIn(str(self.root), text)
        self.assertNotIn('Traceback', text)
        return rc, text

    def test_population_and_preservation_of_every_other_value(self):
        before = copy.deepcopy(self.config)
        rc, text = self.invoke(interactive=True)
        self.assertEqual(rc, 0); self.assertNotIn('STOP', text)
        after = json.loads(self.path.read_text())
        self.assertEqual([after[k] for k in helper.PATH_FIELDS], [str(self.data), str(self.master), str(self.questionnaire)])
        for key in before:
            if key not in helper.PATH_FIELDS: self.assertEqual(before[key], after[key])
        self.assertEqual(list(after['public_source_bindings']), list(before['public_source_bindings']))

    def test_population_keeps_binding_order_and_unknown_fields(self):
        self.config['public_source_bindings'] = dict(reversed(list(self.bindings.items())))
        self.config['future_public_option'] = ['unchanged', 9]
        self.save(); before = copy.deepcopy(self.config)
        self.assertEqual(self.invoke(interactive=True)[0], 0)
        after = json.loads(self.path.read_text())
        self.assertEqual(list(after['public_source_bindings']), list(before['public_source_bindings']))
        self.assertEqual(after['future_public_option'], before['future_public_option'])

    def test_private_mode_0600_after_atomic_save(self):
        os.chmod(self.path, 0o644)
        self.assertEqual(self.invoke(interactive=True)[0], 0)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)

    def test_atomic_replace_uses_same_directory_restrictive_temp_and_no_leftover(self):
        before = self.path.read_bytes(); real_replace = os.replace; observed = []
        def checked_replace(source, destination):
            source, destination = Path(source), Path(destination)
            self.assertEqual(source.parent, self.path.parent)
            self.assertEqual(destination, self.path)
            self.assertEqual(self.path.read_bytes(), before)
            self.assertEqual(stat.S_IMODE(source.stat().st_mode), 0o600)
            observed.append(source)
            return real_replace(source, destination)
        with patch.object(helper.os, 'replace', side_effect=checked_replace):
            self.assertEqual(self.invoke(interactive=True)[0], 0)
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0].exists())
        self.assertEqual(list(self.root.glob('.export-config-*.tmp')), [])

    def test_validate_only_does_not_prompt_or_write(self):
        self.populated(); before = self.path.read_bytes(); info = self.path.stat()
        with (patch.object(helper.getpass, 'getpass', side_effect=AssertionError('must not prompt')),
              patch.object(helper, 'atomic_save', side_effect=AssertionError('must not write'))):
            rc, text = self.invoke()
        self.assertEqual(rc, 0); self.assertNotIn('STOP', text)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(info.st_mtime_ns, self.path.stat().st_mtime_ns)
        self.assertEqual(stat.S_IMODE(info.st_mode), stat.S_IMODE(self.path.stat().st_mode))

    def test_clinical_input_files_are_never_opened(self):
        self.populated(); original_open = helper.os.open; opened = []
        def public_and_config_only(path, *args, **kwargs):
            self.assertNotIn(str(path), [str(self.master), str(self.questionnaire), str(self.data)])
            opened.append(str(path)); return original_open(path, *args, **kwargs)
        with patch.object(helper.os, 'open', side_effect=public_and_config_only):
            # The source verifier checks function identity for supports_dir_fd.
            with patch.object(helper.os, 'supports_dir_fd', helper.os.supports_dir_fd | {helper.os.open}):
                self.assertEqual(self.invoke()[0], 0)
        self.assertTrue(opened)

    def test_missing_config_rejected(self):
        self.path.unlink(); self.assertEqual(self.invoke()[0], 2)

    def test_config_directory_rejected(self):
        self.assertEqual(self.invoke([str(self.root), '--validate-only'])[0], 2)

    def test_relative_config_rejected(self):
        self.assertEqual(self.invoke(['invented_config.json', '--validate-only'])[0], 2)

    def test_schema_rejected(self):
        self.config['schema'] = 'invented_other_schema'; self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_mode_rejected(self):
        self.config['mode'] = 'invented_other_mode'; self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_no_test_rows_integer_is_not_true(self):
        self.config['no_test_rows'] = 1; self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_no_test_rows_false_rejected(self):
        self.config['no_test_rows'] = False; self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_62_bindings_rejected(self):
        self.config['public_source_bindings'].pop(next(iter(self.bindings)))
        self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_64_bindings_rejected(self):
        self.config['public_source_bindings']['src/dmv_mat_cvd/invented_extra.py'] = '0'*64
        self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_changed_binding_rejected_even_with_63_entries(self):
        self.config['public_source_bindings'][next(iter(self.bindings))] = '0'*64
        self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_changed_public_file_rejected(self):
        self.populated(); (self.project/next(iter(self.bindings))).write_text('# changed invented source')
        rc, text = self.invoke(); self.assertEqual(rc, 2)
        self.assertIn('PUBLIC_SOURCE_BINDINGS: STOP', text)

    def test_missing_public_file_rejected(self):
        self.populated(); (self.project/next(iter(self.bindings))).unlink()
        self.assertEqual(self.invoke()[0], 2)

    def test_source_symlink_rejected(self):
        self.populated(); path = self.project/next(iter(self.bindings)); copy_path = self.root/'invented_outside.py'
        copy_path.write_bytes(path.read_bytes()); path.unlink(); path.symlink_to(copy_path)
        self.assertEqual(self.invoke()[0], 2)

    def test_source_parent_symlink_rejected(self):
        self.populated(); original = self.project/'src'; renamed = self.root/'invented_public_source'
        original.rename(renamed); original.symlink_to(renamed, target_is_directory=True)
        self.assertEqual(self.invoke()[0], 2)

    def test_project_directory_missing(self):
        self.populated(); self.config['isolated_public_project'] = str(self.root/'invented_absent_project')
        self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_project_relative_rejected(self):
        self.populated(); self.config['isolated_public_project'] = 'invented_relative_project'
        self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_all_three_path_types_and_placeholders(self):
        self.populated()
        for field in helper.PATH_FIELDS:
            for invalid in ['relative/invented', str(self.root/'invented_absent'), '/<LOCAL_PLACEHOLDER>',
                            '/path/to/invented', '/TODO/invented', '/$INVENTED/file', None]:
                with self.subTest(field=field, invalid_kind=type(invalid).__name__):
                    original = self.config[field]; self.config[field] = invalid; self.save()
                    self.assertEqual(self.invoke()[0], 2)
                    self.config[field] = original

    def test_wrong_file_directory_types_rejected(self):
        self.populated()
        for field, value in [('data_root', str(self.master)), ('master_file', str(self.data)), ('questionnaire', str(self.data))]:
            with self.subTest(field=field):
                previous = self.config[field]; self.config[field] = value; self.save()
                self.assertEqual(self.invoke()[0], 2); self.config[field] = previous

    def test_input_file_symlinks_rejected(self):
        self.populated(); link = self.root/'invented_link'; link.symlink_to(self.master)
        self.config['master_file'] = str(link); self.save(); self.assertEqual(self.invoke()[0], 2)

    def test_symlink_config_rejected(self):
        link = self.root/'invented_config_link.json'; link.symlink_to(self.path)
        self.assertEqual(self.invoke([str(link), '--validate-only'])[0], 2)

    def test_bad_json_and_duplicate_keys_and_nan_fail_without_leakage(self):
        for value in ['{INVENTED_PRIVATE_NOT_REAL', '{"schema":1,"schema":2}', '{"x":NaN}', '[]']:
            with self.subTest(kind=value[:1]):
                self.path.write_text(value); rc, text = self.invoke()
                self.assertEqual(rc, 2); self.assertNotIn('INVENTED_PRIVATE_NOT_REAL', text)

    def test_invalid_argv_not_echoed(self):
        self.assertEqual(self.invoke([str(self.path), '--INVENTED_DO_NOT_ECHO'])[0], 2)

    def test_missing_argument_is_safe(self):
        out = io.StringIO(); err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err): rc = helper.main([])
        self.assertEqual(rc, 2); self.assertEqual(len(out.getvalue().splitlines()), 7)
        self.assertEqual(err.getvalue(), '')

    def test_noninteractive_population_stops_without_prompt(self):
        with patch.object(helper.sys.stdin, 'isatty', return_value=False), patch.object(helper.getpass, 'getpass') as prompt:
            self.assertEqual(self.invoke([str(self.path)])[0], 2)
        prompt.assert_not_called()

    def test_getpass_no_echo_warning_aborts(self):
        before = self.path.read_bytes()
        with patch.object(helper.sys.stdin, 'isatty', return_value=True), patch.object(
                helper.getpass, 'getpass', side_effect=helper.getpass.GetPassWarning('invented warning')):
            self.assertEqual(self.invoke([str(self.path)])[0], 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_invalid_population_does_not_write_or_keep_temp(self):
        before = self.path.read_bytes()
        self.assertEqual(self.invoke(interactive=True, entries=['relative', str(self.master), str(self.questionnaire)])[0], 2)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.export-config-*.tmp')), [])

    def test_unexpected_error_discloses_only_status_and_preserves_original(self):
        before = self.path.read_bytes()
        with patch.object(helper, 'assess', side_effect=RuntimeError('INVENTED_DO_NOT_ECHO')):
            self.assertEqual(self.invoke(interactive=True)[0], 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_replace_error_cleans_temporary_and_preserves_original(self):
        before = self.path.read_bytes()
        with patch.object(helper.os, 'replace', side_effect=OSError('INVENTED_DO_NOT_ECHO')):
            self.assertEqual(self.invoke(interactive=True)[0], 2)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.export-config-*.tmp')), [])

    def test_fsync_error_cleans_temporary_and_preserves_original(self):
        before = self.path.read_bytes()
        with patch.object(helper.os, 'fsync', side_effect=OSError('INVENTED_DO_NOT_ECHO')):
            self.assertEqual(self.invoke(interactive=True)[0], 2)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.root.glob('.export-config-*.tmp')), [])

    def test_detected_concurrent_configuration_change_not_overwritten(self):
        original_fsync = os.fsync
        changed = {**self.config, 'unchanged_extra': 'INVENTED_CONCURRENT_EDIT'}
        def change_after_flush(fd):
            original_fsync(fd); self.path.write_text(json.dumps(changed))
        with patch.object(helper.os, 'fsync', side_effect=change_after_flush):
            self.assertEqual(self.invoke(interactive=True)[0], 2)
        self.assertEqual(json.loads(self.path.read_text()), changed)
        self.assertEqual(list(self.root.glob('.export-config-*.tmp')), [])

    def test_interruption_is_safe_and_does_not_write(self):
        before = self.path.read_bytes()
        with patch.object(helper.sys.stdin, 'isatty', return_value=True), patch.object(
                helper.getpass, 'getpass', side_effect=KeyboardInterrupt()):
            self.assertEqual(self.invoke([str(self.path)])[0], 2)
        self.assertEqual(self.path.read_bytes(), before)

    def test_production_pin_cannot_accept_arbitrary_63_entry_map(self):
        with patch.object(helper, 'EXPECTED_BINDINGS_SHA256', PRODUCTION_DIGEST):
            self.assertFalse(helper._bindings_are_original(self.bindings))

    def test_no_nonstandard_library_imports_or_process_invocation(self):
        tree = ast.parse(SCRIPT.read_text())
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): modules.update(n.name.split('.')[0] for n in node.names)
            elif isinstance(node, ast.ImportFrom): modules.add(node.module.split('.')[0])
        self.assertLessEqual(modules, sys.stdlib_module_names | {'__future__'})
        self.assertFalse(modules & {'subprocess', 'dmv_mat_cvd', 'numpy', 'pandas', 'torch'})

    def test_cli_subprocess_safe_missing_invented_configuration(self):
        missing = self.root/'invented_missing_configuration.json'
        run = subprocess.run([sys.executable, '-B', str(SCRIPT), '--validate-only', str(missing)],
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 2); self.assertEqual(run.stderr, '')
        self.assertEqual(len(run.stdout.splitlines()), 7)
        self.assertNotIn(str(self.root), run.stdout)


if __name__ == '__main__':
    unittest.main()
