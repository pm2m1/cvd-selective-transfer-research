#!/usr/bin/env python3
"""Read-only local metadata diagnostic; never opens archive or receipt contents."""
from pathlib import Path
from prepare_plan import (Stop, arguments, require_operator, existing_file, load_plan,
                          evidence_state, validate_structure, source_review, archive_location,
                          PLACEHOLDER, location)


def readiness(plan_value, count_tools, authorization=None, output=None):
    p = location(plan_value)
    state = evidence_state(p, authorization, output)
    # Unknown siblings could be differently named operation evidence. Do not
    # falsely report NO consumed attempt when their role cannot be established.
    if state['unknown']:
        raise Stop('UNRECOGNIZED_RUN_ARTIFACT_READINESS_UNDETERMINED')
    structure = configured = present = established = False
    try:
        p = existing_file(p, 'REGISTRATION_PLAN_MISSING')
        _, plan = load_plan(p)
        established = source_review(plan)
        raw = plan.get('input_archives', [{}])[0].get('archive_path')
        configured = isinstance(raw, str) and raw != PLACEHOLDER and Path(raw).is_absolute()
        if configured:
            try:
                archive_location(raw)
                present = True
            except Stop:
                pass
        validate_structure(plan, count_tools)
        structure = True
    except (Stop, IndexError, TypeError, AttributeError):
        pass
    ready = (structure and configured and present and established and not state['output']
             and not state['consumed'] and not state['unknown'])
    return [
        'REGISTRATION_PLAN: ' + ('READY' if ready else 'INCOMPLETE'),
        'ARCHIVE_PATH: ' + ('CONFIGURED' if configured else 'MISSING'),
        'ARCHIVE_FILE: ' + ('PRESENT' if present else 'MISSING'),
        'SOURCE_REVIEW: ' + ('ESTABLISHED' if established else 'UNRESOLVED'),
        'AUTHORIZATION: ' + ('RECORDED' if state['authorization'] else 'NOT_RECORDED'),
        'CONSUMED_ATTEMPT: ' + ('YES' if state['consumed'] else 'NO')]


def main():
    try:
        args = arguments(__doc__)
        require_operator()
        result = readiness(args.plan, args.count_tools, args.authorization, args.output)
        print('\n'.join(result))
        return 0 if result[0].endswith(': READY') else 2
    except Stop as exc:
        print('STOP ISSUE=' + str(exc))
    except SystemExit as exc:
        return exc.code
    except BaseException:
        print('STOP ISSUE=LOCAL_READINESS_NOT_DETERMINED')
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
