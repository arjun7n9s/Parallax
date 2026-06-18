# SOC FAQ

## Is PARALLAX a replacement for manual reverse engineering?

No. It automates repeatable triage, evidence gathering, scoring, and report generation.
Use it to prioritize cases and speed investigation, then escalate severe or ambiguous
samples to a reverse engineer.

## Can I upload live malware?

Yes, but only through the approved upload flow. PARALLAX stores uploaded APKs in quarantine
object storage and executes them only in the analysis sandbox.

## Why did my sample deduplicate?

PARALLAX keys submissions by tenant and SHA-256. If your tenant already analyzed the same
APK, the API returns the existing analysis instead of wasting compute.

## Why is a cloud LLM mentioned?

Admins can choose local-only, cloud, or automatic LLM routing. For strict data-residency
deployments, `LOCAL_ONLY=true` forces all agent calls to local Ollama-compatible models.

## What should I do with `SUSPICIOUS`?

Review the evidence and tenant history. Suspicious verdicts are useful for threat hunting
and temporary controls, but they usually need analyst judgment before permanent blocking.
