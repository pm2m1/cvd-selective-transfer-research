"""Pure aggregate-schema checks and unresolved worksheets; no file/data loaders."""
from collections import Counter
import copy
import re

PARTS = ('PARTICIPATION_ONE', 'PARTICIPATION_ZERO', 'PARTICIPATION_MISSING', 'PARTICIPATION_OTHER_OR_INVALID')
RESPONDING = ('CORE_PERSONAL_INTERVIEW', 'CORE_PARTIAL_INTERVIEW', 'CORE_PROXY_INTERVIEW', 'CORE_INSTITUTIONAL_INTERVIEW')
CORES = RESPONDING + ('NO_CORE_RECORD', 'CORE_AMBIGUOUS', 'NO_CORE_INTERVIEW_EVIDENCE', 'CORE_DEATH_STATUS_NO_INTERVIEW_EVIDENCE')
BASES = ('OUTCOME_BASED', 'ASKPX_FALLBACK', 'EXPLICIT_PROXY_FLAG_DISAGREEMENT', 'NO_CORE_RECORD', 'DOMAIN_ERROR')
INTERPRETATIONS = ('CONSISTENT', 'KNOWN_DISAGREEMENT', 'INSUFFICIENT_EVIDENCE', 'UNRESOLVED_DECODER_AMBIGUITY')
TARGETS = ('NOT_APPLICABLE_NO_CORE', 'EARLIER_PARTICIPATION_DOMAIN_REJECTION', 'EARLIER_SOURCE_DOMAIN_REJECTION',
           'WOULD_REJECT_KNOWN_ZERO', 'WOULD_REJECT_MISSING', 'NO_TARGET_REJECTION')


def require(test):
    if not test:
        raise ValueError('UNSUPPORTED_OR_INCOMPLETE_REVIEW_EVIDENCE')


def count(value):
    require(type(value) is int and value >= 0)
    return value


def counter(value, allowed=None):
    require(isinstance(value, dict))
    require(all(isinstance(k, str) and (allowed is None or k in allowed) for k in value))
    return Counter({k: count(v) for k, v in value.items()})


def classify_cell(part, core, basis):
    """Reference to the frozen diagnostic's recorded categories, not causality."""
    require(part in PARTS and core in CORES and basis in BASES)
    require((core == 'NO_CORE_RECORD') == (basis == 'NO_CORE_RECORD'))
    require(basis != 'DOMAIN_ERROR' or core == 'CORE_AMBIGUOUS')
    require(basis not in ('ASKPX_FALLBACK', 'EXPLICIT_PROXY_FLAG_DISAGREEMENT') or core == 'CORE_PROXY_INTERVIEW')
    if basis == 'DOMAIN_ERROR':
        return 'INSUFFICIENT_EVIDENCE', 'EARLIER_SOURCE_DOMAIN_REJECTION'
    if part == PARTS[3]:
        return 'INSUFFICIENT_EVIDENCE', 'EARLIER_PARTICIPATION_DOMAIN_REJECTION'
    if core == 'NO_CORE_RECORD':
        return ('CONSISTENT' if part == PARTS[1] else 'INSUFFICIENT_EVIDENCE'), 'NOT_APPLICABLE_NO_CORE'
    target = ('WOULD_REJECT_KNOWN_ZERO' if part == PARTS[1] else
              'WOULD_REJECT_MISSING' if part == PARTS[2] else 'NO_TARGET_REJECTION') if core in RESPONDING else 'NO_TARGET_REJECTION'
    if basis in ('ASKPX_FALLBACK', 'EXPLICIT_PROXY_FLAG_DISAGREEMENT'):
        return 'UNRESOLVED_DECODER_AMBIGUITY', target
    if core in RESPONDING:
        return ('CONSISTENT' if part == PARTS[0] else 'KNOWN_DISAGREEMENT' if part == PARTS[1] else 'INSUFFICIENT_EVIDENCE'), target
    if core in ('NO_CORE_INTERVIEW_EVIDENCE', 'CORE_DEATH_STATUS_NO_INTERVIEW_EVIDENCE'):
        return ('CONSISTENT' if part == PARTS[1] else 'UNRESOLVED_DECODER_AMBIGUITY' if part == PARTS[0] else 'INSUFFICIENT_EVIDENCE'), target
    return 'INSUFFICIENT_EVIDENCE', target


def raw_counter(value):
    result = counter(value)
    pattern = r'(PYTHON_NONE|BOOLEAN_REPRESENTATION|STATA_MISSING_(PLAIN|[A-Z])|NONNUMERIC_REPRESENTATION|NONFINITE_REPRESENTATION|NONINTEGER_REPRESENTATION|OUT_OF_STATUS_CODE_RANGE|NO_CORE_RECORD|NUMERIC(_STRING)?_-?[0-9]{1,3})'
    require(all(re.fullmatch(pattern, k) for k in result))
    return result


def validate_aggregate(report):
    expected = {'schema', 'scope', 'waves', 'overall_interpretations', 'zero_and_missing_conflicts_separate',
                'first_detected_target_conflict', 'first_order', 'source_domain_error_observed', 'documented_semantics',
                'wave_specific_review', 'remaining_interpretation', 'eligibility_decisions_changed',
                'participant_rows_or_keys_written', 'scientific_cause_established', 'action_policy', 'bindings'}
    require(isinstance(report, dict) and set(report) == expected)
    require(report['schema'] == 'elsa-private-status-diagnostic-v1')
    require(report['scope'] == 'STATUS_ONLY_NO_DISEASE_ENDPOINTS_NO_ELIGIBILITY_CHANGES')
    require(all(report[k] is False for k in ('source_domain_error_observed', 'eligibility_decisions_changed',
                                          'participant_rows_or_keys_written', 'scientific_cause_established')))
    require(set(report['waves']) == {str(w) for w in range(1, 10)})
    require(report['first_order'] == 'HARMONIZED_SOURCE_ROW_ORDER_THEN_WAVE_NOT_PROOF_OF_HISTORICAL_FIRST')
    require(report['documented_semantics'] == 'INW_INCLUDES_FULL_PARTIAL_PERSONAL_PROXY_INSTITUTIONAL_RESPONSE_NOT_DISEASE_ABSENCE')
    require(report['remaining_interpretation'] == 'RECORDED_DISAGREEMENT_NOT_CAUSAL_PROOF_OF_LINKAGE_ROUTING_OR_REVISION_ERROR')
    require(report['action_policy'] == ['A_OBSERVABILITY_ONLY', 'B_IMPLEMENTATION_DEFECT_NOT_ESTABLISHED', 'C_AMENDMENT_REQUIRED_BEFORE_SEMANTIC_CHANGE'])
    require(report['wave_specific_review'] == {'1':'INDOC_ASKPX1_PROXY_NO_2','2':'W2INDOUT_ASKPX1_PROXY_NO_0',
        '3_9':'WAVE_SPECIFIC_WINDOUT_ASKPX_DOMAINS_NOT_INTERCHANGEABLE','1_5':'H_INDICATOR_CAN_USE_INDEX_OUTCOMES','6_9':'H_INDICATOR_USES_CORE_OUTCOMES'})
    overall, conflicts, waves = Counter(), Counter(), {}
    universe = None
    for w in map(str, range(1, 10)):
        q = report['waves'][w]
        require(set(q) == {'classification_matrix', 'interpretations', 'frozen_target_checks', 'decoder_basis',
                          'participation_raw_states', 'outcome_raw_states', 'proxy_raw_states',
                          'missing_core_records', 'unmatched_core_records'})
        cells = counter(q['classification_matrix']); interpretations, targets, bases = Counter(), Counter(), Counter()
        families = []
        missing = 0
        for key, n in sorted(cells.items()):
            bits = key.split('|'); require(len(bits) == 3)
            part, core, basis = bits
            interpretation, target = classify_cell(part, core, basis)
            # A COMPLETED frozen diagnostic cannot have source/participation domain errors.
            require(part != PARTS[3] and basis != 'DOMAIN_ERROR')
            interpretations[interpretation] += n; targets[target] += n; bases[basis] += n
            if core == 'NO_CORE_RECORD': missing += n
            if target in ('WOULD_REJECT_KNOWN_ZERO', 'WOULD_REJECT_MISSING'):
                conflicts[target + '|' + basis] += n
            if n:
                families.append({'family_id': 'W' + w + '_FAMILY_' + str(len(families)+1).zfill(3),
                    'participation': part, 'core': core, 'decoder_basis': basis, 'private_frequency': n,
                    'recorded_diagnostic_interpretation': interpretation, 'frozen_target_check': target,
                    'public_evidence_class': 'CONFIRMED_SYNTHETIC_REPRODUCTION',
                    'scientific_interpretation_status': 'UNRESOLVED',
                    'review_requirement': 'PRIVATE_REVIEW_REQUIRED', 'reviewer_evidence_and_determination': 'UNRESOLVED'})
        n = sum(cells.values()); require(n > 0)
        if universe is None: universe = n
        require(n == universe)
        require(interpretations == counter(q['interpretations'], INTERPRETATIONS))
        require(targets == counter(q['frozen_target_checks'], TARGETS))
        require(bases == counter(q['decoder_basis'], BASES))
        require(count(q['missing_core_records']) == missing)
        for field in ('participation_raw_states', 'outcome_raw_states', 'proxy_raw_states'):
            require(sum(raw_counter(q[field]).values()) == n)
        overall.update(interpretations)
        waves[w] = {'observed_families': families, 'unmatched_core_records': count(q['unmatched_core_records']),
                    'missing_core_records': missing, 'participation_raw_states': q['participation_raw_states'],
                    'outcome_raw_states': q['outcome_raw_states'], 'proxy_raw_states': q['proxy_raw_states'],
                    'documentation_reviewed': 'UNRESOLVED', 'linkage_interpretation': 'UNRESOLVED',
                    'all_observed_families_reviewed': 'UNRESOLVED'}
    require(overall == counter(report['overall_interpretations'], INTERPRETATIONS))
    require(conflicts == counter(report['zero_and_missing_conflicts_separate']))
    first = report['first_detected_target_conflict']
    if sum(conflicts.values()) == 0:
        require(first is None)
    else:
        require(isinstance(first, dict) and set(first) == {'wave','participation','core','decoder_basis','interpretation','frozen_target_check'})
        require(type(first['wave']) is int and 1 <= first['wave'] <= 9)
        key = '|'.join(first[k] for k in ('participation','core','decoder_basis'))
        require(report['waves'][str(first['wave'])]['classification_matrix'].get(key, 0) > 0)
        interpretation, target = classify_cell(first['participation'],first['core'],first['decoder_basis'])
        require(first['interpretation'] == interpretation and first['frozen_target_check'] == target and target.startswith('WOULD_REJECT_'))
    return waves


def worksheet(report, decision_template, provenance):
    waves = validate_aggregate(report)
    decision = copy.deepcopy(decision_template)
    decision['family_determinations'] = [{'family_id': f['family_id'], 'determination': 'UNRESOLVED',
        'supporting_evidence': 'UNRESOLVED', 'action_category': 'UNRESOLVED'} for q in waves.values() for f in q['observed_families']]
    result = {'schema': 'elsa-private-scientific-evidence-worksheet-v1',
        'mechanical_verification': {'reviewed_metadata_hashes_matched': True,
            'completed_diagnostic_binding_matched': True, 'frozen_diagnostic_code_binding_matched': True,
            'failed_count_binding_matched': True, 'ten_history_source_descriptors_matched': True,
            'registration_metadata_matched': True, 'all_nine_waves_accounted': True,
            'raw_source_bytes_rechecked': False, 'independent_source_authentication_established': False,
            'permission_or_scientific_acceptance_granted_by_software': False},
        'source_provenance': provenance, 'all_waves': waves,
        'evidence_limitations': ['Recorded frequencies do not establish a causal explanation or scientific precedence.',
            'Status matrix cells and separate raw marginals cannot reconstruct every joint raw outcome/proxy combination.',
            'No new source-byte reads, linkage joins, respondent records or disease counts were performed.',
            'Successful diagnostic forbids invalid/duplicate linkage; missing/unmatched Core coverage may remain.',
            'Equal history descriptors do not validate nurse features, earlier permissions, authentic distributor edition or baseline timing.',
            'First conflict is not proof that all conflicts share a cause.'],
        'reviewer_decision': decision, 'no_automatic_adoption': True, 'no_count_or_training': True}
    return result, decision
