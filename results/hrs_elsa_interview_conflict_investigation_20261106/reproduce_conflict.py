"""INVENTED records only. No --config, --input, authorization or real-data mode."""
import sys
from public_reference import references


def visit(p, wave):
    return next(v for v in p['visits'] if v['wave'] == wave)


def main():
    if len(sys.argv) != 1:
        print('STOP ISSUE=SYNTHETIC_REPRODUCER_ACCEPTS_NO_EXTERNAL_INPUTS')
        return 2
    old, fixtures, mapping, protocol, proposed = references()
    for label, flag in [('CONSISTENT', 1), ('KNOWN_DISAGREEMENT', 0), ('MISSING_INDICATOR', '.a')]:
        p = fixtures.person(mapping)
        p['participation']['6'] = flag
        for name, engine in [('FROZEN', old), ('PROPOSED_OBSERVABILITY', proposed)]:
            try:
                engine.validate_people([p], mapping)
                outcome = 'VALIDATION_ACCEPTED_NOT_SCIENTIFIC_APPROVAL'
            except engine.CountError as exc:
                outcome = str(exc)
            print('SYNTHETIC_ONLY CASE=' + label + ' ENGINE=' + name + ' RESULT=' + outcome)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
