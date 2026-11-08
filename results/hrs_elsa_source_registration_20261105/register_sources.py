"""Independent local entry point. No protected files are read at import."""
from local_execution import cli, Rejected
from registration import PURPOSE, register, verify_public


def no_demo(_):
    raise Rejected('USE_INVENTED_FIXTURE_TESTS_ONLY')


if __name__ == '__main__':
    try:
        verify_public()  # Public references only; no protected configuration access.
    except BaseException:
        print('STOP ISSUE=PUBLIC_REGISTRATION_REFERENCE_BINDING_INVALID')
        raise SystemExit(2)
    raise SystemExit(cli(PURPOSE, register, no_demo))
