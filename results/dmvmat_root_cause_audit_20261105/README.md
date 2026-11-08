# Public-only root-cause audit

Run only the invented-data tests from the repository root:

```sh
.venv/bin/python -B -m unittest discover -s results/dmvmat_root_cause_audit_20261105/tests -v
```

The diagnostic program has **no real-input or authorization interface**:

```sh
.venv/bin/python -B results/dmvmat_root_cause_audit_20261105/run_synthetic_diagnostics.py
```

It generates hard-coded invented observations and exclusively creates `synthetic_results/` beside itself. The delivered directory already contains the completed synthetic run; executing that command again intentionally fails rather than overwriting evidence. To independently reproduce it, use a separate public-only copy with a new empty audit directory, preserving its sibling public follow-up and public seven-candidate staging dependencies. Keep their relative directory structure; never copy private research outputs. No clinical/private input or private configuration is needed or accepted.

`audit_core.py` imports pure public model/metric/selector functions from the unchanged sibling follow-up's vendored API. It does not call its retained-export loader, original clinical loader, real executor or any authorization routine. Source imports and tests are scoped to public code. All reference implementations and experimental diagnostics are isolated here; original scripts and protocols remain untouched.

Read ROOT_CAUSE_REPORT.md for findings. Tables/figures marked SYNTHETIC_ONLY are mechanism illustrations, not HAALSI/MHAS results. The proposed next development study is inactive and requires separate prespecification and applicable independent local authorization. No independent external test is supplied by this audit.
