"""New package/config bindings; retained-export verification is copied unchanged."""
from pathlib import Path
import importlib.metadata
import json
import platform
from local_execution import need,load_json,sha,descriptor
ROOT=Path(__file__).resolve().parent
PACKAGES=['numpy','pandas','torch','scikit-learn','scipy','matplotlib','joblib']


def runtime():
    return {'python':platform.python_version(),**{p:importlib.metadata.version(p) for p in PACKAGES}}


def relative(name):
    need(isinstance(name,str) and bool(name),'INVALID_PUBLIC_PACKAGE_PATH')
    p=Path(name)
    need(not p.is_absolute() and '..' not in p.parts and '\\' not in name and p.suffix in ['.py','.json','.md','.txt'],
         'INVALID_PUBLIC_PACKAGE_PATH')
    return p


def verified_file(root,name,digest):
    p=root
    for part in relative(name).parts:
        p=p/part;need(not p.is_symlink(),'PUBLIC_PACKAGE_SYMLINK_REJECTED')
    need(p.is_file() and sha(p)==digest,'PUBLIC_PACKAGE_FILE_MISMATCH')
    return p


def verify_package(root=ROOT):
    manifest=load_json(root/'PUBLIC_PACKAGE_MANIFEST.json')
    need(manifest['schema']=='epoch-zero-public-package-v1','PUBLIC_PACKAGE_SCHEMA_INVALID')
    for name,digest in manifest['files'].items():verified_file(root,name,digest)
    immutable=load_json(root/'IMMUTABLE_DEPENDENCIES.json')
    for name,record in immutable.items():verified_file(root,name,record['sha256'])
    return manifest


def reviewed_protocol(config):
    need(set(config)=={'schema','mode','protocol','package_manifest_sha256','runtime_versions',
                      'no_locked_test','no_prior_validation_outcomes','inputs'},'LOCAL_CONFIG_FIELDS_INVALID')
    need(config['schema']=='epoch-zero-local-v1' and config['mode']=='independent_local_only'
         and config['no_locked_test'] is True and config['no_prior_validation_outcomes'] is True,
         'LOCAL_CONFIG_BOUNDARY_INVALID')
    need(set(config['inputs'])=={'development_manifest','completed_workflow_receipt',
                                'source_preprocessing','development_bundle'},'RETAINED_INPUT_FIELDS_INVALID')
    need(config['package_manifest_sha256']==sha(ROOT/'PUBLIC_PACKAGE_MANIFEST.json'),'REVIEWED_PACKAGE_BINDING_MISMATCH')
    need(config['runtime_versions']==runtime(),'REVIEWED_RUNTIME_MISMATCH')
    p=descriptor(config['protocol'])
    need(sha(p)==sha(ROOT/'EXPERIMENT_CONFIG.json'),'EXPERIMENT_PROTOCOL_CHANGED')
    return load_json(p)
