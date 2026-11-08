"""Public package integrity and retained-export verification; no data at import."""
from pathlib import Path
import hashlib
import importlib
import json
import sys
from local_execution import need, sha, descriptor, load_json

ROOT = Path(__file__).resolve().parent
ORIGINAL_ASSIGNMENTS_SHA = '6dfcb3271cff9d0ee122ac4667d5d4fe600334b3927778e0eaa5d6441b3d9866'
ORIGINAL_EXPORTER_SHA = '1f8e3bb08d96b8da1521d994d88a2f855fbe9aa2aaf7ad522163a295b574fdf7'
ORIGINAL_PUBLIC_MAP_SHA = '5a2bd5df394d064224647af2a49bcb804d2bba5a79939b208eb4fcc27f4565e2'
ORIGINAL_WORKFLOW_LEDGER = '46bedc68c743a9a5bf3f6bb51871d494fbec6d8eec877a0de00d4775acb3efce'
ORIGINAL_PUBLIC_MANIFEST = 'bbdf85519801c3e37f82c5e374d8348f1e979b23c762414329089716141a8b46'


def safe_relative(name):
    p = Path(name)
    need(isinstance(name, str) and not p.is_absolute() and '..' not in p.parts
         and '\\' not in name and p.suffix in {'.py','.json','.md','.txt'}, 'PACKAGE_PATH_INVALID')
    return p


def verify_package(root=ROOT):
    inventory = load_json(root/'PUBLIC_PACKAGE_MANIFEST.json')
    need(inventory['schema'] == 'public-label-efficiency-package-v1', 'PACKAGE_MANIFEST_INVALID')
    for name, digest in inventory['files'].items():
        rel = safe_relative(name)
        current = root
        for part in rel.parts:
            current /= part
            need(not current.is_symlink(), 'PACKAGE_SYMLINK_REJECTED')
        need(current.is_file() and sha(current) == digest, 'PACKAGE_HASH_MISMATCH')
    for name, record in load_json(root/'VENDOR_BINDINGS.json').items():
        need(sha(root/safe_relative(name)) == record['sha256'], 'VENDORED_SOURCE_MISMATCH')
    return inventory


def api():
    sys.path.insert(0, str(ROOT/'vendor'))
    module = importlib.import_module('train_exploratory_candidates')
    need(Path(module.__file__).resolve() == (ROOT/'vendor/train_exploratory_candidates.py').resolve(),
         'SCIENTIFIC_HELPER_IMPORT_MISMATCH')
    return module


def protocol_from(config):
    p = descriptor(config['protocol'])
    need(sha(p) == sha(ROOT/'protocol_v1.json'), 'REGISTERED_PROTOCOL_CHANGED')
    protocol = load_json(p)
    need(config['outer_folds'] in [protocol['primary_outer_folds'],protocol['registered_extension_outer_folds']],
         'UNREGISTERED_FOLD_DESIGN')
    need(config['no_locked_test'] is True and config['no_prior_validation_outcomes'] is True,
         'FOLLOWUP_BOUNDARY_INVALID')
    return protocol


def validate_selected_arrays(data, target_validation_ids, t, synthetic=False):
    import numpy as np
    all_ids = []
    for role in ['source_train','source_validation','target_pool']:
        y = data[role+'__y']; ids = data[role+'__ids']
        expected_n, expected_e = (len(y),int(y.sum())) if synthetic else t.COUNTS[role]
        need(ids.dtype.kind == 'U' and ids.shape == (expected_n,) and len(set(ids.tolist())) == expected_n,
             'FOLLOWUP_ID_INVALID')
        need(y.shape == (expected_n,) and np.isin(y,[0,1]).all() and int(y.sum()) == expected_e,
             'FOLLOWUP_LABEL_INVALID')
        all_ids += ids.tolist()
        for view, dim in t.VIEWS.items():
            x = data[role+'__'+view]
            need(x.shape == (expected_n,dim) and np.isfinite(x).all(), 'FOLLOWUP_FEATURE_INVALID')
    need(len(all_ids) == len(set(all_ids)), 'FOLLOWUP_ROLE_OVERLAP')
    need(target_validation_ids.dtype.kind == 'U' and target_validation_ids.ndim == 1
         and len(set(target_validation_ids.tolist())) == len(target_validation_ids)
         and not set(all_ids) & set(target_validation_ids.tolist()), 'PREVIOUS_VALIDATION_OVERLAP')
    if not synthetic: need(len(target_validation_ids) == 171, 'PREVIOUS_VALIDATION_ID_COUNT_INVALID')


def load_retained_export(config):
    """Only retained export artifacts. Never opens datasets or original assignments."""
    import numpy as np
    t = api(); inputs = config['inputs']
    manifest = load_json(descriptor(inputs['development_manifest']))
    receipt = load_json(descriptor(inputs['completed_workflow_receipt']))
    pp_path = descriptor(inputs['source_preprocessing'])
    bundle_path = descriptor(inputs['development_bundle'])
    need(receipt['status'] == 'COMPLETED_PRIVATE_DISCLOSURE_REVIEW_REQUIRED'
         and receipt['attempt_consumed'] is True and receipt['stage'] == 'NONE' and receipt['issue'] == 'NONE'
         and receipt['real_test_evaluation'] is False
         and receipt['export_manifest_sha256'] == inputs['development_manifest']['sha256']
         and receipt['bindings']['public_manifest_sha256'] == ORIGINAL_PUBLIC_MANIFEST
         and receipt['bindings']['helper_ledger_sha256'] == ORIGINAL_WORKFLOW_LEDGER,
         'PRIOR_COMPLETED_WORKFLOW_BINDING_INVALID')
    canonical = json.dumps(manifest['public_source_bindings'], sort_keys=True, separators=(',',':'),ensure_ascii=True).encode('ascii')
    need(hashlib.sha256(canonical).hexdigest() == ORIGINAL_PUBLIC_MAP_SHA
         and manifest['source_assignments_sha256'] == ORIGINAL_ASSIGNMENTS_SHA
         and manifest['preparation_script_sha256'] == ORIGINAL_EXPORTER_SHA
         and manifest['bundle_sha256'] == inputs['development_bundle']['sha256']
         and manifest['preprocessor_sha256'] == inputs['source_preprocessing']['sha256']
         and manifest['preprocessing_fit_role'] == 'source_train'
         and manifest['protocol'] == 'public-haalsi-mhas-v2' and manifest['test_rows_included'] is False,
         'RETAINED_EXPORT_PROVENANCE_INVALID')
    pp = load_json(pp_path)
    need(pp['fit_role'] == 'source_train' and pp['schema_version'] == 'cvd-public-wave-v2-ten-doctor-report',
         'SOURCE_PREPROCESSOR_BINDING_INVALID')
    expected = {role+'__'+field for role in t.ROLES for field in ['ids','y',*t.VIEWS]}
    expected |= {f'draw_{i}' for i in range(10)}
    with np.load(bundle_path, allow_pickle=False) as z:
        need(len(z.files) == 38 and set(z.files) == expected, 'EXTRA_OR_MISSING_BUNDLE_ARRAY')
        data = {role+'__'+field:z[role+'__'+field].copy()
                for role in ['source_train','source_validation','target_pool'] for field in ['ids','y',*t.VIEWS]}
        # Read membership only; never decode old validation features/outcomes.
        val_ids = z['target_validation__ids'].copy()
        old_draws = [z[f'draw_{i}'].copy() for i in range(10)]
    validate_selected_arrays(data,val_ids,t)
    historical_fit_indices = set()
    for ix in old_draws:
        need(ix.ndim == 1 and ix.dtype.kind in 'iu' and len(set(ix.tolist())) == 100
             and (ix >= 0).all() and (ix < 679).all()
             and int(data['target_pool__y'][ix].sum()) == 25, 'PRIOR_DRAW_CONTRACT_INVALID')
        historical_fit_indices.update(ix.tolist())
    history = {'previous_adaptation_fit_union_n':len(historical_fit_indices),
               'previous_model_selection_validation_n':len(val_ids),
               'original_label_informed_adaptation_pool_n':len(data['target_pool__y']),
               'previous_target_development_labels_available':len(val_ids)+len(data['target_pool__y']),
               'incremental_budget_is_not_total_historical_label_cost':True,
               'prior_validation_outcomes_decoded':False,'original_assignments_reopened':False}
    need(sha(bundle_path)==inputs['development_bundle']['sha256'] and sha(pp_path)==inputs['source_preprocessing']['sha256'],
         'INPUT_CHANGED_DURING_READ')
    return data,history
