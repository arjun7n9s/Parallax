# Report Guide

PARALLAX reports are evidence-first. Start with the summary, then read the chain that
supports the score.

## Sections

| Section | What To Look For |
|---|---|
| Executive summary | Final verdict, score, confidence, and the most important behaviors. |
| Static evidence | Permissions, receivers, strings, YARA hits, decompiled-code findings, FlowDroid paths. |
| Dynamic evidence | Runtime observations, network behavior, Frida hooks, UI exploration findings. |
| AI reasoning | Agent hypotheses, disagreements, final rationale, and known uncertainty. |
| Fraud chain | Banking-specific sequence such as overlay abuse, SMS interception, C2, exfiltration. |
| Indicators | Domains, URLs, IPs, hashes, package names, certificates, and rules. |
| Recommended actions | Blocking, hunting, containment, and sharing guidance. |

## Analyst Workflow

1. Confirm the package name and SHA-256 match the submitted sample.
2. Read the score and confidence together.
3. Check whether static and dynamic evidence agree.
4. Use the fraud-chain section to decide containment steps.
5. Export STIX/YARA only after reviewing whether indicators are tenant-specific.

## When Evidence Is Missing

PARALLAX degrades rather than fabricating findings. Missing dynamic evidence usually means
the emulator, Frida, proxy, or timeout budget prevented a full run. Missing FlowDroid paths
usually means Android platform jars or the FlowDroid jar were not configured.
