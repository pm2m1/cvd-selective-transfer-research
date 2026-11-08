"""Allowlisted PUBLIC evidence imports only. No restricted input interfaces."""
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent


def verify_frozen():
    ledger = json.loads((ROOT / 'FROZEN_PUBLIC_BINDINGS.json').read_text())
    base = ROOT.parent / ledger['root_relative_to_results']
    for name, expected in ledger['files'].items():
        p = base / name
        if p.is_symlink() or not p.resolve().is_relative_to(base.resolve()) or not p.is_file():
            raise ValueError('PUBLIC_EVIDENCE_MISSING_OR_UNSAFE')
        if hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            raise ValueError('PUBLIC_EVIDENCE_CHANGED')
    return base


def references():
    base = verify_frozen()
    sys.path.insert(0, str(base))
    engine = importlib.import_module('count_engine')
    fixture = importlib.import_module('synthetic_fixture')
    if Path(engine.__file__).resolve() != (base / 'count_engine.py').resolve():
        raise ValueError('UNEXPECTED_PUBLIC_ENGINE_IMPORT')
    if Path(fixture.__file__).resolve() != (base / 'synthetic_fixture.py').resolve():
        raise ValueError('UNEXPECTED_PUBLIC_FIXTURE_IMPORT')
    mapping = json.loads((base / 'official_variable_map.json').read_text())
    protocol = json.loads((base / 'PROTOCOL.json').read_text())
    spec = importlib.util.spec_from_file_location('elsa_observability_proposal',
                ROOT / 'proposal/count_engine_observability_v1.py')
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    return engine, fixture, mapping, protocol, candidate
