"""Disposable invented installations; no private configuration or clinical input."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import repair_public_installation_metadata as repair
import run_development_workflow as workflow


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class PublicMetadataRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='invented_metadata_repair_')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base/'invented_public_staging'; self.source.mkdir()
        self.destination = self.base/'invented_installation'; self.destination.mkdir(mode=0o700)
        self.copies = {}
        manifest = {'public_source_files':[], 'additional_public_records':[], 'experiment_tools':[]}
        for i in range(63):
            name = f'src/dmv_mat_cvd/invented_{i:02d}.py'
            payload = f'# INVENTED PURE PUBLIC SOURCE {i}\n'.encode()
            self.write_source('public_project/'+name, payload)
            manifest['public_source_files'].append({'path':name, 'expected_sha256':sha(payload)})
        for i in range(5):
            name = f'configs/invented_{i}.json'; payload = b'{"fixture":"INVENTED_PUBLIC"}\n'
            self.write_source('public_project/'+name, payload)
            manifest['additional_public_records'].append({'path':name,'actual_sha256':sha(payload)})
        for i in range(25):
            name = 'local_execution.py' if i==0 else f'invented_tool_{i}.py'
            # This one pure public guard is the unchanged real implementation.
            # It is never used to authorize or execute anything in these tests.
            payload = (HERE.parent/'experiment_tools/local_execution.py').read_bytes() if i==0 else b'# INVENTED TOOL\n'
            self.write_source('experiment_tools/'+name,payload)
            manifest['experiment_tools'].append({'path':name,'source_sha256':sha(payload)})
        names = ['configure_export_local.py','run_development_workflow.py','review_development_results_local.py']
        names += [f'invented_public_helper_{i}.md' for i in range(9)]
        for name in names:
            self.write_source('helpers/'+name,b'# INVENTED PUBLIC HELPER; NOT EXECUTED\n')
        ledger = {'schema':'workflow-public-helper-bindings-v1',
            'files':{name:sha(self.copies['helpers/'+name]) for name in names}}
        ledger_raw = (json.dumps(ledger,indent=2)+'\n').encode()
        self.write_source(repair.HELPER_LEDGER,ledger_raw)
        self.payload = (json.dumps(manifest,indent=2)+'\n').encode()
        (self.source/repair.MANIFEST).write_bytes(self.payload)
        sums = (sha(self.payload)+'  '+repair.MANIFEST+'\n').encode()
        (self.source/repair.CHECKSUMS).write_bytes(sums)
        # Only synthetic expected fingerprints are injected, never production pins.
        patches = [patch.object(repair,'MANIFEST_SHA256',sha(self.payload)),
            patch.object(repair,'HELPER_LEDGER_SHA256',sha(ledger_raw)),
            patch.object(repair,'CHECKSUMS_SHA256',sha(sums)),
            patch.object(workflow,'PUBLIC_MANIFEST_SHA',sha(self.payload)),
            patch.object(workflow,'CONFIG_HELPER_SHA',ledger['files']['configure_export_local.py'])]
        for p in patches: p.start(); self.addCleanup(p.stop)
        # Exactly the prior three-folder transfer; no root manifest/checksum.
        for name,raw in self.copies.items():
            p=self.destination/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)

    def write_source(self, name, payload):
        p=self.source/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(payload)
        self.copies[name]=payload

    def verified(self):
        return repair.verify_source(self.source)

    def apply_repair(self):
        payload,entries=self.verified()
        return repair.repair(self.source,self.destination,payload,entries)

    def test_original_failure_identifies_exact_first_public_dependency(self):
        original=workflow.public_file
        with patch.object(workflow,'public_file',wraps=original) as lookup:
            with self.assertRaises(workflow.Stop) as exc: workflow.verify_installation(self.destination)
        self.assertEqual(exc.exception.code,'PUBLIC_FILE_MISSING')
        self.assertEqual(lookup.call_count,1)
        self.assertEqual(lookup.call_args.args,(self.destination,'PUBLIC_STAGING_MANIFEST.json'))

    def test_both_original_modes_fail_before_any_private_prompt(self):
        for flag in ['--status','--prepare']:
            with self.subTest(mode=flag), patch.object(workflow,'HELPERS',self.destination/'helpers'), \
                 patch.object(workflow,'hidden',side_effect=AssertionError('must not prompt')):
                stdout=io.StringIO()
                with contextlib.redirect_stdout(stdout):rc=workflow.main([flag])
                self.assertEqual(rc,2)
                self.assertEqual(stdout.getvalue(),'STOP ISSUE=PUBLIC_FILE_MISSING\n')

    def test_minimal_repair_restores_full_original_public_verification(self):
        before=set(p.relative_to(self.destination).as_posix() for p in self.destination.rglob('*') if p.is_file())
        self.assertEqual(self.apply_repair(),'PASS: ROOT_PUBLIC_MANIFEST_INSTALLED')
        after=set(p.relative_to(self.destination).as_posix() for p in self.destination.rglob('*') if p.is_file())
        self.assertEqual(after-before,{repair.MANIFEST})
        self.assertEqual((self.destination/repair.MANIFEST).read_bytes(),self.payload)
        workflow.verify_installation(self.destination)  # Original checks, unchanged.

    def test_changed_source_file_hash_still_fails(self):
        (self.source/'experiment_tools/invented_tool_1.py').write_text('INVENTED CHANGED SOURCE')
        with self.assertRaises(repair.RepairStop):self.apply_repair()
        self.assertFalse((self.destination/repair.MANIFEST).exists())

    def test_changed_destination_tool_fails_without_repair_or_overwrite(self):
        p=self.destination/'experiment_tools/invented_tool_1.py'; p.write_text('INVENTED CONFLICT')
        with self.assertRaises(repair.RepairStop):self.apply_repair()
        self.assertEqual(p.read_text(),'INVENTED CONFLICT')
        self.assertFalse((self.destination/repair.MANIFEST).exists())

    def test_missing_nonmetadata_asset_is_reported_not_copied(self):
        name='experiment_tools/invented_tool_1.py'; (self.destination/name).unlink()
        with self.assertRaises(repair.RepairStop) as exc:self.apply_repair()
        self.assertEqual(exc.exception.code,'REQUIRED_PUBLIC_ASSET_MISSING')
        self.assertEqual(exc.exception.public_file,name)
        self.assertFalse((self.destination/name).exists())
        self.assertFalse((self.destination/repair.MANIFEST).exists())

    def test_unrelated_or_restricted_looking_sentinels_not_opened_or_copied(self):
        # Invented sentinels only; not clinical files or actual private locations.
        secret=self.source/'invented_restricted_do_not_copy.json'; secret.write_text('INVENTED EXCLUDED')
        existing=self.destination/'invented_unrelated.json'; existing.write_text('INVENTED PRESERVE')
        original=repair.read_regular
        def guard(path):
            self.assertNotIn(Path(path),[secret,existing]);return original(path)
        with patch.object(repair,'read_regular',side_effect=guard):self.apply_repair()
        self.assertFalse((self.destination/secret.name).exists())
        self.assertEqual(existing.read_text(),'INVENTED PRESERVE')

    def test_fingerprinted_tree_bytes_modes_and_mtimes_unchanged(self):
        names=[n for n in self.copies if n.startswith('experiment_tools/')]
        before={n:((self.destination/n).read_bytes(),(self.destination/n).stat().st_mode,
            (self.destination/n).stat().st_mtime_ns) for n in names}
        self.apply_repair()
        after={n:((self.destination/n).read_bytes(),(self.destination/n).stat().st_mode,
            (self.destination/n).stat().st_mtime_ns) for n in names}
        self.assertEqual(before,after)

    def test_existing_exact_manifest_is_idempotent_without_metadata_change(self):
        self.apply_repair(); p=self.destination/repair.MANIFEST; os.chmod(p,0o640)
        before=(p.stat().st_mode,p.stat().st_mtime_ns,p.stat().st_ino)
        self.assertEqual(self.apply_repair(),'PASS: ROOT_PUBLIC_MANIFEST_ALREADY_VERIFIED')
        self.assertEqual(before,(p.stat().st_mode,p.stat().st_mtime_ns,p.stat().st_ino))

    def test_conflicting_existing_manifest_never_overwritten(self):
        p=self.destination/repair.MANIFEST;p.write_text('INVENTED WRONG MANIFEST')
        with self.assertRaises(repair.RepairStop):self.apply_repair()
        self.assertEqual(p.read_text(),'INVENTED WRONG MANIFEST')

    def test_new_manifest_0600_root_mode_unchanged_no_temporary_left(self):
        before=self.destination.stat().st_mode
        self.apply_repair()
        self.assertEqual((self.destination/repair.MANIFEST).stat().st_mode & 0o777,0o600)
        self.assertEqual(before,self.destination.stat().st_mode)
        self.assertEqual(list(self.destination.glob('.public-manifest-repair-*.tmp')),[])
        self.assertFalse((self.destination/repair.CHECKSUMS).exists())

    def test_destination_symlink_rejected(self):
        p=self.destination/'experiment_tools/invented_tool_1.py'; q=self.base/'invented_outside.py'
        q.write_bytes(p.read_bytes()); p.unlink(); p.symlink_to(q)
        with self.assertRaises(repair.RepairStop):self.apply_repair()
        self.assertFalse((self.destination/repair.MANIFEST).exists())

    def test_link_race_cannot_overwrite_created_destination(self):
        real_link=os.link
        def race(source,destination,**kwargs):
            Path(destination).write_text('INVENTED CONCURRENT ENTRY')
            return real_link(source,destination,**kwargs)
        with patch.object(repair.os,'link',side_effect=race):
            with self.assertRaises(repair.RepairStop):self.apply_repair()
        self.assertEqual((self.destination/repair.MANIFEST).read_text(),'INVENTED CONCURRENT ENTRY')
        self.assertEqual(list(self.destination.glob('.public-manifest-repair-*.tmp')),[])

    def test_write_failure_keeps_missing_target_and_cleans_temporary(self):
        with patch.object(repair.os,'fsync',side_effect=OSError('INVENTED_NO_ECHO')):
            with self.assertRaises(OSError):self.apply_repair()
        self.assertFalse((self.destination/repair.MANIFEST).exists())
        self.assertEqual(list(self.destination.glob('.public-manifest-repair-*.tmp')),[])

    def test_wrong_root_fails_without_installing_manifest_in_wrong_folder(self):
        wrong=self.base/'invented_wrong_root';wrong.mkdir()
        payload,entries=self.verified()
        with self.assertRaises(repair.RepairStop):repair.repair(self.source,wrong,payload,entries)
        self.assertFalse((wrong/repair.MANIFEST).exists())

    def test_original_guard_remains_active_after_public_repair(self):
        self.apply_repair(); output=io.StringIO()
        with patch.object(workflow,'HELPERS',self.destination/'helpers'), \
             patch.dict(os.environ,{'CODEX_THREAD_ID':'INVENTED_AGENT_MARKER'}), \
             patch.object(workflow,'hidden',side_effect=AssertionError('must not prompt')), \
             contextlib.redirect_stdout(output):
            rc=workflow.main(['--status'])
        self.assertEqual(rc,2)
        self.assertEqual(output.getvalue(),'STOP ISSUE=INDEPENDENT_WORKFLOW_NOT_COMPLETED\n')

    def test_repair_guard_rejects_agent(self):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'INVENTED_AGENT_MARKER'}):
            with self.assertRaises(repair.RepairStop) as exc:repair.require_independent_operator(self.source)
        self.assertEqual(exc.exception.code,'INDEPENDENT_LOCAL_OPERATOR_REQUIRED')

    def test_human_cli_simulation_reports_only_public_statuses(self):
        out=io.StringIO();err=io.StringIO()
        with patch.object(repair,'require_independent_operator') as gate, \
             contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            rc=repair.main(['--staging',str(self.source),'--destination',str(self.destination)])
        gate.assert_called_once_with(self.source)
        self.assertEqual(rc,0);self.assertEqual(err.getvalue(),'')
        self.assertEqual(out.getvalue(),'PASS: ROOT_PUBLIC_MANIFEST_INSTALLED\nPASS: REQUIRED_WORKFLOW_PUBLIC_LAYOUT_VERIFIED\n')
        self.assertNotIn(str(self.base),out.getvalue())

    def test_argument_error_does_not_echo_private_location(self):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            rc=repair.main(['--INVENTED_NO_ECHO',str(self.base)])
        self.assertEqual(rc,2);self.assertEqual(err.getvalue(),'')
        self.assertNotIn(str(self.base),out.getvalue())


if __name__ == '__main__':unittest.main()
