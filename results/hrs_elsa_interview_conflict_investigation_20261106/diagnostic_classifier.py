"""Pure diagnostic classifier, not a private-data loader or execution controller.

Future use on actual source metadata is a distinct protected operation requiring
independent scope/authorization. This module has no file, network or CLI input.
All detailed outputs from any such authorized operation must remain private.
"""


def classify_observation(engine, mapping, wave, participation, outcome, proxy):
    if type(wave) is not int or not 1 <= wave <= 9:
        raise ValueError('INVALID_SYNTHETIC_OR_REVIEWED_WAVE')
    outcome_field = 'indoc' if wave == 1 else f'w{wave}indout'
    proxy_field = 'askpx1' if wave < 3 else 'askpx'
    raw = {outcome_field: outcome, proxy_field: proxy}
    result = {'wave': wave, 'disposition': None, 'decoder_kind': None, 'decoder_basis': None}
    try:
        flag = engine.code(participation)
        if flag not in (0, 1, None):
            result['disposition'] = 'PARTICIPATION_INPUT_DOMAIN_ERROR'
            return result
        fields = mapping['waves'][str(wave)]['fields']
        out = engine.scalar(raw, outcome_field, fields)
        px = engine.scalar(raw, proxy_field, fields)
        kind = engine.interview({'wave': wave, 'raw': raw}, mapping)
    except engine.CountError:
        result['disposition'] = 'SOURCE_INPUT_DOMAIN_ERROR'
        return result
    result['decoder_kind'] = kind
    result['decoder_basis'] = ('PROXY_FLAG_FALLBACK' if kind == 'proxy' and out not in (13, 23, 25, 27)
                               else 'EXPLICIT_OR_UNKNOWN_OUTCOME')
    if kind in ('personal', 'partial', 'proxy', 'institutional'):
        result['disposition'] = ('RESPONSE_FLAG_UNRESOLVED' if flag is None else
                                 'KNOWN_RESPONSE_FLAG_DISAGREEMENT' if flag == 0 else
                                 'NO_TARGET_CONFLICT')
    else:
        result['disposition'] = 'NO_TARGET_CONFLICT'
    return result
