# Verdict Meanings

PARALLAX emits a verdict, a risk score, and confidence. Use all three together.

## Verdicts

| Verdict | Meaning | Typical Action |
|---|---|---|
| `CLEAN` | No strong malicious indicators were found. | Allow only if business context agrees. Keep telemetry. |
| `SUSPICIOUS` | Some malicious or fraud-like behavior exists, but evidence is incomplete or mixed. | Review report evidence, compare with tenant history, consider temporary block. |
| `MALICIOUS` | Multiple high-confidence signals indicate malware, fraud, or abuse. | Block distribution, escalate incident response, share indicators. |

## Scores

Scores are evidence-weighted and should be read as operational priority, not a legal
statement of intent.

| Score Range | Severity | Interpretation |
|---|---|---|
| `0-29` | Low | Likely benign or insufficient evidence. |
| `30-59` | Medium | Needs analyst review. |
| `60-79` | High | Strong fraud or malware indicators. |
| `80-100` | Critical | Multiple severe behaviors or confirmed attack chain. |

## Confidence

Confidence drops when parts of the pipeline degrade, such as FlowDroid being unavailable,
dynamic analysis timing out, or a graph store being offline. A lower-confidence high score
is still important; it means the evidence is risky, but the system wants analyst review
before a final action.

## Family Attribution

Family names come from a combination of code features, dynamic behavior, YARA matches,
threat-intel correlation, and cross-sample similarity. If attribution seems wrong, trust
the evidence sections first and mark the family as analyst-disputed in your case notes.
