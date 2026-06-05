# PARALLAX  --  API Design Specification
## Complete REST API Reference

> **V2 NOTE:** This document is part of the original planning suite. The authoritative
> design now lives in:
> - `PARALLAX_VISION.md`  --  anchor vision document
> - `02b_ARCHITECTURE_REVISED.md`  --  revised architecture with hypothesis-driven loop
> - `02_ARCHITECTURE.md`  --  original (this doc references it)
>
> Key v2 additions: AI Reverse Engineering Workbench, Hypothesis Loop, AI-Guided
> Dynamic Exploration, Adaptive Hook Planning, Malware Pattern Memory, Risk
> Calibration Engine, IRT distillation, Fraud Attack Chain, Approval Modes.
> Read `PARALLAX_VISION.md` first for the anchor view.

---

---

## 1. API Design Principles

1. **RESTful**  --  resource-oriented, HTTP semantics
2. **Versioned**  --  `/api/v1/` prefix, future-proof
3. **Async-first**  --  long-running analyses return submission_id, poll for status
4. **OpenAPI 3.1**  --  auto-generated docs at `/docs`
5. **Pydantic schemas**  --  request/response validation
6. **Structured errors**  --  consistent error format across all endpoints
7. **Webhooks**  --  push notifications for completion + alerts
8. **Auth**  --  JWT bearer tokens (OIDC compatible)

---

## 2. Authentication

### 2.1 Token-based (JWT)

```http
Authorization: Bearer <jwt_token>
```

- JWT signed with RS256
- Issued by bank's IdP (OIDC integration)
- Claims: `sub`, `roles`, `exp`, `iat`
- Roles: `analyst`, `admin`, `auditor`, `service`

### 2.2 API Key (for service-to-service)

```http
X-API-Key: <key>
```

- For: MISP sync, webhooks out, internal microservices
- Rotated quarterly

---

## 3. Endpoints  --  Ingestion

### 3.1 Submit APK for Analysis

```http
POST /api/v1/analyze
Content-Type: multipart/form-data
Authorization: Bearer <jwt>

--boundary
Content-Disposition: form-data; name="apk_file"; filename="sample.apk"
Content-Type: application/vnd.android.package-archive

<binary>
--boundary
Content-Disposition: form-data; name="source"

honeypot_whatsapp
--boundary
Content-Disposition: form-data; name="priority_hint"

high
--boundary
Content-Disposition: form-data; name="tags"

["smishing_target_sbi", "whatsapp_distribution"]
--boundary
```

**Response 202 Accepted:**
```json
{
  "submission_id": "0192f8a3-7b9c-7c8e-9d4f-1a2b3c4d5e6f",
  "apk_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "triage_score": 78,
  "priority": "HIGH",
  "eta_seconds": 720,
  "status_url": "/api/v1/analysis/0192f8a3-7b9c-7c8e-9d4f-1a2b3c4d5e6f",
  "stream_url": "/api/v1/analysis/0192f8a3-7b9c-7c8e-9d4f-1a2b3c4d5e6f/events"
}
```

### 3.2 Submit APK via Hash (already uploaded)

```http
POST /api/v1/analyze/hash
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "apk_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "source": "internal_mdm",
  "tags": ["sideloaded", "internal_device"]
}
```

**Response 202:** Same as above (analysis re-triggered if needed).

### 3.3 Bulk Submit

```http
POST /api/v1/analyze/bulk
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "apks": [
    {"sha256": "abc...", "source": "misp_feed"},
    {"sha256": "def...", "source": "misp_feed"},
    {"sha256": "ghi...", "source": "misp_feed"}
  ]
}
```

**Response 202:**
```json
{
  "batch_id": "batch-uuid",
  "submissions": [
    {"submission_id": "sub-1", "sha256": "abc...", "priority": "CRITICAL"},
    {"submission_id": "sub-2", "sha256": "def...", "priority": "HIGH"},
    {"submission_id": "sub-3", "sha256": "ghi...", "priority": "MEDIUM"}
  ]
}
```

---

## 4. Endpoints  --  Status & Results

### 4.1 Get Analysis Status

```http
GET /api/v1/analysis/{submission_id}
Authorization: Bearer <jwt>
```

**Response 200:**
```json
{
  "submission_id": "0192f8a3-7b9c-7c8e-9d4f-1a2b3c4d5e6f",
  "status": "analyzing",
  "progress_pct": 65,
  "current_stage": "ai_cortex",
  "stages": {
    "ingestion": {"status": "completed", "duration_seconds": 2},
    "triage": {"status": "completed", "duration_seconds": 1.5},
    "static": {"status": "completed", "duration_seconds": 234},
    "dynamic": {"status": "completed", "duration_seconds": 487},
    "visual": {"status": "completed", "duration_seconds": 87},
    "ai_cortex": {"status": "in_progress", "started_at": "2026-06-04T10:35:00Z"},
    "taig_update": {"status": "pending"},
    "report": {"status": "pending"}
  },
  "eta_seconds": 45,
  "submitted_at": "2026-06-04T10:25:00Z",
  "started_at": "2026-06-04T10:25:30Z"
}
```

### 4.2 Get Full Analysis Result

```http
GET /api/v1/analysis/{submission_id}/result
Authorization: Bearer <jwt>
```

**Response 200:**
```json
{
  "submission_id": "...",
  "apk_metadata": {
    "package": "com.fake.sbi",
    "app_name": "SBI YONO Update",
    "version": "1.2.3",
    "size_bytes": 4823094,
    "min_sdk": 21,
    "target_sdk": 33,
    "signer": "CN=Fake",
    "certificate_fingerprint": "..."
  },
  "triage": {
    "pre_score": 78,
    "priority": "HIGH",
    "flag_reasons": ["accessibility_service_request", "sms_capable"]
  },
  "static": { /* full static analysis JSON */ },
  "dynamic": { /* full dynamic analysis JSON */ },
  "visual": { /* full visual analysis JSON */ },
  "ai_cortex": {
    "verdict": "CRITICAL",
    "risk_score": 94,
    "confidence": 0.92,
    "components": {
      "permission_abuse": 0.95,
      "behavioral_indicators": 0.98,
      "code_intent_risk": 0.92,
      "network_exfiltration": 0.94,
      "brand_impersonation": 0.97
    },
    "attck_techniques": [
      {"id": "T1412", "name": "Capture SMS Messages", "confidence": 0.94},
      {"id": "T1417", "name": "Input Capture", "confidence": 0.89},
      {"id": "T1655", "name": "Input Injection", "confidence": 0.91}
    ],
    "threat_actor": {
      "candidate": "GoldFactory",
      "confidence": 0.78,
      "alternatives": [{"name": "CloudAtlas", "confidence": 0.34}]
    },
    "campaign_links": [
      {"campaign": "SBI-YONO-2024-Q4", "similarity": 0.91}
    ]
  },
  "iocs": {
    "hashes": ["sha256:abc..."],
    "ips": ["185.220.101.47"],
    "domains": ["fake-sbi.com"],
    "certificates": ["A1:B2:C3:..."]
  }
}
```

### 4.3 Get Events Stream (SSE)

```http
GET /api/v1/analysis/{submission_id}/events
Accept: text/event-stream
Authorization: Bearer <jwt>
```

**Server-Sent Events stream:**
```
event: stage_started
data: {"stage": "static", "timestamp": "..."}

event: stage_completed
data: {"stage": "static", "duration_seconds": 234, "summary": "47 permissions, 12 dangerous APIs"}

event: tool_completed
data: {"tool": "androguard", "duration": 12, "findings": 47}

event: alert
data: {"severity": "CRITICAL", "type": "EVASION_SUSPECTED", "message": "..."}
```

### 4.4 Get History (Paginated)

```http
GET /api/v1/history?limit=50&offset=0&since=2026-06-01T00:00:00Z&verdict=CRITICAL
Authorization: Bearer <jwt>
```

**Response 200:**
```json
{
  "total": 1247,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "submission_id": "...",
      "apk_sha256": "...",
      "package": "com.fake.sbi",
      "submitted_at": "2026-06-04T10:25:00Z",
      "verdict": "CRITICAL",
      "risk_score": 94,
      "source": "honeypot_whatsapp"
    }
  ]
}
```

---

## 5. Endpoints  --  Outputs

### 5.1 Download Report (PDF)

```http
GET /api/v1/analysis/{submission_id}/report.pdf
Authorization: Bearer <jwt>
```

**Response 200:** `application/pdf`

### 5.2 Download STIX 2.1 Bundle

```http
GET /api/v1/analysis/{submission_id}/stix
Authorization: Bearer <jwt>
```

**Response 200:** `application/json`
```json
{
  "type": "bundle",
  "id": "bundle--...",
  "objects": [
    {"type": "malware-analysis", "id": "..."},
    {"type": "indicator", "pattern": "[file:hashes.'SHA-256' = 'abc...']"},
    {"type": "attack-pattern", "external_references": [{"external_id": "T1412"}]},
    {"type": "threat-actor", "name": "GoldFactory", "sophistication": "advanced"}
  ]
}
```

### 5.3 Download YARA Rule

```http
GET /api/v1/analysis/{submission_id}/yara
Authorization: Bearer <jwt>
```

**Response 200:** `text/plain` (YARA rule file)

### 5.4 Download Suricata Rule

```http
GET /api/v1/analysis/{submission_id}/suricata
Authorization: Bearer <jwt>
```

**Response 200:** `text/plain`

### 5.5 Download IOCs (CSV/JSON)

```http
GET /api/v1/analysis/{submission_id}/iocs?format=csv
GET /api/v1/analysis/{submission_id}/iocs?format=json
```

### 5.6 Download Fraud Rules

```http
GET /api/v1/analysis/{submission_id}/fraud-rules
Authorization: Bearer <jwt>
```

**Response 200:** Bank-DSL fraud rules (configurable format)

### 5.7 Get Screenshots (list)

```http
GET /api/v1/analysis/{submission_id}/screenshots
Authorization: Bearer <jwt>
```

**Response 200:**
```json
{
  "screenshots": [
    {"id": "ss-1", "url": "/files/ss-1.png", "timestamp": "...", "stage": "login_screen"},
    {"id": "ss-2", "url": "/files/ss-2.png", "timestamp": "...", "stage": "otp_request"}
  ]
}
```

### 5.8 Get Screenshot File

```http
GET /api/v1/files/screenshots/{screenshot_id}
Authorization: Bearer <jwt>
```

**Response 200:** `image/png` (or jpeg)

### 5.9 Get Decompiled Code

```http
GET /api/v1/analysis/{submission_id}/decompiled
Authorization: Bearer <jwt>
```

**Response 200:** ZIP of decompiled Java

### 5.10 Get ATT&CK Navigator Layer

```http
GET /api/v1/analysis/{submission_id}/attck-layer
Authorization: Bearer <jwt>
```

**Response 200:** ATT&CK Navigator JSON (importable)

---

## 6. Endpoints  --  TAIG Graph

### 6.1 Execute Cypher Query (read-only)

```http
POST /api/v1/graph/cypher
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "query": "MATCH (a:APK)-[:IMPERSONATES]->(b:BankApp) WHERE b.name = $name RETURN a, b",
  "params": {"name": "SBI YONO"},
  "limit": 100
}
```

**Response 200:**
```json
{
  "results": [
    {"a.sha256": "...", "a.package": "com.fake.sbi", "a.risk_score": 94},
    ...
  ],
  "took_ms": 87,
  "nodes": [...],
  "relationships": [...]
}
```

### 6.2 Find Similar APKs (Vector Search)

```http
POST /api/v1/graph/similar
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "apk_sha256": "abc...",
  "k": 10,
  "min_similarity": 0.7
}
```

**Response 200:**
```json
{
  "matches": [
    {
      "sha256": "def...",
      "package": "com.fake.hdfc",
      "similarity": 0.91,
      "risk_score": 89,
      "family": "GoldPickaxe"
    }
  ]
}
```

### 6.3 Find by IOC

```http
POST /api/v1/graph/find-by-ioc
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "iocs": [
    {"type": "ip", "value": "185.220.101.47"},
    {"type": "domain", "value": "fake-sbi.com"}
  ]
}
```

**Response 200:** List of APKs containing these IOCs

### 6.4 Get Lineage Tree

```http
GET /api/v1/graph/lineage/{apk_sha256}
Authorization: Bearer <jwt>
```

**Response 200:** EVOLVED_FROM tree as JSON

### 6.5 Get Campaign Details

```http
GET /api/v1/graph/campaign/{campaign_id}
Authorization: Bearer <jwt>
```

**Response 200:** Campaign metadata + member APKs

---

## 7. Endpoints  --  Threat Hunting

### 7.1 Structured Hunt

```http
POST /api/v1/hunt
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "filters": {
    "target_sector": "Banking",
    "target_region": "IN",
    "time_range": "P30D",
    "min_risk_score": 70,
    "verdict": ["MALICIOUS", "CRITICAL"]
  },
  "include_attribution": true,
  "include_campaign_links": true
}
```

**Response 200:**
```json
{
  "matches": [...],
  "total": 47,
  "campaigns": [...],
  "threat_actors": [...],
  "summary": "47 APKs targeting Indian banking sector in last 30 days, attributed to 3 distinct threat actors, 2 active campaigns"
}
```

### 7.2 Save Hunt (named query)

```http
POST /api/v1/hunt/saved
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "name": "Daily IN Banking Threat Check",
  "filters": {...},
  "schedule": "0 9 * * *",
  "alert_webhook": "https://..."
}
```

### 7.3 List Saved Hunts

```http
GET /api/v1/hunt/saved
Authorization: Bearer <jwt>
```

---

## 8. Endpoints  --  Webhooks (incoming)

Banks can register webhooks to receive push notifications:

```http
POST /api/v1/webhooks
Content-Type: application/json
Authorization: Bearer <jwt>

{
  "name": "Critical Verdict to SIEM",
  "url": "https://siem.bank.com/parallax-webhook",
  "events": ["analysis.critical_verdict", "campaign.detected", "attribution.matched"],
  "secret": "shared-secret-for-signing",
  "active": true
}
```

**Webhook delivery payload (POSTed to bank's URL):**
```json
{
  "event": "analysis.critical_verdict",
  "timestamp": "2026-06-04T10:35:00Z",
  "data": {
    "submission_id": "...",
    "apk_sha256": "...",
    "package": "com.fake.sbi",
    "risk_score": 94,
    "verdict": "CRITICAL",
    "report_url": "/api/v1/analysis/.../report.pdf",
    "iocs": {...}
  },
  "signature": "sha256=..."
}
```

**Signature verification:**
```python
expected = hmac.new(secret.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
```

---

## 9. Endpoints  --  Admin

### 9.1 Stats Overview

```http
GET /api/v1/admin/stats
Authorization: Bearer <jwt>  (admin role)
```

**Response 200:**
```json
{
  "analyses_total": 12453,
  "analyses_today": 47,
  "avg_latency_seconds": 542,
  "verdict_distribution": {
    "BENIGN": 8234,
    "SUSPICIOUS": 2134,
    "MALICIOUS": 1743,
    "CRITICAL": 342
  },
  "campaigns_tracked": 23,
  "threat_actors_known": 47,
  "iocs_in_graph": 89234,
  "yara_rules_active": 1247,
  "system_uptime_seconds": 864003,
  "llm_costs_usd_today": 12.34
}
```

### 9.2 Health Check

```http
GET /api/v1/admin/health
```

**Response 200:**
```json
{
  "status": "healthy",
  "components": {
    "api": "ok",
    "database": "ok",
    "redis": "ok",
    "neo4j": "ok",
    "qdrant": "ok",
    "ollama": "ok",
    "minio": "ok",
    "misp": "ok"
  },
  "version": "1.0.0",
  "uptime_seconds": 864003
}
```

### 9.3 System Config

```http
GET /api/v1/admin/config
PUT /api/v1/admin/config
Authorization: Bearer <jwt>  (admin role)
```

---

## 10. Error Format (Consistent Across All Endpoints)

```json
{
  "error": {
    "code": "ANALYSIS_NOT_FOUND",
    "message": "No analysis found for submission_id abc-123",
    "details": {
      "submission_id": "abc-123"
    },
    "request_id": "req-uuid",
    "timestamp": "2026-06-04T10:35:00Z",
    "docs_url": "https://docs.parallax.security/errors/ANALYSIS_NOT_FOUND"
  }
}
```

### Standard Error Codes

| HTTP | Code | Meaning |
|---|---|---|
| 400 | INVALID_REQUEST | Bad input |
| 401 | UNAUTHORIZED | Missing/bad token |
| 403 | FORBIDDEN | Insufficient role |
| 404 | NOT_FOUND | Resource missing |
| 409 | CONFLICT | Duplicate submission |
| 413 | PAYLOAD_TOO_LARGE | APK > 500MB |
| 422 | UNPROCESSABLE | Schema invalid |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server bug |
| 503 | SERVICE_UNAVAILABLE | Dependency down |

---

## 11. Rate Limiting

| Endpoint | Limit |
|---|---|
| POST /analyze | 100/hour per user, 1000/hour per org |
| GET /status | 600/min per user |
| POST /graph/cypher | 60/min per user (expensive query) |
| All others | 1000/hour per user |

Headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1622812800
```

---

## 12. Pagination

All list endpoints use cursor-based pagination:

```http
GET /api/v1/history?limit=50&cursor=eyJzdGF0dXMiOiJjb21wbGV0ZWQiLCJpZCI6Ii4uLiJ9
```

Response:
```json
{
  "items": [...],
  "next_cursor": "eyJzdGF0dXMiOiJjb21wbGV0ZWQiLCJpZCI6Ii4uLiJ9",
  "has_more": true
}
```

---

## 13. Webhook Events Catalog

| Event | Trigger |
|---|---|
| `analysis.submitted` | New analysis queued |
| `analysis.started` | Worker picked up |
| `analysis.stage_completed` | Each major stage done |
| `analysis.completed` | Full pipeline done |
| `analysis.critical_verdict` | Risk score >= 90 |
| `analysis.failed` | Pipeline error |
| `campaign.detected` | New campaign cluster found |
| `campaign.updated` | Existing campaign grew |
| `attribution.matched` | APK attributed to known actor |
| `yara_rule.generated` | New auto-generated rule |
| `ioc.published` | IOCs pushed to MISP |
| `system.alert` | System-level alerts |

---

## 14. SDK Examples

### Python

```python
import parallax_sdk

client = parallax_sdk.Client(
    base_url="https://parallax.bank.com",
    api_key="..."
)

# Submit APK
with open("suspicious.apk", "rb") as f:
    result = client.analyze.upload(f, source="manual", tags=["sbi_target"])

# Wait for completion
final = client.analyze.wait_for_completion(result.submission_id, timeout=900)

# Download outputs
report = client.analysis.download_report(final.submission_id)
iocs = client.analysis.get_iocs(final.submission_id, format="csv")

# Graph query
matches = client.graph.cypher(
    "MATCH (a:APK)-[:IMPERSONATES]->(b:BankApp) WHERE b.name = $n RETURN a",
    params={"n": "SBI YONO"}
)
```

### cURL

```bash
# Submit
curl -X POST https://parallax.bank.com/api/v1/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "apk_file=@suspicious.apk" \
  -F "source=honeypot" \
  -F "tags=[\"smishing\"]"

# Status
curl https://parallax.bank.com/api/v1/analysis/$ID \
  -H "Authorization: Bearer $TOKEN"

# Download STIX
curl https://parallax.bank.com/api/v1/analysis/$ID/stix \
  -H "Authorization: Bearer $TOKEN" -o report.stix
```

### Webhook Receiver (Python)

```python
from flask import Flask, request
import hmac, hashlib

app = Flask(__name__)
SECRET = b"shared-secret"

@app.post("/parallax-webhook")
def receive():
    payload = request.get_data()
    sig = request.headers.get("X-PARALLAX-Signature", "")
    expected = "sha256=" + hmac.new(SECRET, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return "bad signature", 401
    
    event = request.json
    if event["event"] == "analysis.critical_verdict":
        # Trigger fraud rule deployment
        deploy_fraud_rule(event["data"])
    return "ok", 200
```

---

## 15. OpenAPI Spec Generation

FastAPI auto-generates OpenAPI 3.1 spec at `/openapi.json`. Use to generate:
- Client SDKs (openapi-generator)
- Postman collections
- API documentation portal

---

## 16. V2 Resources -- Investigation Loop APIs

### 16.1 Hypotheses

**Resource:** `Hypothesis` -- a claim the investigation engine forms and tests

```
GET    /api/v1/analyses/{submission_id}/hypotheses
       Returns all hypotheses for an investigation, ordered by formed_at.
       Query params:
         ?status=CONFIRMED|REJECTED|UNRESOLVED|PENDING
         ?expose_in_irt=true  (only IRT-visible ones)

GET    /api/v1/hypotheses/{hypothesis_id}
       Returns a single hypothesis with full internal trace.
       Requires role: analyst | auditor (not available to "service" role)

Response schema (single hypothesis):
{
  "hypothesis_id": "H1-abc12345-def67890",
  "apk_sha256": "...",
  "claim": "Accessibility service abuse for overlay attack",
  "category": "behavioral",
  "status": "CONFIRMED",          // PENDING | CONFIRMED | REJECTED | UNRESOLVED
  "initial_confidence": 0.85,
  "final_confidence": 0.98,
  "expose_in_irt": true,
  "irt_label": "Accessibility overlay attack confirmed",
  "formed_by_agent": "triage_agent",
  "formed_at": "2025-01-15T10:22:01Z",
  "resolved_at": "2025-01-15T10:24:47Z",
  "spawned_from": null,
  "experiments": [
    {
      "experiment_id": "E1-H1-abc-001",
      "type": "static_check",
      "description": "Check for AccessibilityService subclass in decompiled code",
      "tool_used": "re_workbench",
      "result": "CONFIRMED",
      "result_summary": "AccessibilityService subclass found: com.fake.sbi.AccessibilityStealer",
      "duration_ms": 1240
    },
    {
      "experiment_id": "E2-H1-abc-002",
      "type": "dynamic_test",
      "description": "Install mock SBI YONO and bring to foreground",
      "tool_used": "droidbot_gpt",
      "result": "CONFIRMED",
      "result_summary": "Overlay drawn at T+22s on top of mock SBI YONO",
      "duration_ms": 22000
    }
  ],
  // Note: raw_output and failed_attempts NOT returned in API response.
  // Available only via internal audit endpoint (requires auditor role + trace_id).
  "observations_count": 3
}

GET /api/v1/analyses/{submission_id}/hypotheses/irt
    Returns only IRT-ready hypotheses (expose_in_irt=true, status CONFIRMED or UNRESOLVED).
    This is the clean set the report generator uses.

Response:
{
  "submission_id": "...",
  "irt_hypotheses": [
    {
      "status": "CONFIRMED",
      "irt_label": "Accessibility overlay attack confirmed",
      "final_confidence": 0.98,
      "evidence_summary": "Static + dynamic verification with mock SBI installation"
    },
    {
      "status": "UNRESOLVED",
      "irt_label": "Possible crypto wallet targeting",
      "unresolved_reason": "No wallet app present in test environment",
      "recommended_next_step": "Re-run with Unocoin or Zebpay app installed"
    }
  ]
}
```

---

### 16.2 Experiments

**Resource:** `Experiment` -- one action taken to test a Hypothesis

```
GET  /api/v1/hypotheses/{hypothesis_id}/experiments
     Returns all experiments for a hypothesis, ordered by started_at.

GET  /api/v1/experiments/{experiment_id}
     Returns one experiment. raw_output field requires auditor role.

Response schema:
{
  "experiment_id": "E2-H1-abc-002",
  "hypothesis_id": "H1-abc12345-def67890",
  "type": "dynamic_test",
  "description": "Install mock SBI YONO and bring to foreground",
  "tool_used": "droidbot_gpt",
  "agent": "dynamic_explorer",
  "started_at": "2025-01-15T10:23:44Z",
  "completed_at": "2025-01-15T10:24:06Z",
  "duration_ms": 22000,
  "result": "CONFIRMED",
  "result_summary": "Overlay drawn at T+22s on top of mock SBI YONO",
  "evidence_citations": ["screen_5.png", "frida_hook_T22.json"],
  "failed_attempts": []
  // raw_output: omitted unless ?include_raw=true AND role=auditor
}
```

---

### 16.3 Observations

**Resource:** `Observation` -- a real-time event fired during dynamic analysis

```
GET  /api/v1/analyses/{submission_id}/observations
     Returns all runtime observations, ordered by timestamp_offset_ms.
     Query params:
       ?type=OVERLAY_DRAWN|NETWORK_POST|SMS_INTERCEPTED|...
       ?min_confidence=0.8
       ?updates_hypothesis={hypothesis_id}

Response:
{
  "observations": [
    {
      "observation_id": "obs-001",
      "observation_type": "OVERLAY_DRAWN",
      "timestamp_offset_ms": 22000,
      "hook_source": "accessibility_abuse.js",
      "target_package": "com.sbi.lotus",
      "confidence": 0.98,
      "updates_hypothesis": "H1-abc12345-def67890",
      "update_direction": "CONFIRMS"
      // raw_data: omitted by default. Include with ?include_raw=true + auditor role.
    },
    {
      "observation_id": "obs-002",
      "observation_type": "NETWORK_POST",
      "timestamp_offset_ms": 27000,
      "hook_source": "network_logger.js",
      "target_package": null,
      "confidence": 0.99,
      "updates_hypothesis": "H2-abc12345-xyz12345",
      "update_direction": "CONFIRMS"
    }
  ],
  "total": 14
}
```

---

### 16.4 Hook Plans

**Resource:** `HookPlan` -- the adaptive Frida instrumentation plan for a session

```
GET  /api/v1/analyses/{submission_id}/hook-plan
     Returns the hook plan as it stood at the END of the session
     (includes any mid-run additions).

Response:
{
  "submission_id": "...",
  "hooks": [
    {
      "script": "accessibility_abuse.js",
      "targets": ["AccessibilityService", "AccessibilityEvent"],
      "capture": ["package_transitions", "overlay_windows", "event_text"],
      "enabled_at": "static",     // "static" = pre-planned; "dynamic" = added mid-run
      "enabled_at_ms": null,      // null if pre-planned
      "fired_count": 4
    },
    {
      "script": "dynamic_class_loader.js",
      "targets": ["DexClassLoader", "PathClassLoader"],
      "capture": ["loaded_class_names", "source_paths"],
      "enabled_at": "dynamic",    // added mid-run
      "enabled_at_ms": 45000,     // added when DEX_CLASS_LOADED observation fired
      "fired_count": 1
    }
  ],
  "hooks_pre_planned": 4,
  "hooks_added_mid_run": 1,
  "total_hooks": 5
}

POST /api/v1/sessions/{session_id}/hook-plan/update
     Allows the Hook Planning Agent to add a hook mid-session.
     Internal use only (service role). Not exposed to analysts.

Body:
{
  "script": "crypto_extraction.js",
  "reason": "CRYPTO_API_FIRED observation at T+60s",
  "triggered_by_observation": "obs-007"
}
```

---

### 16.5 Investigation Reasoning Trace (IRT)

**Resource:** `IRT` -- the clean external investigation trace for report consumption

```
GET  /api/v1/analyses/{submission_id}/irt
     Returns the distilled IRT. This is what analysts and the report generator see.
     Internal traces are NOT returned here -- use /audit-trace for those.

Response:
{
  "submission_id": "...",
  "apk_sha256": "...",
  "generated_at": "2025-01-15T10:30:00Z",
  "generated_by": "synthesis_agent",
  "confirmed": [
    {
      "label": "Accessibility overlay attack",
      "description": "The APK draws a pixel-perfect overlay over SBI YONO, capturing user credentials via fake login form.",
      "confidence": 0.98,
      "evidence": ["Static: AccessibilityService subclass found", "Dynamic: Overlay fired at T+22s"]
    },
    {
      "label": "SMS OTP interception",
      "description": "Broadcast receiver intercepts incoming SMS and posts body to C2 within 200ms.",
      "confidence": 0.99,
      "evidence": ["Static: SmsReceiver with network POST", "Dynamic: Simulated OTP intercepted at T+37s"]
    }
  ],
  "unresolved": [
    {
      "label": "Possible crypto wallet targeting",
      "reason": "No wallet app present in test environment",
      "recommended_next_step": "Re-run with Unocoin or Zebpay app installed"
    }
  ],
  "total_hypotheses_tested": 8,
  "confirmed_count": 4,
  "rejected_count": 3,
  "unresolved_count": 1,
  "internal_trace_id": "tr-abc-20250115-001"
  // Note: rejected hypotheses are deliberately NOT returned here.
  // Use /audit-trace to see all including rejected and partial states.
}

GET  /api/v1/analyses/{submission_id}/audit-trace
     Returns the complete internal trace including rejected hypotheses,
     failed experiments, partial states, intermediate reasoning.
     Requires role: auditor only.
     Used by: deep audit, compliance review, developer debugging.

Response:
{
  "trace_id": "tr-abc-20250115-001",
  "all_hypotheses": [...],      // including rejected and partial
  "all_experiments": [...],     // including failed attempts
  "all_observations": [...],    // raw hook data included
  "agent_reasoning_log": [...], // every agent's internal reasoning step
  "cycle_count": 3,
  "total_duration_ms": 487000,
  "tools_invoked": ["androguard", "jadx", "frida", "droidbot_gpt", "unicorn"]
}
```

---

### 16.6 Fraud Attack Chain

**Resource:** `FraudChain` -- the bank-specific fraud narrative

```
GET  /api/v1/analyses/{submission_id}/fraud-chain
     Returns the full ordered fraud attack chain for this APK.

Response:
{
  "submission_id": "...",
  "apk_sha256": "...",
  "chain_confidence": 0.94,
  "stages": [
    {
      "stage_order": 1,
      "stage_type": "distribution_vector",
      "description": "APK distributed via WhatsApp forwarded message with shortened URL.",
      "evidence": ["honeypot_capture_jan15.json"],
      "attck_techniques": ["T1660"],
      "confidence": 0.87
    },
    {
      "stage_order": 2,
      "stage_type": "brand_impersonation",
      "description": "Impersonates com.sbi.lotus (SBI YONO) with 97% visual similarity.",
      "evidence": ["visual_similarity_score.json", "screen_2.png"],
      "attck_techniques": ["T1655"],
      "confidence": 0.97,
      "target_brand": "com.sbi.lotus"
    },
    {
      "stage_order": 3,
      "stage_type": "permission_acquisition",
      "description": "Requests BIND_ACCESSIBILITY_SERVICE first, then RECEIVE_SMS after 3 interactions.",
      "evidence": ["manifest_analysis.json"],
      "attck_techniques": ["T1624"],
      "confidence": 0.95
    },
    {
      "stage_order": 4,
      "stage_type": "credential_capture",
      "description": "Draws fullscreen overlay matching SBI YONO login when real app is in foreground.",
      "evidence": ["frida_hook_T22.json", "screen_5.png"],
      "attck_techniques": ["T1516", "T1417"],
      "confidence": 0.98
    },
    {
      "stage_order": 5,
      "stage_type": "otp_interception",
      "description": "SMS receiver intercepts OTP and posts to C2 within 200ms.",
      "evidence": ["frida_hook_T37.json"],
      "attck_techniques": ["T1412"],
      "confidence": 0.99
    },
    {
      "stage_order": 9,
      "stage_type": "exfiltration",
      "description": "Credentials and OTP exfiltrated to 185.220.101.47:8080 via HTTP POST, Base64 encoded.",
      "evidence": ["network_capture.pcap", "mitmproxy_T27.json"],
      "attck_techniques": ["T1646"],
      "confidence": 0.99,
      "c2_destinations": ["185.220.101.47:8080", "c2-backup.evil.com"]
    },
    {
      "stage_order": 10,
      "stage_type": "recommended_fraud_control",
      "description": "Block transaction if device has active accessibility service AND app matching com.sbi.yono.* pattern is installed.",
      "recommended_control": "RULE: block_txn IF device.accessibility_service_active AND device.app_installed LIKE 'com.sbi.yono.*'",
      "approval_mode": "HELD",
      "evidence": ["re_workbench_output.json"]
    }
  ]
}
```

---

### 16.7 Approval Decisions

**Resource:** `ApprovalDecision` -- analyst approval/rejection of recommended actions

```
GET  /api/v1/analyses/{submission_id}/approvals
     Returns all recommended actions with their current approval status.

Response:
{
  "submission_id": "...",
  "actions": [
    {
      "action_id": "act-001",
      "action_type": "block_ip",
      "description": "Block 185.220.101.47 at perimeter firewall",
      "approval_mode": "APPROVED",
      "current_status": "PENDING_ANALYST",
      "recommended_by": "synthesis_agent",
      "confidence": 0.99
    },
    {
      "action_id": "act-002",
      "action_type": "add_yara_rule",
      "description": "Add YARA rule BankingTrojan_SBI_Overlay_v3 to library",
      "approval_mode": "AUTO_LOW_RISK",
      "current_status": "AUTO_DEPLOYED",
      "deployed_at": "2025-01-15T10:31:00Z"
    },
    {
      "action_id": "act-003",
      "action_type": "modify_fraud_rule",
      "description": "Add accessibility service block rule to fraud engine",
      "approval_mode": "HELD",
      "current_status": "AWAITING_SENIOR_ANALYST",
      "hold_reason": "Customer-impacting rule. Requires senior analyst sign-off."
    }
  ]
}

POST /api/v1/analyses/{submission_id}/approvals/{action_id}/decide
     Analyst approves or rejects a recommended action.
     Requires role: analyst (APPROVED mode) or admin (HELD mode).

Body:
{
  "decision": "APPROVE" | "REJECT",
  "reason": "Confirmed C2 IP, safe to block",
  "decided_by": "analyst@bank.com"
}

Response:
{
  "action_id": "act-001",
  "decision": "APPROVE",
  "deployed_at": "2025-01-15T11:05:22Z",
  "deployment_result": "Firewall rule added: 185.220.101.47/32 DROP"
}
```

---

*This is the complete PARALLAX API surface -- v1 original + v2 investigation loop resources.*

