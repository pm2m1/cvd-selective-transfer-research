# Audit summary

**Completed:** public-code audit, independent selector/geometry/MMD references, all-mask freezing/optimizer tests, split-isolation tests, six invented neural stress scenarios, threshold-resampling stress, label-allocation arithmetic and a prospective one-factor experiment specification.

**Tests:** 30 passed, zero failures. The 128 masks and 3,054 logical boundary/random decisions are internal test cases, not an inflated test-method total. Synthetic neural run: six source fits, 72 target fits, 36 source-reference evaluations. No clinical operation was executed.

**Selector verdict:** no tested specification violation. Logical updates33 plus the sizes of its selected modules; fusion1 alone adds5,312. Total architecture remains8,033. Invalid geometry shares internal blocks; it does not fall back to full adaptation. Fresh target clones and exact optimizer membership behaved correctly.

**Scientific verdict:** real negative transfer and its cause remain unverified without an authorized paired private assessment. Synthetic adaptation helped after relationship reversal and hurt with scarce events. Better Brier can accompany worse AP. Pooled OOF scores can change ranking metrics through fold offsets even when each fold's discrimination is unchanged.

**Stopping/calibration:** checkpoint choice is BCE-based, not AP-based. Epoch zero cannot win under the frozen rule. The 10% calibration sample has nine labels and cannot support5+5. Other small calibration samples may remain unsupported or highly unstable. All-negative predictions correctly yield recall0 and undefined precision; accuracy does not demonstrate event detection.

**Next experiment:** compare otherwise identical full adaptation with versus without epoch-zero eligibility, with source-only control and participant-matched outer diagnostics. Fresh prespecification/authorization and new private destinations are required; do not reuse a completed attempt. Details: FUTURE_EXPERIMENT_PROPOSAL.md.

**Not done:** no private output inspection, real training, export, threshold tuning on clinical data, test inference, frozen-code patch, altered source bindings or deployed recovery mechanism. No independent validation or real-data improvement is claimed.

Start with ROOT_CAUSE_REPORT.md; machine-readable invented evidence is in synthetic_results/. Public/new source SHA256 values are recorded in SOURCE_INTEGRITY.json and AUDIT_SHA256.json.
