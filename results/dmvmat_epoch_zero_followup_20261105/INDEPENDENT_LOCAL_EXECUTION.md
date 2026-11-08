# Independent local installation and new execution

This public package is ready for **independent permission review and synthetic verification**, not permission to process clinical records through Codex. No real execution was performed here. Keep all private config, retained input descriptors, authorization, checkpoints, outcomes and results in an environment inaccessible to AI tools/indexers. Do not paste protected paths or outputs into chat.

## 1. Install a new public-only copy

Manually transfer this new public package to the independently controlled machine/workspace. Use the release's public manifest SHA256 from VALIDATION_REPORT.md/the final handoff to check that the expected public version was transferred. Existing source packages and fingerprinted tool trees must stay unchanged.

```sh
python3 -B /PUBLIC_TRANSFER/dmvmat_epoch_zero_followup_20261105/install_public_epoch_zero.py \
  --source /PUBLIC_TRANSFER/dmvmat_epoch_zero_followup_20261105 \
  --destination /ISOLATED_NEW_PUBLIC_PACKAGE \
  --expected-manifest-sha256 PUBLIC_MANIFEST_SHA256_FROM_RELEASE
```

Paths shown are placeholders, not actual private locations. The destination must not exist and its parent must already exist. The installer verifies every manifest-listed public file before copying, copies only that allowlist, rechecks hashes and creates restrictive permissions. It rejects symlinks and overwrites. It never transfers private records. On installation interruption preserve the partial destination; diagnose it, then choose a genuinely new public installation destination. That does not authorize retrying a consumed clinical operation.

## 2. Prepare the new reviewed config locally

Use the existing approved Python environment; no network/package installation is performed by this utility. The copied requirements file documents earlier synthetic dependencies; actual versions must be recorded and reviewed for this distinct operation. In the newly installed public package:

```sh
cd /ISOLATED_NEW_PUBLIC_PACKAGE
python3 -B epoch_zero.py --runtime-info
```

Create a **new private** reviewed JSON from local_config.template.json, with permissions0600, outside this public tool tree. Fill its protocol path/digest and package manifest digest using this release. Copy only the four reviewed retained-export descriptors from the prior independently prepared follow-up config, preserving their existing exact hashes:

- development_manifest
- completed_workflow_receipt (the original completed seven-candidate workflow receipt required by the retained-export verifier)
- source_preprocessing
- development_bundle

Do not substitute the old label-curve result/receipt for that original workflow receipt. Do not reopen raw datasets, original assignments or prior predictions to construct inputs. Do not regenerate governance records or relax old source bindings. Record the exact runtime versions printed above in `runtime_versions`. Placeholder values cannot pass verification. Independently review permission scope for this new retained-export operation and its restricted output storage; file existence/hash equality does not establish permission or authenticity. The package does not discover private paths or populate authorization claims.

There is no need to rerun the old exporter, old reviewer, seven-candidate training or label-curve experiment. This new operation may reuse immutable retained inputs only after new independent authorization.

## 3. Separately authorize this distinct operation

Run in a real independent Terminal, not an agent/CI shell. **Do not remove AI/CI variables to disguise an agent environment.** Use new unused private authorization and output paths under an existing private parent directory with mode0700:

```sh
python3 -B epoch_zero.py --authorize-local \
  --config /PRIVATE/NEW_EPOCH_ZERO_REVIEWED_CONFIG.json \
  --authorization /PRIVATE/NEW_EPOCH_ZERO_AUTHORIZATION.json \
  --output /PRIVATE/NEW_EPOCH_ZERO_RUN
```

The original runtime prompts for the actual operator identity and confirmation of provider/institutional scope and isolation. Enter these locally only after establishing that scope. No phrase, name or approval is prefilled or piped. A new authorization purpose binds this package's code, configuration and exact output destination. Previous export/training/diagnostic authorizations cannot be reused. `LOCAL_AUTHORIZATION_RECORDED_NO_DATA_PROCESSING` indicates only a new local operator record, not data processing, institutional approval or scientific acceptance.

## 4. Execute once using that new authorization

```sh
python3 -B epoch_zero.py --execute-local \
  --config /PRIVATE/NEW_EPOCH_ZERO_REVIEWED_CONFIG.json \
  --authorization /PRIVATE/NEW_EPOCH_ZERO_AUTHORIZATION.json \
  --output /PRIVATE/NEW_EPOCH_ZERO_RUN
```

The unchanged runtime guard runs before reading private config/authorization. The new wrapper verifies package/protocol/runtime; the retained loader verifies the original input chain. A consumed STARTED marker is created before restricted processing. Expected terminal success acknowledgment is the **static** `REVIEW ISSUE=PRIVATE_OUTPUT_REQUIRES_DISCLOSURE_REVIEW`. It says nothing about improvement or scientific acceptance. Any failure prints a static local-operation status; inspect its private receipt locally. A processing failure stops the whole experiment; no continuing remaining cells, rerun or resume is automatic.

Do not edit/delete/rename output or attempt markers, repoint a used authorization, or choose another output merely to evade a failed attempt. Any recovery requires documented cause and separately justified new authorization/version. Old and new completed outputs remain immutable.

## 5. Review privately

The same run creates the private JSON and Markdown comparison; **no second model or metric execution is needed**. Read `epoch_zero_comparison.private.md` locally with an ordinary editor or `less`, and inspect JSON/checkpoints only in the approved private environment. Do not share counts, rates, scores, state hashes, threshold availability, data-conditioned decisions or participant outputs with AI until applicable disclosure review clears the specific aggregate release.

The report contains all budgets, paired fold differences, conditional uncertainty, pooled-OOF secondary metrics, epoch0 frequencies, checkpoint drift, confusion matrices and supported threshold metrics. Repeats reuse people; no 9-fold count is nine independent studies. A favorable point estimate is not superiority. No empirical winner, clinical sensitivity guarantee or real-test authorization is assigned automatically.

## Synthetic verification only

Tests never read retained/private inputs:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B epoch_zero.py --synthetic-demo --output /NEW_UNUSED_SYNTHETIC_OUTPUT
```

The demo uses invented IDs/features/outcomes, two source epochs, three target epochs and20 bootstrap resamples, while retaining all45 split/budget cells and three arms. Its different settings and SYNTHETIC_ONLY scope are recorded. Real configuration is rejected by demo CLI. Synthetic output cannot be used as clinical results or an authorization fixture.

**INDEPENDENT_TEST_NOT_AVAILABLE.** The original MHAS locked test remains untouched. Cross-validation on previously exposed development participants does not establish external generalization.
