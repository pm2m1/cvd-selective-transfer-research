# ELSA source registration V1 — public implementation

**PUBLIC_REGISTRATION_WORKFLOW_READY_NOT_EXECUTED**

Historical source authentication is **not established**. Public historical fingerprints bind Python code, not clinical archives. This package prepares a separate independently authorized local archive/member registration; it does not run clinical counts or train models.

Read `HISTORICAL_SOURCE_CONTRACT_AUDIT.md`, `PROVENANCE_LIMITATIONS_AND_BLOCKERS.md`, and `HUMAN_ONLY_SOURCE_REGISTRATION.md` before use. `REGISTRATION_PROTOCOL.json` records the AI-authored technical contract; it is not human/provider approval.

Entry point: `register_sources.py`. Registration implementation: `registration.py`. Source-descriptor generator: `config_generation.py`. The independent runtime `local_execution.py` is copied byte-for-byte from the unchanged count release. Templates are unpopulated public records, never authorizations. The `references/` files are exact public count-release/template copies.

## Public-only checks

```sh
python3 -B verify_package.py
python3 -B -m pytest -q -p no:cacheprovider tests
```

Production uses standard library only, Python 3.10+. Tests additionally use pytest and pandas to create invented Stata ZIP members in temporary directories. No clinical fixtures are included. The original count installation is verified by fingerprint only at independent execution; tests use an invented mini-installation.

All real source paths/hashes and generated artifacts must remain in the independently controlled private environment. Do not execute the protected operation through an AI agent. Existing attempts, audits, clinical sources, scientific definitions and count-engine code are not modified.
