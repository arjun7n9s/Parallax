# PARALLAX — API Design Specification
## Complete REST API Reference

---

## 1. API Design Principles

1. **RESTful** — resource-oriented, HTTP semantics
2. **Versioned** — `/api/v1/` prefix, future-proof
3. **Async-first** — long-running analyses return submission_id, poll for status
4. **OpenAPI 3.1** — auto-generated docs at `/docs`
5. **Pydantic schemas** — request/response validation
6. **Structured errors** — consistent error format across all endpoints
7. **Webhooks** — push notifications for completion + alerts
8. **Auth** — JWT bearer tokens (OIDC compatible)

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

## 3. Endpoints — Ingestion

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

## 4. Endpoints — Status & Results

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

## 5. Endpoints — Outputs

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

## 6. Endpoints — TAIG Graph

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

## 7. Endpoints — Threat Hunting

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

## 8. Endpoints — Webhooks (incoming)

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

## 9. Endpoints — Admin

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

*This is the complete API surface for PARALLAX v1.*
