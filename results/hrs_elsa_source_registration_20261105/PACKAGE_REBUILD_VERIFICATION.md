# Public distribution verification

The public ZIP is extracted into a newly created temporary directory and its public manifest is independently checked there. The same 60 invented-fixture tests are run from the extracted source with bytecode/cache writing disabled. No clinical files or count installation are required for the extracted test suite.

Expected and verified distribution properties: one public tool tree at ZIP root; all referenced reference files present; no absolute or traversing ZIP entry names; no clinical `.dta`/prediction/checkpoint/authorization files packaged; no compiler/cache files; no path outside the extracted package needed by tests. Production separately requires the unchanged public count installation, referenced explicitly in the independent private plan.

Exact archive SHA256, final extracted verification status and actual test totals are recorded in the adjacent `ELSA_Source_Registration_20261105_Public.verification.json` distribution receipt. That receipt is outside the ZIP to avoid a self-referential archive digest. It is a public build receipt, not a source-use authorization or evidence of real registration.
