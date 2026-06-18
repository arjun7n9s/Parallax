# Getting Started

This guide is for SOC analysts submitting an APK and reading the first result.

## Before You Start

Ask your PARALLAX admin for:

- API base URL, for example `https://parallax.example-bank.internal/api/v1`
- Analyst API key, used as `X-API-Key`
- Tenant name if your organization separates teams or subsidiaries

Never upload customer data unless your bank's internal process allows it. PARALLAX is
designed for APK malware and fraud apps, not arbitrary document storage.

## Submit an APK in the Analyst Console

1. Open the PARALLAX console.
2. Set the API base URL.
3. Paste your analyst API key.
4. Select the APK.
5. Submit and keep the analysis detail page open.

The status should move through:

`queued -> triaging -> static -> dynamic -> reasoning -> delivery -> complete`

If the status remains `queued`, a worker is not running or is not listening on the
`triage` queue. Send the submission ID to your admin.

## Submit with curl

```bash
curl -s \
  -H "X-API-Key: $PARALLAX_API_KEY" \
  -F "file=@sample.apk" \
  https://parallax.example-bank.internal/api/v1/analyze
```

The response contains `submission_id`.

```bash
curl -s \
  -H "X-API-Key: $PARALLAX_API_KEY" \
  https://parallax.example-bank.internal/api/v1/analysis/<submission_id>
```

## Download Artifacts

When status is `complete`, download:

- HTML report for quick review
- PDF report for case management
- STIX bundle for threat-intel tooling
- YARA rule when enough distinctive strings are present
- Fraud-chain and incident-response outputs for containment

Raw APK download uses a short-lived signed quarantine URL. Treat it as malware and
open it only in approved analysis environments.
