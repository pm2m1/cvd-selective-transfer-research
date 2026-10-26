"""Optional reproducibility lock. Provenance checks, not an access-control system."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .data.cohort_construction import cohort_digest
from .data.releases import digest_json, load_json, validate_manifest
from .method import METHOD_SPEC_VERSION, PRIMARY_SELECTOR, REQUIRED_COMPARATORS, SELECTOR_VERSIONS
from .data.schema import SCHEMA_VERSION
from .transfer.calibration import CalibrationConfig


def validate_locked_config(cfg) -> None:
    if not cfg.publication_mode:
        return
    if cfg.method_spec_version != METHOD_SPEC_VERSION or cfg.schema_version != SCHEMA_VERSION or cfg.selector_policy is None:
        raise ValueError('Locked mode requires explicit supported method_spec_version, schema_version and selector_policy')
    if cfg.selector_policy not in SELECTOR_VERSIONS:
        raise ValueError('Unknown frozen selector')
    if cfg.analysis_role not in {'confirmatory', 'secondary', 'selector_ablation'}:
        raise ValueError('Declare confirmatory, secondary or selector_ablation analysis role')
    if cfg.analysis_role != 'selector_ablation' and cfg.selector_policy != PRIMARY_SELECTOR:
        raise ValueError('Primary/secondary method-v1 experiments require calibrated_logical; label selector ablations explicitly')
    if set(REQUIRED_COMPARATORS) - set(cfg.modes):
        raise ValueError('Locked method-v1 runs must include all required transfer comparators')
    if cfg.target_event_budget not in {10, 25, 50, 100}:
        raise ValueError('Locked runs require a declared method-v1 event budget')
    if cfg.analysis_role == 'confirmatory' and cfg.target_event_budget != 50:
        raise ValueError('Confirmatory comparison requires 50 target events, subject to feasibility')
    if (cfg.calibration != CalibrationConfig() or cfg.view_hidden != 16 or cfg.selector_scope != 'all'
            or cfg.discrepancy_weight != .65 or cfg.adapt_fraction != .5 or not cfg.mmd_normalize
            or cfg.mmd_max_samples != 128 or cfg.random_budget_tolerance != .005
            or tuple(cfg.fixed_mask) != ('fusion1', 'fusion2') or cfg.preprocessing_policy != 'source_fitted'):
        raise ValueError('Locked method-v1 selector/model settings differ from the frozen method; use an explicitly nonpublication experiment')
    if not isinstance(cfg.cohort_inputs, dict) or set(cfg.cohort_inputs) != {'source', 'target'}:
        raise ValueError('Locked mode requires explicit source and target cohort_inputs')
    for role, name in (('source', 'ARIC Visit 1'), ('target', 'MESA Exam 1')):
        item = cfg.cohort_inputs[role]
        required = ('cohort_name', 'mapping_config', 'endpoint_crosswalk', 'release_manifest', 'release_directory')
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k] for k in required):
            raise ValueError('Cohort inputs must explicitly identify cohort, mapping, crosswalk, manifest and release directory')
        if item['cohort_name'] != name:
            raise ValueError('Locked method-v1 uses ARIC Visit 1 source and MESA Exam 1 target')


def prepare_publication(source, target, cfg):
    """Check readiness against the actual table/configs; snapshot before training."""
    if not cfg.publication_mode:
        return None
    validate_locked_config(cfg)
    evidence, assets, not_ready = {}, {}, []
    for role, cohort in (('source', source), ('target', target)):
        item = cfg.cohort_inputs[role]
        if cohort.domain != item['cohort_name']:
            raise ValueError('Configured cohort does not match supplied canonical table')
        documents = {name: load_json(item[name]) for name in ('mapping_config', 'endpoint_crosswalk', 'release_manifest')}
        if (documents['mapping_config'].get('cohort_name') != cohort.domain
                or documents['release_manifest'].get('cohort_name') != cohort.domain
                or documents['mapping_config'].get('release_version') != documents['release_manifest'].get('release_version')):
            raise ValueError('Mapping and manifest must describe the same configured cohort release')
        release = validate_manifest(documents['release_manifest'], item['release_directory'])
        if not release['valid']:
            raise ValueError('Release manifest validation failed before modeling')
        report = cohort.onboarding
        if not isinstance(report, dict) or report.get('cohort_digest') != cohort_digest(cohort):
            raise ValueError('Canonical cohort lacks current, content-bound onboarding evidence')
        for field, document in (('mapping_hash', 'mapping_config'), ('crosswalk_hash', 'endpoint_crosswalk'), ('manifest_hash', 'release_manifest')):
            if report.get(field) != digest_json(documents[document]):
                raise ValueError('Onboarding evidence does not match the declared release/mapping/crosswalk')
        if report.get('access_phase') != 'pre_split' or report.get('statistical_preprocessing_performed') is not False:
            raise ValueError('Forbidden test exposure or cohort-wide statistical preprocessing cannot be overridden')
        if not report.get('mapping_audit', {}).get('valid') or not report.get('crosswalk_audit', {}).get('valid'):
            raise ValueError('Invalid mandatory mapping or endpoint crosswalk cannot be overridden')
        if not report.get('ready') or not all(report.get('gates', {}).values()):
            not_ready.append(role)
        assets[role] = documents
        evidence[role] = report
    if not_ready and not cfg.exploratory_override:
        raise ValueError('COHORT_READY = NO; publication execution blocked. An explicit exploratory_override is required for exploratory execution')
    experiment_id = f'{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}'
    output = Path(cfg.output_dir) / experiment_id
    output.mkdir(parents=True, exist_ok=False)
    snapshot = {'configuration': asdict(cfg), 'method_spec_version': cfg.method_spec_version,
                'schema_version': cfg.schema_version, 'selector_name': cfg.selector_policy,
                'selector_version': SELECTOR_VERSIONS[cfg.selector_policy],
                'cohort_documents': assets, 'readiness': evidence,
                'release_manifest_hashes': {role: digest_json(values['release_manifest']) for role, values in assets.items()},
                'mapping_hashes': {role: digest_json(values['mapping_config']) for role, values in assets.items()},
                'seed': cfg.seed, 'exploratory_override': cfg.exploratory_override,
                'readiness_overridden_roles': not_ready,
                'synthetic_fixture': any(values['release_manifest'].get('synthetic_fixture') is True for values in assets.values()),
                'snapshot_stage': 'before_splitting_and_training'}
    snapshot['eligible_for_clinical_reporting'] = not not_ready and not snapshot['synthetic_fixture'] and not cfg.exploratory_override
    snapshot['configuration_digest'] = digest_json(snapshot)
    (output / 'locked_configuration.json').write_text(json.dumps(snapshot, indent=2, allow_nan=False) + '\n')
    return {'experiment_id': experiment_id, 'output': output, 'snapshot': snapshot}


def bind_target_test(lock, partition):
    if lock is None:
        return None
    binding = {'split_role': 'target_test', 'cohort_digest': cohort_digest(partition.cohort),
               'participant_count': len(partition.participant_ids), 'seed': lock['snapshot']['seed'],
               'configuration_digest': lock['snapshot']['configuration_digest'],
               'policy': 'immutable within run; no participant identifiers emitted'}
    (lock['output'] / 'locked_target_test.json').write_text(json.dumps(binding, indent=2) + '\n')
    return binding


def verify_target_test(binding, partition):
    if binding is not None and (getattr(partition.role, 'value', None) != 'target_test' or binding['cohort_digest'] != cohort_digest(partition.cohort)):
        raise ValueError('Locked target-test partition changed within the run')


def verify_configuration(lock, cfg):
    if lock is not None and digest_json(lock['snapshot']['configuration']) != digest_json(asdict(cfg)):
        raise ValueError('Locked configuration changed within the run')
