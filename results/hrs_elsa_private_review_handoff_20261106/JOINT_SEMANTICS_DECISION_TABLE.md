# Joint semantics decision matrix

Apply the exact wave domain first, across W1–9. The first column describes hypothetical combinations, not actual private findings. `review_logic.py` supplies the executable aggregate-category matrix; `references/PUBLIC_CONTRACT.json` preserves wave-specific raw domains.

| Combination | Documented meaning | Frozen behavior | Evidence class / outstanding requirement |
|---|---|---|---|
| Direct personal/partial/proxy/institutional response + inw1 | Broad response agrees | No target conflict; personal disease eligibility remains separate | CONFIRMED_PUBLIC_DOCUMENTATION and CONFIRMED_SYNTHETIC_REPRODUCTION; actual lineage still PRIVATE_REVIEW_REQUIRED |
| Direct responding outcome + inw0 | Recorded nonresponse versus response disagreement | Reject known zero | CONFIRMED_SYNTHETIC_REPRODUCTION; cause/source precedence PRIVATE_REVIEW_REQUIRED |
| Direct responding outcome + inw missing | No verified participation evidence | Reject with original combined issue | CONFIRMED_SYNTHETIC_REPRODUCTION; missing is not zero; interpretation UNRESOLVED |
| Any invalid participation | Not a documented response flag | Earlier participation-domain rejection | CONFIRMED_SYNTHETIC_REPRODUCTION; successful diagnostic cannot contain this as an accepted source state |
| `askpx=1` without explicit proxy outcome | Proxy classification inferred by fallback | Proxy branch; reject if inw0/missing | CONFIRMED_SYNTHETIC_REPRODUCTION; joint completion/precedence UNRESOLVED, PRIVATE_REVIEW_REQUIRED |
| Explicit proxy outcome + proxy-no | Competing recorded indicators | Still proxy; diagnostic flags explicit proxy disagreement | CONFIRMED_SYNTHETIC_REPRODUCTION; no silent precedence correction |
| Missing/unknown Core outcome without proxy evidence | Incomplete interview evidence | Unknown; no automatic responding conflict | CONFIRMED_SYNTHETIC_REPRODUCTION; never disease-negative by default |
| No Core record + inw0 | No matched Core response is compatible with nonresponse | No Core target check | CONFIRMED_SYNTHETIC_REPRODUCTION; universe/linkage review remains necessary |
| No Core record + inw1 or missing | Missing coverage or unresolved response | Does not prove an interview or clinical negative | PRIVATE_REVIEW_REQUIRED; no new join by this tool |
| Documented nonresponse/death outcome + inw0, no fallback | Compatible nonresponse status | Not a personal outcome interval | CONFIRMED_PUBLIC_DOCUMENTATION plus synthetic behavior; death is not a nonevent |
| Nonresponse/death outcome + inw1 or fallback | Inconsistent or ambiguous evidence | Diagnostic ambiguity or fallback behavior | PRIVATE_REVIEW_REQUIRED; do not delete the wave or infer onset/absence |
| Invalid/duplicate linkage | Invalid input, not usable matched histories | Original diagnostic fails before successful output | CONFIRMED_SYNTHETIC_REPRODUCTION; failed artifacts cannot masquerade as completed evidence |
| Unmatched Core people outside H universe | Coverage mismatch, not proof of erroneous linkage | Existing private per-wave count | PRIVATE_REVIEW_REQUIRED; no person-level keys exported |

The completed report has separate raw-state **marginals**, not a full joint raw-code cross-tabulation. It may not establish which precise outcome code was paired with each fallback cell. The tool records this information limit rather than inventing a causal resolution. A first-conflict record is checked for consistency with its cell; without person keys the historical row order cannot be independently reconstructed, and it is not proof of a common cause.

Every observed cell becomes an unresolved family worksheet entry, including apparently consistent cells. All waves require documentary/lineage review. Invalid states are distinguished in the reference matrix but an alleged successful report containing them is refused, consistent with the original completed-diagnostic contract.
