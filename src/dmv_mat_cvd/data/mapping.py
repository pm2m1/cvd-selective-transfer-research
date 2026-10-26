"""Explicit, release-supplied field declarations and small transform hooks."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from .releases import digest_json, load_json
from .schema import CANONICAL_UNITS, CATEGORIES, CONTINUOUS, PREDICTORS

BASELINE_FIELDS = ('index_attendee', 'prior_mi', 'prior_stroke')
TIME_FIELDS = ('mi_event_time', 'stroke_event_time', 'death_time', 'last_followup_time')
EVENT_FIELDS = ('mi_event_type', 'stroke_event_type', 'death_cause', *TIME_FIELDS)
TARGETS = ('participant_id', 'index_date', *PREDICTORS, *BASELINE_FIELDS, *EVENT_FIELDS)


def field_role(target: str) -> str:
    return 'predictor' if target in PREDICTORS else 'eligibility' if target in BASELINE_FIELDS else 'identifier' if target == 'participant_id' else 'endpoint'


def mapping_config(value: dict | str | Path) -> dict:
    return load_json(value) if isinstance(value, (str, Path)) else value


def validate_mapping(config: dict, raw_columns) -> dict:
    errors, warnings, checks = [], [], []
    for key in ('mapping_version', 'release_version', 'documentation_reference', 'cohort_name'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            errors.append(f'{key}: explicit mapping provenance required')
    columns = list(raw_columns)
    if len(set(columns)) != len(columns):
        errors.append('Raw column names are duplicated')
    fields = config.get('fields')
    if not isinstance(fields, list) or any(not isinstance(f, dict) for f in fields):
        return {'valid': False, 'errors': ['fields must be a list of declarations'], 'warnings': [], 'checks': [], 'available': {}}
    names = [f.get('canonical') for f in fields]
    if len(set(names)) != len(names):
        errors.append('Canonical field mapped twice')
    if set(names) != set(TARGETS):
        errors.append('Every required canonical field must be declared exactly once, or explicitly marked missing')
    used, available = {}, {}
    unit_ok, category_ok = True, True
    for f in fields:
        target = f.get('canonical')
        if target not in TARGETS:
            errors.append('Unsupported canonical target')
            continue
        before = len(errors)
        if f.get('status') not in {'mapped', 'missing'}:
            errors.append(f'{target}: mapping status remains unresolved')
        if f.get('role') != field_role(target):
            errors.append(f'{target}: predictor/endpoint/eligibility separation violated')
        if f.get('status') == 'missing':
            available[target] = False
            if not isinstance(f.get('reason'), str) or not f['reason'].strip():
                errors.append(f'{target}: explicit missing reason required')
            if f.get('raw'):
                errors.append(f'{target}: missing field cannot also have a raw mapping')
            warnings.append(f'{target}: explicitly unavailable; readiness will fail for required fields')
            checks.append({'canonical': target, 'status': 'explicitly_missing'})
            continue
        raw = f.get('raw')
        available[target] = bool(raw and raw in columns)
        if not isinstance(raw, str) or not raw or raw.startswith('TODO') or raw not in columns:
            errors.append(f'{target}: mapped raw column is missing or unresolved')
        if raw and raw in used:
            errors.append(f'{target}: raw column reused by another canonical field')
        if raw:
            used[raw] = target
        if target in PREDICTORS:
            timing = f.get('timing')
            end = f.get('measurement_window_end_days')
            availability = f.get('available_at_days')
            if (timing != 'baseline' or not isinstance(end, (int, float)) or not math.isfinite(end) or end > 0
                    or not isinstance(availability, (int, float)) or not math.isfinite(availability) or availability > 0):
                errors.append(f'{target}: explicit baseline measurement and availability at/before index required')
        transform = f.get('transform', {})
        kind = transform.get('kind')
        if target in CONTINUOUS:
            output = transform.get('output_unit')
            valid_unit = (kind == 'already_canonical' and transform.get('input_unit') == CANONICAL_UNITS[target]
                          or kind == 'linear' and isinstance(transform.get('input_unit'), str) and bool(transform['input_unit'])
                          and all(isinstance(transform.get(k), (int, float)) and math.isfinite(transform[k]) for k in ('scale', 'offset'))
                          and transform['scale'] > 0)
            if not valid_unit or output != CANONICAL_UNITS[target]:
                errors.append(f'{target}: explicit canonical units or finite linear conversion required')
                unit_ok = False
        elif target in CATEGORIES or target in BASELINE_FIELDS:
            values = transform.get('values')
            allowed = (*CATEGORIES[target], 'unknown') if target in CATEGORIES else (True, False)
            if kind != 'categories' or not isinstance(values, list) or not values:
                errors.append(f'{target}: explicit category mapping required')
                category_ok = False
            else:
                seen = []
                for v in values:
                    if not isinstance(v, dict) or 'raw' not in v or v.get('canonical') not in allowed or v['raw'] in seen:
                        errors.append(f'{target}: invalid/duplicate category mapping')
                        category_ok = False
                        break
                    if target in BASELINE_FIELDS and type(v['canonical']) is not bool:
                        errors.append(f'{target}: eligibility outputs must be explicit booleans')
                        category_ok = False
                    seen.append(v['raw'])
        elif target == 'index_date':
            if kind != 'date' or not transform.get('format'):
                errors.append('index_date: explicit date format required')
        elif target in TIME_FIELDS:
            if not (kind == 'already_canonical' and transform.get('input_unit') == 'days_after_index'
                    and transform.get('output_unit') == 'days_after_index'
                    or kind == 'date_to_days' and transform.get('format')):
                errors.append(f'{target}: explicit days-after-index units or date format required')
                unit_ok = False
        elif target == 'participant_id' and kind == 'identifier' and isinstance(transform.get('namespace'), str) and transform['namespace']:
            pass
        elif kind != 'identity':
            errors.append(f'{target}: explicit identity transform required; endpoint codes belong in crosswalk')
        checks.append({'canonical': target, 'status': 'valid' if len(errors) == before else 'invalid'})
    if config.get('participant_rows') != 'unique_baseline':
        errors.append('Declare one unique baseline record per participant; resolve longitudinal joins separately')
    if config.get('event_record_policy') != 'first_qualifying_candidates_verified':
        errors.append('First qualifying MI/stroke candidate ascertainment must be explicitly verified')
    return {'valid': not errors, 'errors': errors, 'warnings': warnings, 'checks': checks,
            'available': available, 'units_valid': unit_ok, 'categories_valid': category_ok,
            'mapping_hash': digest_json(config)}


def mapping_report(audit: dict) -> str:
    lines = ['MAPPING_VALID = ' + ('YES' if audit['valid'] else 'NO')]
    lines += [f"[{ 'x' if row['status'] == 'valid' else ' ' }] {row['canonical']}: {row['status']}" for row in audit['checks']]
    lines += ['ERROR: ' + message for message in audit['errors']]
    lines += ['NOTE: ' + message for message in audit['warnings']]
    return '\n'.join(lines) + '\n'


def harmonize(raw: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, dict]:
    audit = validate_mapping(config, raw.columns)
    if not audit['valid']:
        raise ValueError('Mapping validation failed; inspect the aggregate mapping audit')
    fields = {f['canonical']: f for f in config['fields']}
    output = pd.DataFrame(index=raw.index)
    for target in ('index_date', *[x for x in TARGETS if x != 'index_date']):
        f = fields[target]
        if f.get('status') == 'missing':
            output[target] = pd.NA
            continue
        series = raw[f['raw']].copy()
        transform, kind = f['transform'], f['transform']['kind']
        if kind in {'already_canonical', 'linear'}:
            try:
                series = pd.to_numeric(series, errors='raise')
            except (ValueError, TypeError):
                raise ValueError(f'{target}: nonnumeric observations; values omitted') from None
            if kind == 'linear':
                series = series * transform['scale'] + transform['offset']
            if np.isinf(series.to_numpy(dtype=float, na_value=np.nan)).any():
                raise ValueError(f'{target}: nonfinite observations; values omitted')
        elif kind == 'identifier':
            series = series.map(lambda x: pd.NA if pd.isna(x) else transform['namespace'] + str(x))
        elif kind == 'categories':
            result = pd.Series(pd.NA, index=series.index, dtype='object')
            matched = series.isna()
            for item in transform['values']:
                match = series.eq(item['raw']).fillna(False)
                result.loc[match] = item['canonical']
                matched |= match
            if not matched.all():
                raise ValueError(f'{target}: unmapped categorical observations ({int((~matched).sum())} rows); values omitted')
            series = result
        elif kind in {'date', 'date_to_days'}:
            parsed = pd.to_datetime(series, format=transform['format'], errors='coerce')
            # Invalid dates are retained as missing for explicit construction accounting.
            if kind == 'date_to_days':
                parsed = (parsed - pd.to_datetime(output['index_date'])).dt.total_seconds() / 86400
                if (series.notna() & parsed.isna() & output.index_date.notna()).any():
                    raise ValueError(f'{target}: invalid event dates; values omitted')
            series = parsed
        output[target] = series
    return output, audit
