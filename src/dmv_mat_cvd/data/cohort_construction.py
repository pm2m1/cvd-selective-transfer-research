"""Pre-model eligibility/endpoint construction and auditable readiness gates."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np
import pandas as pd

from .base import CohortTable
from .endpoint import EventMetadata, build_endpoint
from .mapping import BASELINE_FIELDS, PREDICTORS, TIME_FIELDS, harmonize, validate_mapping
from .releases import digest_json, validate_manifest
from .schema import CATEGORIES

SPECIAL = ('fatal_mi', 'fatal_stroke', 'tia', 'silent_ecg_only_mi', 'fatal_chd_not_definite_mi',
           'competing_nonqualifying_death')


def validate_crosswalk(config: dict | None) -> dict:
    errors = []
    if not isinstance(config, dict):
        return {'valid': False, 'errors': ['An explicit endpoint crosswalk is required']}
    if config.get('verified') is not True or not config.get('version') or not config.get('documentation_reference'):
        errors.append('Crosswalk version, verification and documentation reference required')
    if config.get('missing_event_category') not in {'no_record', 'unresolved'}:
        errors.append('Explicit handling of missing event categories required')
    if config.get('missing_event_category') == 'unresolved':
        errors.append('Missing event handling remains unresolved')
    rules = config.get('special_rules', {})
    for name in SPECIAL:
        rule = rules.get(name, {})
        allowed = {'qualifying_mi'} if name == 'fatal_mi' else {'qualifying_stroke'} if name == 'fatal_stroke' else {'nonqualifying'}
        if rule.get('action') not in allowed or not rule.get('documentation'):
            errors.append(f'{name}: explicit reviewed handling required')
        if name.startswith('fatal_') and name in {'fatal_mi', 'fatal_stroke'}:
            if rule.get('time_source') not in {'death_time', 'mi_event_time' if name == 'fatal_mi' else 'stroke_event_time'}:
                errors.append(f'{name}: explicit fatal event time source required')
    for stream in ('mi', 'stroke', 'death'):
        entries = config.get(stream + '_categories')
        if not isinstance(entries, list) or not entries:
            errors.append(f'{stream}: explicit category crosswalk required')
            continue
        valid_actions = ({'qualifying_mi', 'nonqualifying', 'none', 'fatal_mi', 'silent_ecg_only_mi'} if stream == 'mi'
                         else {'qualifying_stroke', 'nonqualifying', 'none', 'fatal_stroke', 'tia'} if stream == 'stroke'
                         else {'fatal_mi', 'fatal_stroke', 'fatal_chd_not_definite_mi', 'competing_nonqualifying_death', 'none'})
        seen = []
        for item in entries:
            if (not isinstance(item, dict) or 'raw' not in item or item['raw'] is None
                    or item.get('classification') not in valid_actions or item['raw'] in seen):
                errors.append(f'{stream}: unknown, duplicate or unresolved crosswalk declaration')
                break
            seen.append(item['raw'])
    return {'valid': not errors, 'errors': errors, 'crosswalk_hash': digest_json(config)}


class EndpointCrosswalkError(ValueError):
    pass


def classify(value, stream: str, config: dict) -> str:
    if pd.isna(value):
        if stream != 'death' and config['missing_event_category'] == 'no_record':
            return 'none'
        return 'none'  # A death time without cause is rejected in row_endpoint.
    for item in config[stream + '_categories']:
        if value == item['raw']:
            return item['classification']
    raise EndpointCrosswalkError(f'Unmapped {stream} endpoint category; observed values omitted')


def row_endpoint(row: pd.Series, crosswalk: dict):
    def time(name):
        value = row[name]
        return None if pd.isna(value) else float(value)
    death, followup = time('death_time'), time('last_followup_time')
    all_times = [time(name) for name in TIME_FIELDS]
    if any(v is not None and (not np.isfinite(v) or v < 0) for v in all_times):
        raise ValueError('Invalid event chronology')
    candidates = []
    for stream in ('mi', 'stroke'):
        category = classify(row[stream + '_event_type'], stream, crosswalk)
        when = time(stream + '_event_time')
        fatal = category in {'fatal_mi', 'fatal_stroke'}
        if not fatal and (category == 'none') != (when is None):
            raise ValueError('Event category/time mismatch')
        if when is not None and (when == 0 or death is not None and when > death):
            raise ValueError('Event is at index or after death')
        action = crosswalk['special_rules'][category]['action'] if category in SPECIAL else category
        if action in {'qualifying_mi', 'qualifying_stroke'}:
            if fatal:
                when = time(crosswalk['special_rules'][category]['time_source'])
                if death is None or when is None:
                    raise ValueError('Fatal event without verified death/event chronology')
            candidates.append((when, 'mi' if action == 'qualifying_mi' else 'stroke'))
    cause = classify(row.death_cause, 'death', crosswalk)
    if (cause == 'none') != (death is None):
        raise EndpointCrosswalkError('Death chronology/cause incomplete; cannot certify endpoint readiness')
    nonqualifying = False
    if death is not None:
        rule = crosswalk['special_rules'][cause]
        if rule['action'] in {'qualifying_mi', 'qualifying_stroke'}:
            when = time(rule['time_source'])
            if when is None:
                raise ValueError('Fatal event time unavailable')
            candidates.append((when, 'mi' if rule['action'] == 'qualifying_mi' else 'stroke'))
        else:
            nonqualifying = True
    first_time, event_type = min(candidates) if candidates else (None, None)
    metadata = EventMetadata(event_type, first_time, death, followup, nonqualifying)
    return build_endpoint(metadata), metadata


def cohort_digest(cohort: CohortTable) -> str:
    """One aggregate content fingerprint; never emits per-person hashes/records."""
    h = hashlib.sha256()
    h.update(digest_json({'domain': cohort.domain, 'schema': cohort.schema_version,
                          'columns': list(cohort.records.columns)}).encode())
    h.update(pd.util.hash_pandas_object(cohort.records, index=False).to_numpy().tobytes())
    return h.hexdigest()


@dataclass
class ConstructionResult:
    cohort: CohortTable | None
    report: dict


def readiness_text(report: dict) -> str:
    lines = ['COHORT_READY = ' + ('YES' if report['ready'] else 'NO')]
    for name, value in report['gates'].items():
        lines.append(f"[{'x' if value else ' '}] {name}")
    lines += [f'{name}: {value}' for name, value in report.get('counts', {}).items()]
    lines += ['ERROR: ' + error for error in report.get('errors', [])]
    return '\n'.join(lines) + '\n'


def construct_cohort(raw: pd.DataFrame, mapping: dict, crosswalk: dict | None, *,
                     domain: str, manifest: dict | None = None, release_directory=None,
                     policy: dict | None = None, access_phase: str = 'pre_split') -> ConstructionResult:
    """Dry-run assembly only. Does not impute, standardize, select or train.

    Exclusions are sequential and disjoint; missing individual predictors remain
    for the existing training-only imputation. Explicit policy thresholds are a
    readiness convention, not a clinical sample-size or statistical-power claim.
    """
    mapping_audit = validate_mapping(mapping, raw.columns)
    crosswalk_audit = validate_crosswalk(crosswalk)
    release = validate_manifest(manifest or {}, release_directory)
    available = mapping_audit.get('available', {})
    gates = {
        'release_manifest_complete': release['valid'] and release['files_verified'],
        'mandatory_predictor_mappings_valid': mapping_audit['valid'] and all(available.get(k) for k in PREDICTORS),
        'units_validated': mapping_audit.get('units_valid', False),
        'category_mappings_validated': mapping_audit.get('categories_valid', False),
        'baseline_exclusions_mapped': all(available.get(k) for k in BASELINE_FIELDS),
        'endpoint_crosswalk_validated': crosswalk_audit['valid'],
        'event_chronology_available': all(available.get(k) for k in ('index_date', 'mi_event_type', 'stroke_event_type', 'death_cause', *TIME_FIELDS)),
        'last_followup_censoring_available': available.get('last_followup_time', False),
        'sufficient_five_year_followup': False,
        'participant_ids_unique_understood': False,
        'no_forbidden_target_test_preprocessing': access_phase == 'pre_split',
    }
    report = {'report_version': 'cohort-readiness-v1', 'cohort_name': domain, 'ready': False, 'gates': gates,
              'mapping_audit': mapping_audit, 'crosswalk_audit': crosswalk_audit, 'release_audit': release,
              'policy': policy, 'access_phase': access_phase, 'pipeline_stages': ['mapping', 'eligibility', 'endpoint_construction'],
              'statistical_preprocessing_performed': False, 'training_performed': False,
              'errors': [*mapping_audit['errors'], *crosswalk_audit['errors'], *release['errors']],
              'counts': {**dict.fromkeys(('initial_participant_count', 'index_exam_attendees', 'prior_mi_exclusions',
                    'prior_stroke_exclusions', 'invalid_chronology_exclusions', 'missing_index_date',
                    'missing_mandatory_predictors', 'followup_available', 'qualifying_events_within_1826',
                    'competing_deaths_before_1826', 'known_event_free_through_1826', 'early_unknown_lost_followup',
                    'final_eligible_n', 'final_observed_binary_n', 'final_endpoint_count', 'endpoint_prevalence')),
                    'initial_rows': len(raw)}}
    if manifest and manifest.get('cohort_name') != domain:
        gates['release_manifest_complete'] = False
        report['errors'].append('Release manifest cohort does not match adapter domain')
    if manifest and mapping.get('release_version') != manifest.get('release_version'):
        gates['mandatory_predictor_mappings_valid'] = False
        report['errors'].append('Mapping release version does not match manifest')
    if mapping.get('cohort_name') != domain:
        gates['mandatory_predictor_mappings_valid'] = False
        report['errors'].append('Mapping cohort does not match adapter domain')
    if not mapping_audit['valid'] or not crosswalk_audit['valid']:
        return ConstructionResult(None, report)
    try:
        frame, _ = harmonize(raw, mapping)
    except ValueError as exc:
        gates['category_mappings_validated'] = False
        report['errors'].append(str(exc))
        return ConstructionResult(None, report)
    ids = frame.participant_id
    report['counts'].update(initial_participant_count=int(ids.dropna().astype(str).nunique()),
                            missing_participant_ids=int(ids.isna().sum()),
                            duplicate_participant_id_excess=int(ids.dropna().astype(str).duplicated().sum()))
    gates['participant_ids_unique_understood'] = bool(ids.notna().all() and ids.astype(str).str.strip().ne('').all() and ids.astype(str).is_unique)
    if not gates['participant_ids_unique_understood']:
        report['errors'].append('Resolve missing/duplicate participant IDs before constructing a baseline cohort')
        return ConstructionResult(None, report)
    # Fail closed on *all* observed release categories, even in excluded rows.
    try:
        for stream, column in (('mi', 'mi_event_type'), ('stroke', 'stroke_event_type'), ('death', 'death_cause')):
            for value in frame[column].dropna().unique():
                classify(value, stream, crosswalk)
    except EndpointCrosswalkError as exc:
        gates['endpoint_crosswalk_validated'] = False
        report['errors'].append(str(exc))
        return ConstructionResult(None, report)
    remaining = frame.copy()
    counts = report['counts']
    def exclude(name, mask):
        nonlocal remaining
        mask = mask.fillna(False)
        counts[name] = int(mask.sum())
        remaining = remaining.loc[~mask].copy()
    counts['index_exam_attendees'] = int(frame.index_attendee.eq(True).sum())
    exclude('nonattendee_exclusions', remaining.index_attendee.eq(False))
    exclude('unknown_attendance_exclusions', remaining.index_attendee.isna())
    exclude('prior_mi_exclusions', remaining.prior_mi.eq(True))
    exclude('prior_stroke_exclusions', remaining.prior_stroke.eq(True))
    exclude('unknown_baseline_history_exclusions', remaining.prior_mi.isna() | remaining.prior_stroke.isna())
    exclude('missing_index_date', remaining.index_date.isna())
    def missing_predictors(data):
        return pd.DataFrame({k: data[k].isna() | (data[k].eq('unknown').fillna(False) if k in CATEGORIES else False)
                             for k in PREDICTORS})
    missing = missing_predictors(remaining)
    counts['missing_mandatory_predictors'] = int(missing.any(axis=1).sum())
    counts['missing_predictors_by_field'] = {k: int(missing[k].sum()) for k in PREDICTORS}
    counts['followup_available'] = int(remaining.last_followup_time.notna().sum())
    constructed, invalid, incomplete = [], 0, 0
    for _, row in remaining.iterrows():
        try:
            endpoint, meta = row_endpoint(row, crosswalk)
        except EndpointCrosswalkError:
            incomplete += 1
            continue
        except ValueError:
            invalid += 1
            continue
        item = {name: row[name] for name in ('participant_id', 'index_date', *PREDICTORS)}
        item.update(event_type=meta.event_type, event_time_days=meta.event_time_days, death_time_days=meta.death_time_days,
                    last_followup_days=meta.last_followup_days, death_is_nonqualifying=meta.death_is_nonqualifying,
                    endpoint_status=endpoint.status.value, label=endpoint.label)
        constructed.append(item)
    counts['invalid_chronology_exclusions'] = invalid
    counts['incomplete_endpoint_exclusions'] = incomplete
    if incomplete:
        gates['endpoint_crosswalk_validated'] = False
        report['errors'].append('Incomplete death ascertainment; endpoint crosswalk gate remains closed')
    if not constructed:
        counts.update(final_eligible_n=0, final_observed_binary_n=0, final_endpoint_count=0,
                      qualifying_events_within_1826=0, known_event_free_through_1826=0,
                      competing_deaths_before_1826=0, early_unknown_lost_followup=0, excluded_total=len(frame))
        report['errors'].append('No eligible records after construction')
        return ConstructionResult(None, report)
    canonical = pd.DataFrame(constructed)
    canonical['label'] = pd.array(canonical.label, dtype='Int64')
    cohort = CohortTable(canonical, domain)
    states = canonical.endpoint_status.value_counts()
    counts.update(final_eligible_n=len(canonical), final_observed_binary_n=int(canonical.label.notna().sum()),
                  qualifying_events_within_1826=int(states.get('positive', 0)),
                  competing_deaths_before_1826=int(states.get('competing_death', 0)),
                  known_event_free_through_1826=int(states.get('known_negative', 0)),
                  early_unknown_lost_followup=int(states.get('unknown', 0)),
                  final_endpoint_count=int(states.get('positive', 0)),
                  endpoint_prevalence=float(canonical.label.dropna().mean()) if canonical.label.notna().any() else None)
    counts['excluded_total'] = len(frame) - len(canonical)
    # Mapping available does not imply actual observations exist.
    gates['mandatory_predictor_mappings_valid'] &= bool((~missing_predictors(canonical)).any().all())
    gates['last_followup_censoring_available'] &= bool(canonical.last_followup_days.notna().any())
    policy_valid = (isinstance(policy, dict) and policy.get('missing_predictor_policy') == 'retain_for_train_only_imputation'
                    and type(policy.get('minimum_known_outcomes')) is int and policy['minimum_known_outcomes'] >= 1
                    and type(policy.get('minimum_event_free_horizon')) is int and policy['minimum_event_free_horizon'] >= 1
                    and isinstance(policy.get('minimum_ascertained_fraction'), (int, float)) and 0 <= policy['minimum_ascertained_fraction'] <= 1)
    gates['sufficient_five_year_followup'] = bool(policy_valid
        and counts['final_observed_binary_n'] >= policy['minimum_known_outcomes']
        and counts['known_event_free_through_1826'] >= policy['minimum_event_free_horizon']
        and counts['final_observed_binary_n'] / len(canonical) >= policy['minimum_ascertained_fraction'])
    if not policy_valid:
        report['errors'].append('Explicit follow-up readiness thresholds and missing-predictor policy required')
    report.update(ready=all(gates.values()), cohort_digest=cohort_digest(cohort),
                  mapping_hash=digest_json(mapping), crosswalk_hash=digest_json(crosswalk),
                  manifest_hash=digest_json(manifest or {}),
                  provenance_note='Readiness is an engineering gate under declared thresholds, not clinical feasibility or power.')
    cohort.onboarding = report
    return ConstructionResult(cohort, report)
