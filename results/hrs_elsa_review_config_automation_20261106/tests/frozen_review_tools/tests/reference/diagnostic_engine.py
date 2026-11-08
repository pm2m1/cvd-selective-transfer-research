"""Pure status-only aggregation. No dataset, cohort, endpoint or model imports."""
from collections import Counter
import math
import re
import frozen_decoder as decoder

PARTICIPATION = ('PARTICIPATION_ONE', 'PARTICIPATION_ZERO', 'PARTICIPATION_MISSING',
                 'PARTICIPATION_OTHER_OR_INVALID')
RESPONDING = ('personal', 'partial', 'proxy', 'institutional')


def raw_state(value):
    """Bounded code/storage tokens only; never unrestricted scalar text."""
    if value is None:
        return 'PYTHON_NONE'
    if isinstance(value, bool):
        return 'BOOLEAN_REPRESENTATION'
    if isinstance(value, str) and re.fullmatch(r'\.[a-z]?', value):
        return 'STATA_MISSING_' + ('PLAIN' if value == '.' else value[1:].upper())
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 'NONNUMERIC_REPRESENTATION'
    if not math.isfinite(number):
        return 'NONFINITE_REPRESENTATION'
    if not number.is_integer():
        return 'NONINTEGER_REPRESENTATION'
    # Never accidentally output an identifier mistakenly stored in a status field.
    if abs(number) > 999:
        return 'OUT_OF_STATUS_CODE_RANGE'
    return ('NUMERIC_STRING_' if isinstance(value, str) else 'NUMERIC_') + str(int(number))


def participation(value):
    try:
        code = decoder.code(value)
    except decoder.CountError:
        return PARTICIPATION[3], None
    if code == 1:
        return PARTICIPATION[0], code
    if code == 0:
        return PARTICIPATION[1], code
    if code is None:
        return PARTICIPATION[2], code
    return PARTICIPATION[3], code


def classify(wave, flag, raw, mapping):
    """One status observation; no IDs accepted or returned."""
    part, _ = participation(flag)
    result = {'participation': part, 'core': 'NO_CORE_RECORD',
        'decoder_kind': 'NO_CORE_RECORD', 'decoder_basis': 'NO_CORE_RECORD',
        'interpretation': 'INSUFFICIENT_EVIDENCE', 'frozen_target_check': 'NOT_APPLICABLE_NO_CORE',
        'input_domain_error': part == PARTICIPATION[3],
        'participation_raw_state': raw_state(flag), 'outcome_raw_state': 'NO_CORE_RECORD',
        'proxy_raw_state': 'NO_CORE_RECORD'}
    if raw is None:
        if part == PARTICIPATION[1]:
            result['interpretation'] = 'CONSISTENT'
        if part == PARTICIPATION[3]:
            result['frozen_target_check'] = 'EARLIER_PARTICIPATION_DOMAIN_REJECTION'
        return result
    outcome_name = 'indoc' if wave == 1 else f'w{wave}indout'
    proxy_name = 'askpx1' if wave < 3 else 'askpx'
    fields = mapping['waves'][str(wave)]['fields']
    result.update(outcome_raw_state=raw_state(raw.get(outcome_name)),
                  proxy_raw_state=raw_state(raw.get(proxy_name)))
    try:
        outcome = decoder.scalar(raw, outcome_name, fields)
        proxy = decoder.scalar(raw, proxy_name, fields)
        kind = decoder.interview({'wave': wave, 'raw': raw}, mapping)
    except decoder.CountError:
        result.update(core='CORE_AMBIGUOUS', decoder_kind='CORE_DOMAIN_INVALID',
                      decoder_basis='DOMAIN_ERROR', input_domain_error=True,
                      frozen_target_check='EARLIER_SOURCE_DOMAIN_REJECTION')
        return result
    fallback = kind == 'proxy' and outcome not in (13, 23, 25, 27)
    contradictory_proxy = outcome in (13, 23, 25, 27) and proxy == (2 if wave == 1 else 0)
    if kind in RESPONDING:
        core = {'personal': 'CORE_PERSONAL_INTERVIEW', 'partial': 'CORE_PARTIAL_INTERVIEW',
                'proxy': 'CORE_PROXY_INTERVIEW', 'institutional': 'CORE_INSTITUTIONAL_INTERVIEW'}[kind]
    elif kind == 'death_status':
        core = 'CORE_DEATH_STATUS_NO_INTERVIEW_EVIDENCE'
    elif outcome is not None and outcome > 0 and outcome not in (11, 13, 21, 23, 24, 25, 26, 27, 99):
        core = 'NO_CORE_INTERVIEW_EVIDENCE'
    else:
        core = 'CORE_AMBIGUOUS'
    result.update(core=core, decoder_kind=kind,
                  decoder_basis='ASKPX_FALLBACK' if fallback else
                  'EXPLICIT_PROXY_FLAG_DISAGREEMENT' if contradictory_proxy else 'OUTCOME_BASED')
    if part == PARTICIPATION[3]:
        result['frozen_target_check'] = 'EARLIER_PARTICIPATION_DOMAIN_REJECTION'
    elif kind in RESPONDING:
        result['frozen_target_check'] = ('WOULD_REJECT_KNOWN_ZERO' if part == PARTICIPATION[1] else
            'WOULD_REJECT_MISSING' if part == PARTICIPATION[2] else 'NO_TARGET_REJECTION')
    else:
        result['frozen_target_check'] = 'NO_TARGET_REJECTION'
    if part == PARTICIPATION[3]:
        result['interpretation'] = 'INSUFFICIENT_EVIDENCE'
    elif fallback or contradictory_proxy:
        result['interpretation'] = 'UNRESOLVED_DECODER_AMBIGUITY'
    elif kind in RESPONDING:
        result['interpretation'] = ('CONSISTENT' if part == PARTICIPATION[0] else
                                   'KNOWN_DISAGREEMENT' if part == PARTICIPATION[1] else
                                   'INSUFFICIENT_EVIDENCE')
    elif core in ('NO_CORE_INTERVIEW_EVIDENCE', 'CORE_DEATH_STATUS_NO_INTERVIEW_EVIDENCE'):
        result['interpretation'] = ('CONSISTENT' if part == PARTICIPATION[1] else
                                   'UNRESOLVED_DECODER_AMBIGUITY' if part == PARTICIPATION[0] else
                                   'INSUFFICIENT_EVIDENCE')
    return result


def summarize(harmonized, cores, mapping):
    """Internal exact keys stay in memory. Output contains only private aggregates."""
    per_wave = {str(w): {'classification_matrix': Counter(), 'interpretations': Counter(),
        'frozen_target_checks': Counter(), 'decoder_basis': Counter(),
        'participation_raw_states': Counter(), 'outcome_raw_states': Counter(),
        'proxy_raw_states': Counter(), 'missing_core_records': 0,
        'unmatched_core_records': len(set(cores[w]) - set(harmonized))} for w in range(1, 10)}
    overall, conflicts = Counter(), Counter()
    first = None
    domain_error = False
    # Match original reader's harmonized row order, then ascending Core wave.
    for key, h in harmonized.items():
        for w in range(1, 10):
            r = classify(w, h['inw'+str(w)], cores[w].get(key), mapping)
            q = per_wave[str(w)]
            q['classification_matrix'][r['participation']+'|'+r['core']+'|'+r['decoder_basis']] += 1
            for name, value in [('interpretations', r['interpretation']),
                ('frozen_target_checks', r['frozen_target_check']), ('decoder_basis', r['decoder_basis']),
                ('participation_raw_states', r['participation_raw_state']),
                ('outcome_raw_states', r['outcome_raw_state']), ('proxy_raw_states', r['proxy_raw_state'])]:
                q[name][value] += 1
            if r['core'] == 'NO_CORE_RECORD':
                q['missing_core_records'] += 1
            overall[r['interpretation']] += 1
            domain_error |= r['input_domain_error']
            if r['frozen_target_check'] in ('WOULD_REJECT_KNOWN_ZERO', 'WOULD_REJECT_MISSING'):
                conflicts[r['frozen_target_check']+'|'+r['decoder_basis']] += 1
                if first is None:
                    first = {'wave': w, 'participation': r['participation'], 'core': r['core'],
                             'decoder_basis': r['decoder_basis'], 'interpretation': r['interpretation'],
                             'frozen_target_check': r['frozen_target_check']}
    return {'schema': 'elsa-private-status-diagnostic-v1',
        'scope': 'STATUS_ONLY_NO_DISEASE_ENDPOINTS_NO_ELIGIBILITY_CHANGES',
        'waves': per_wave, 'overall_interpretations': overall,
        'zero_and_missing_conflicts_separate': conflicts, 'first_detected_target_conflict': first,
        'first_order': 'HARMONIZED_SOURCE_ROW_ORDER_THEN_WAVE_NOT_PROOF_OF_HISTORICAL_FIRST',
        'source_domain_error_observed': domain_error,
        'documented_semantics': 'INW_INCLUDES_FULL_PARTIAL_PERSONAL_PROXY_INSTITUTIONAL_RESPONSE_NOT_DISEASE_ABSENCE',
        'wave_specific_review': {'1': 'INDOC_ASKPX1_PROXY_NO_2', '2': 'W2INDOUT_ASKPX1_PROXY_NO_0',
            '3_9': 'WAVE_SPECIFIC_WINDOUT_ASKPX_DOMAINS_NOT_INTERCHANGEABLE',
            '1_5': 'H_INDICATOR_CAN_USE_INDEX_OUTCOMES', '6_9': 'H_INDICATOR_USES_CORE_OUTCOMES'},
        'remaining_interpretation': 'RECORDED_DISAGREEMENT_NOT_CAUSAL_PROOF_OF_LINKAGE_ROUTING_OR_REVISION_ERROR',
        'eligibility_decisions_changed': False, 'participant_rows_or_keys_written': False,
        'scientific_cause_established': False,
        'action_policy': ['A_OBSERVABILITY_ONLY', 'B_IMPLEMENTATION_DEFECT_NOT_ESTABLISHED',
                          'C_AMENDMENT_REQUIRED_BEFORE_SEMANTIC_CHANGE']}
