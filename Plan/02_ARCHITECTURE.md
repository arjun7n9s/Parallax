# PARALLAX  --  System Architecture
## Complete Technical Design Document

> **V2 NOTE:** This document was the original architecture. A comprehensive revision has been produced as `02b_ARCHITECTURE_REVISED.md` that implements the hypothesis-driven, AI-native vision in `PARALLAX_VISION.md`. Key additions in v2:
> - **AI Reverse Engineering Workbench** (Module 2)  --  structured artifact model, the heart of v2
> - **Hypothesis-Driven Investigation Loop**  --  recursive, not one-pass
> - **AI-Guided Dynamic Exploration** (Module 6)  --  AI-operated, not passive sandbox
> - **Adaptive Hook Planning** (Module 4)  --  Frida plans that update mid-run
> - **Malware Pattern Memory** (Module 9)  --  8-category named subsystem
> - **Risk Calibration Engine** (Module 11)  --  two-layer scoring
> - **Evidence Validator + IRT** (Module 12)  --  clean external trace, verbose internal
> - **Fraud Attack Chain Builder**  --  bank-specific output
> - **Approval Mode Controller**  --  tiered human-in-the-loop
>
> Read **`PARALLAX_VISION.md` first, then `02b_ARCHITECTURE_REVISED.md`** for the authoritative current design. This file is retained for context and module-level technical detail.

---

## 1. System Overview

PARALLAX is a 5-layer, multi-agent, self-evolving malware analysis platform. The architecture follows a **data-flow pipeline** pattern with **feedback loops** for continuous self-improvement.

### 1.1 Design Principles

1. **Separation of concerns**  --  each layer is independently testable and replaceable
2. **Right tool for right job**  --  no single tool does everything well
3. **AI for reasoning, not magic**  --  LLMs interpret, never hallucinate alone
4. **Grounded outputs**  --  every AI claim cites the tool output it came from
5. **Standards-first**  --  STIX 2.1, MITRE ATT&CK, MISP for all outputs
6. **On-premise capable**  --  runs fully locally with Ollama (no cloud calls)
7. **Observable by design**  --  every decision traced via OpenTelemetry
8. **Self-evolving**  --  every APK makes the system measurably smarter

### 1.2 High-Level Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                         PARALLAX PLATFORM                           ║
╠═══════════════════╦═══════════════════════╦═════════════════════════╣
║   LAYER 1         ║   LAYER 2             ║   LAYER 3              ║
║   INGESTION &     ║   MULTI-DIMENSIONAL   ║   AI REASONING         ║
║   TRIAGE          ║   ANALYSIS ENGINE     ║   CORTEX               ║
╠═══════════════════╬═══════════════════════╬═════════════════════════╣
║   LAYER 4         ║                       ║   LAYER 5              ║
║   TAIG            ║                       ║   DELIVERY &           ║
║   KNOWLEDGE GRAPH ║                       ║   ACTION               ║
╚═══════════════════╩═══════════════════════╩═════════════════════════╝
              │                                       │
              └─────────── FEEDBACK LOOP ────────────┘
```

---

## 2. Layer 1  --  Ingestion & Triage

### 2.1 Purpose
Accept APK submissions from multiple sources, perform fast pre-screening, prioritize queue.

### 2.2 Intake Sources

| Source | Mechanism |
|---|---|
| **Analyst API upload** | REST POST /api/v1/analyze (multipart/form-data) |
| **Honeypot auto-capture** | WhatsApp/SMS trap links forward to ingestion API |
| **MISP feed auto-ingest** | Cron pulls new samples from MISP event attachments |
| **Browser extension** | Customer-facing Chrome extension reports suspicious APKs |
| **Email gateway** | MBOX monitoring of bank's abuse@ inbox |
| **Scheduled scan** | Periodic scan of internal MDM-detected sideloaded apps |

### 2.3 Components

```
APK arrives
    │
    ▼
[1] APKiD  ────────────► Packer/protector fingerprint
    │
[2] apkinfo  ───────────► Metadata normalization (size, arch, min SDK)
    │
[3] ssdeep  ────────────► Fuzzy hash for fast similarity pre-check
    │
[4] Certificate check ─► Self-signed? Expired? Unusual issuer?
    │
[5] Triage LLM  ────────► Phi-3 Mini reads manifest+permissions only
    │                       Outputs pre-score (0-100) in <2 seconds
    │                       Outputs priority (LOW/MED/HIGH/CRITICAL)
    │
[6] Priority Queue  ────► Redis-backed Celery queue
    │                       CRITICAL jumps to head
    │
[7] Storage  ────────────► MinIO (S3-compatible) at s3://parallax-apks/
                            Original APK preserved for forensic replay
```

### 2.4 Triage LLM Prompt (Phi-3 Mini)

```
You are a fast mobile threat triage agent. You have <2 seconds to decide priority.

Given this APK's manifest, permissions, and metadata only, output:
{
  "pre_score": <0-100>,
  "priority": "LOW|MEDIUM|HIGH|CRITICAL",
  "kill_chain_stage": "<which MITRE ATT&CK initial access vector this suggests>",
  "flag_reasons": ["<reason1>", ...]
}

Be conservative  --  false negatives cost money, false positives cost analyst time.
When in doubt, escalate priority.
```

### 2.5 Pre-Check Against Known-Bad

Before full analysis, ssdeep fuzzy hash is checked against the existing hash database. If similarity > 90% to a known-malicious sample, the analysis can be **fast-pathed**  --  only generate a delta report against the previous sample.

### 2.6 Data Structures

**Ingestion request (JSON after upload):**
```json
{
  "submission_id": "uuid-v7",
  "submitted_at": "2026-06-04T10:23:45Z",
  "source": "honeypot_whatsapp",
  "apk_sha256": "abc123...",
  "apk_size_bytes": 4823094,
  "ssdeep_hash": "12288:...",
  "apkid": {
    "packer": "DexGuard",
    "anti_vm": true,
    "compiler": "ART"
  },
  "certificate": {
    "fingerprint": "...",
    "self_signed": true,
    "validity_days": 30
  },
  "triage": {
    "pre_score": 78,
    "priority": "HIGH",
    "flag_reasons": ["accessibility_service", "sms_intercept_capable"]
  }
}
```

### 2.7 Tech Choices

- **FastAPI**  --  async REST ingestion
- **Celery + Redis**  --  distributed task queue
- **MinIO**  --  S3-compatible APK storage (retain originals for 90 days)
- **Ollama**  --  local LLM serving
- **APKiD**, **ssdeep**  --  pre-screening
- **PostgreSQL**  --  submission metadata, audit log

---

## 3. Layer 2  --  Multi-Dimensional Analysis Engine

Three **parallel analysis tracks** run simultaneously on the same APK. Each produces a structured JSON output that feeds Layer 3.

### 3.1 Track A  --  Deep Static Analysis

**Goal:** Understand what the APK *intends* to do without running it.

```
INPUT: APK file
  │
  ├─► androguard (Python library)
  │     └─ Extract: permissions, components, intents, signatures
  │
  ├─► jadx (Java decompiler)
  │     └─ Convert DEX -> readable Java source
  │     └─ Output: src/ tree for LLM consumption
  │
  ├─► apktool (smali decompiler)
  │     └─ Decode resources, manifest, smali
  │
  ├─► r2pipe (Radare2)
  │     └─ Binary-level analysis of native .so libraries
  │     └─ Look for hardcoded keys, hidden strings, crypto constants
  │
  ├─► FlowDroid (taint analysis)
  │     └─ Trace data flow: SOURCE (user input) -> SINK (network send)
  │     └─ Proves: "user's bank PIN travels to remote server"
  │
  ├─► Semgrep (custom banking rules)
  │     └─ Pattern-match: SMS interception, overlay attacks, keyloggers
  │     └─ Rules in: rules/banking_malware.yml
  │
  ├─► YARA (rule engine)
  │     └─ Match against curated rule set + auto-generated rules
  │     └─ Catches known malware families
  │
  ├─► BinDiff / Diaphora (binary similarity)
  │     └─ Compare code against samples in TAIG
  │     └─ Returns: "68% code similarity to GoldPickaxe.B"
  │
  ├─► Unicorn Engine (micro-emulation)
  │     └─ Emulate obfuscated decryptor routines
  │     └─ Reveals: hidden URLs, decrypted stage-2 URLs
  │
  ├─► simplify (deobfuscator)
  │     └─ Undo ProGuard / DexGuard / Allatori transformations
  │
  └─► NetworkX (graph analysis)
        └─ Build permission-API-call graph
        └─ Compute centrality scores, dangerous permission clusters
```

**Output JSON:**
```json
{
  "static_analysis": {
    "permissions": [
      {"name": "BIND_ACCESSIBILITY_SERVICE", "risk": "CRITICAL", "category": "ui_hijack"},
      {"name": "RECEIVE_SMS", "risk": "HIGH", "category": "sms_intercept"}
    ],
    "api_calls": [
      {"class": "android.telephony.SmsManager", "method": "sendTextMessage", "risk": "HIGH"},
      {"class": "android.accessibilityservice.AccessibilityService", "method": "performGlobalAction", "risk": "CRITICAL"}
    ],
    "hardcoded_strings": {
      "urls": ["hxxps://fake-sbi[.]com", "hxxp://185.220.x.x:8080/payload"],
      "ip_addresses": ["185.220.x.x"]
    },
    "certificate": {"self_signed": true, "validity_days": 30, "issuer": "unknown"},
    "obfuscation": {"packer": "DexGuard", "obfuscation_level": "high"},
    "binary_similarity": [
      {"sample_sha256": "abc...", "family": "GoldPickaxe", "similarity": 0.68}
    ],
    "taint_flows": [
      {"source": "EditText.onTextChanged", "sink": "HttpURLConnection.connect", "data": "user_credentials", "confidence": 0.94}
    ],
    "semgrep_matches": [
      {"rule": "sms-interception", "file": "MainActivity.smali", "line": 234, "severity": "error"}
    ],
    "yara_matches": [
      {"rule": "BankingTrojan_GoldPickaxe_B", "matches": 7}
    ],
    "permission_graph_centrality": {
      "BIND_ACCESSIBILITY_SERVICE": 0.91,
      "RECEIVE_SMS": 0.87
    }
  }
}
```

### 3.2 Track B  --  Dynamic Behavioral Analysis

**Goal:** Understand what the APK *actually does* at runtime.

```
INPUT: APK + Frida scripts
  │
  ├─► Android AVD orchestration
  │     └─ Headless emulator (x86_64 image)
  │     └─ Network: isolated VLAN
  │     └─ mitmproxy CA pre-installed for SSL interception
  │
  ├─► DroidBot-GPT (UI automation)
  │     └─ LLM-driven user simulation
  │     └─ Generates realistic input sequences
  │     └─ Explores app: launch, click, scroll, type, login
  │     └─ Can ask: "what would a user do next?" -> executes
  │
  ├─► Frida instrumentation (comprehensive)
  │     └─ Hooks: crypto APIs, SMS, clipboard, accessibility, camera, mic
  │     └─ hooks/accessibility_abuse.js
  │     └─ hooks/sms_interception.js
  │     └─ hooks/keylogger.js
  │     └─ hooks/crypto_extraction.js
  │     └─ hooks/network_call_logger.js
  │     └─ hooks/dynamic_class_loader.js
  │
  ├─► mitmproxy + Scapy
  │     └─ Capture all network traffic
  │     └─ Decode HTTP/HTTPS with installed CA
  │     └─ Custom protocol dissectors for non-HTTP C2
  │     └─ Extract: endpoints, payloads, encryption, beacon patterns
  │
  ├─► Strace / ltrace
  │     └─ System call tracing
  │     └─ File operations, process spawning, IPC abuse
  │     └─ Native library calls
  │
  └─► Mutation testing framework
        └─ Re-run with different:
          - Locale (en-IN, hi-IN, ur-PK, en-NG)
          - SIM operator prefix (+91, +92, +234)
          - Time of day (business hours, off hours)
          - Installed apps (banking app present/absent)
        └─ Catches context-aware malware that hides from sandboxes
```

**Output JSON:**
```json
{
  "dynamic_analysis": {
    "execution_duration_seconds": 312,
    "ui_exploration_steps": 47,
    "screens_visited": [
      {"screen_id": 1, "description": "Fake SBI YONO login", "screenshot": "s3://.../screen_1.png"},
      {"screen_id": 2, "description": "OTP request overlay", "screenshot": "s3://.../screen_2.png"}
    ],
    "events": [
      {"t": 0.2, "type": "PERMISSION_REQUEST", "detail": "BIND_ACCESSIBILITY_SERVICE"},
      {"t": 0.4, "type": "SMS_READ", "detail": "intercepted OTP: 847291"},
      {"t": 0.6, "type": "WEBVIEW_OPEN", "detail": "hxxps://fake-sbi.com"},
      {"t": 0.9, "type": "KEYLOG_HOOK", "detail": "EditText password field"},
      {"t": 1.2, "type": "NETWORK_POST", "detail": "185.220.x.x:8080, payload=base64"}
    ],
    "frida_hooks_triggered": [
      {"hook": "sms_interception", "fired": 3, "captured_otps": 1},
      {"hook": "accessibility_abuse", "fired": 12, "captured_text": ["847291", "user@email.com"]}
    ],
    "network_traffic": {
      "total_connections": 8,
      "unique_destinations": ["185.220.x.x:8080", "fake-sbi.com:443"],
      "encrypted_payloads": 4,
      "beacon_interval_seconds": 60
    },
    "mutation_test_results": {
      "locale_en_IN": {"behavior_change": false, "risk_increase": 0},
      "locale_ur_PK": {"behavior_change": true, "new_c2": "c2.evil.com", "risk_increase": 0.15},
      "banking_app_present": {"behavior_change": true, "overlay_triggered": true, "risk_increase": 0.25}
    },
    "screenshot_count": 47
  }
}
```

### 3.3 Track C  --  Visual Intelligence

**Goal:** Detect malicious UI that code analysis misses.

```
INPUT: Screenshot stream from Track B
  │
  ├─► Screenshot capture
  │     └─ Every screen state during dynamic run
  │     └─ Stored in MinIO with metadata
  │
  ├─► LLaVA-OneVision / InternVL (multimodal LLM)
  │     └─ For each screenshot:
  │         - "Is this UI a clone of a legitimate app?"
  │         - "Are there overlay elements suspicious?"
  │         - "Does this match a known bank's UI?"
  │         - "Are accessibility-text descriptions missing/suspicious?"
  │
  ├─► Brand impersonation matching
  │     └─ Embed screenshots via CLIP / multimodal encoder
  │     └─ Compare to reference screenshots of 100+ legitimate bank apps
  │     └─ Returns visual similarity score
  │
  └─► Overlay attack detection
        └─ Diff against known banking app screenshots
        └─ Look for: extra hidden fields, off-position elements
```

**Output JSON:**
```json
{
  "visual_analysis": {
    "screens_analyzed": 47,
    "phishing_overlays_detected": 2,
    "brand_impersonation": [
      {
        "target_app": "com.sbi.lotus",
        "target_name": "SBI YONO",
        "visual_similarity_score": 0.97,
        "evidence_screenshot": "s3://.../screen_5.png",
        "ai_description": "Pixel-perfect clone of SBI YONO login screen. Slight color shift in background gradient and field positioning offset by 4px."
      }
    ],
    "overlay_attacks": [
      {
        "type": "accessibility_overlay",
        "trigger": "when com.sbi.lotus is in foreground",
        "evidence": "Overlay appears with identical UI but different package"
      }
    ],
    "ui_anomalies": [
      {"screen": 2, "anomaly": "Hidden WebView with iframe pointing to phishing domain"},
      {"screen": 7, "anomaly": "Off-screen EditText for credential capture"}
    ]
  }
}
```

### 3.4 Layer 2 Orchestration

Layer 2 is coordinated by a **Celery task graph**:
- Track A: 3-5 minutes (CPU-bound, decompilation-heavy)
- Track B: 5-10 minutes (emulator + UI exploration)
- Track C: 1-2 minutes (parallel to B, consumes screenshots as they're produced)
- All tracks run **in parallel**; Layer 3 waits for all to complete.

**Failure isolation:** Each track has independent error handling. If Track C (visual) fails, the pipeline still produces a useful result. Critical tracks (A, B) are monitored with retries.

---

## 4. Layer 3  --  AI Reasoning Cortex

### 4.1 Purpose
Transform raw tool outputs into a **reasoned verdict** with explainable risk score.

### 4.2 Agent Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    REASONING CORTEX                              │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  CODE           │  │  BEHAVIOR       │  │  INTEL          │  │
│  │  INTERPRETER    │  │  ANALYST        │  │  CORRELATOR     │  │
│  │  AGENT          │  │  AGENT          │  │  AGENT          │  │
│  │                 │  │                 │  │                 │  │
│  │  Model:         │  │  Model:         │  │  Model:         │  │
│  │  DeepSeek-      │  │  Mistral-Large  │  │  LlamaIndex     │  │
│  │  Coder-V2       │  │  or             │  │  RAG over       │  │
│  │  (16B local)    │  │  Llama-3.1-70B  │  │  ATT&CK + MISP  │  │
│  │                 │  │  (local)        │  │                 │  │
│  │  Input:         │  │  Input:         │  │  Input:         │  │
│  │  Decompiled     │  │  Runtime event  │  │  All IOCs +     │  │
│  │  Java/Smali     │  │  stream         │  │  behaviors      │  │
│  │  + static JSON  │  │  + dynamic JSON │  │  + ATT&CK corpus│  │
│  │                 │  │                 │  │                 │  │
│  │  Output:        │  │  Output:        │  │  Output:        │  │
│  │  Intent graph   │  │  Behavior       │  │  ATT&CK map +   │  │
│  │  per code block │  │  narrative      │  │  campaign links │  │
│  │  + risk per     │  │  + risk per     │  │  + attribution  │  │
│  │  function       │  │  event          │  │  confidence     │  │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
│           │                    │                    │            │
│           └──────────┬─────────┴────────────────────┘            │
│                      ▼                                           │
│           ┌─────────────────────┐                                │
│           │   DEBATE LAYER      │                                │
│           │                     │                                │
│           │ "Static says X,     │                                │
│           │  Behavior says Y,   │                                │
│           │  Intel says Z"      │                                │
│           │                     │                                │
│           │ -> Reconcile,        │                                │
│           │   surface contra-   │                                │
│           │   dictions as       │                                │
│           │   high-confidence   │                                │
│           │   alerts            │                                │
│           └──────────┬──────────┘                                │
│                      ▼                                           │
│           ┌─────────────────────┐                                │
│           │  VISUAL INTELLIGENCE│                                │
│           │  AGENT              │                                │
│           │  (LLaVA-OneVision)  │                                │
│           │  Input: screenshots │                                │
│           │  Output: phishing   │                                │
│           │  proof + brand      │                                │
│           │  similarity         │                                │
│           └──────────┬──────────┘                                │
│                      ▼                                           │
│           ┌─────────────────────┐                                │
│           │   SYNTHESIS AGENT   │                                │
│           │                     │                                │
│           │   Model: GPT-4o     │                                │
│           │   or Claude Opus    │                                │
│           │   (API or local)    │                                │
│           │                     │                                │
│           │   Combines all 5    │                                │
│           │   agent outputs     │                                │
│           │   -> final verdict   │                                │
│           │   -> risk score      │                                │
│           │   -> report          │                                │
│           │   -> recommendations │                                │
│           └─────────────────────┘                                │
└──────────────────────────────────────────────────────────────────┘
```

### 4.3 Agent 1  --  Code Interpreter (DeepSeek-Coder-V2)

**Input:** Decompiled Java + static analysis JSON
**Process:**
```python
# Per code block, classify intent
def classify_intent(code_block: str) -> Intent:
    """
    Returns:
        intent: str  (e.g., "SMS_INTERCEPTION", "CREDENTIAL_OVERLAY", "CRYPTO_WALLET_THEFT")
        risk: float  (0-1)
        explanation: str
        evidence_lines: List[int]
        attck_techniques: List[str]  (T1412, T1417, etc.)
    """
```

**Key prompt patterns:**
- Few-shot examples of known banking trojan code
- Output schema enforced via DSPy signature (not raw prompting)
- DSPy optimization: prompts are compiled against labeled samples, not hand-tuned

**Output feeds into:** NetworkX intent graph for the APK

### 4.4 Agent 2  --  Behavior Analyst (Mistral-Large)

**Input:** Runtime event stream + dynamic analysis JSON
**Process:** Interprets the temporal sequence of events into a narrative

**Example output:**
```json
{
  "behavior_narrative": "On launch, the app immediately requests Accessibility Service 
                        permission (T1516). Once granted, it registers a listener that 
                        fires on application foreground/background events. When the user 
                        opens com.sbi.lotus (the real banking app), the malware draws an 
                        overlay window with a pixel-perfect replica of the SBI YONO login 
                        (T1655). User input is captured and forwarded to the C2 server 
                        at 185.220.x.x within 200ms. The legitimate banking app is then 
                        backgrounded.",
  "behavior_risk": 0.95,
  "kill_chain_phases_observed": [
    "TA0001 - Initial Access",
    "TA0009 - Collection",
    "TA0011 - Command and Control"
  ]
}
```

### 4.5 Agent 3  --  Intel Correlator (RAG-based)

**Input:** All IOCs (IPs, domains, hashes, certs) + observed behaviors
**Corpus:**
- MITRE ATT&CK for Mobile (full XML)
- MISP event database
- Internal TAIG historical samples
- Public threat reports (PDFs ingested via LlamaIndex)

**Process:**
```python
# RAG retrieval + LLM synthesis
retrieved = vector_db.similarity_search(iocs, k=20)
attack_mapping = llm.map_behaviors_to_attck(behaviors, retrieved)
attribution = llm.attribute_threat_actor(iocs, retrieved, confidence_threshold=0.6)
```

**Output:**
```json
{
  "attck_mapping": [
    {"technique": "T1412", "name": "Capture SMS Messages", "confidence": 0.94, "evidence": "..."},
    {"technique": "T1417", "name": "Input Capture", "confidence": 0.89, "evidence": "..."},
    {"technique": "T1655", "name": "Input Injection", "confidence": 0.91, "evidence": "..."}
  ],
  "threat_actor_attribution": {
    "candidate": "GoldFactory",
    "confidence": 0.78,
    "evidence": "C2 IP 185.220.x.x was used in 3 prior campaigns attributed to GoldFactory",
    "alternative_candidates": [{"name": "CloudAtlas", "confidence": 0.34}]
  },
  "campaign_links": [
    {"campaign": "SBI-YONO-2024-Q4", "similarity": 0.91, "first_seen": "2024-10-15"}
  ]
}
```

### 4.6 Debate Layer

**The architecturally most important element of the cortex.**

```python
class DebateLayer:
    def arbitrate(self, agent_outputs: Dict) -> ArbitratedVerdict:
        """
        When agents disagree, surface the contradiction.
        Evasion IS the signature.
        """
        verdicts = {
            "static": agent_outputs["code_interpreter"]["verdict"],
            "dynamic": agent_outputs["behavior_analyst"]["verdict"],
            "intel": agent_outputs["intel_correlator"]["verdict"],
            "visual": agent_outputs["visual"]["verdict"]
        }
        
        # Standard case: all agree
        if self._consensus(verdicts):
            return self._consensus_verdict(verdicts)
        
        # Sophisticated case: static clean, dynamic dirty
        if verdicts["static"] < 0.3 and verdicts["dynamic"] > 0.7:
            return ArbitratedVerdict(
                score=0.85,  # elevated due to contradiction
                confidence=0.92,
                flag="POLYMORPHIC_EVASION_SUSPECTED",
                explanation="Static surface appears clean, but runtime behavior is highly 
                            malicious. Classic signature of context-aware or staged malware."
            )
        
        # Other contradiction patterns...
```

### 4.7 Synthesis Agent (GPT-4o or Claude)

**The final reasoner.** Takes all five agent outputs + debate result and produces:

1. **Final risk score (0-100)** with explainable breakdown
2. **Verdict** (BENIGN / SUSPICIOUS / MALICIOUS / CRITICAL)
3. **Confidence interval**
4. **Natural language report** (executive + technical)
5. **Actionable recommendations**

---

## 5. Layer 4  --  TAIG Knowledge Graph

### 5.1 Architecture

PARALLAX uses a **two-graph architecture**:

| Graph | Tool | Purpose |
|---|---|---|
| **Structural Graph** | Neo4j | Relationships, attribution, campaigns, lineage |
| **Semantic Vector Index** | Qdrant | Code-intent embeddings, similarity search |

### 5.2 Neo4j Schema (Full Specification)

**Node types and properties:**

```cypher
// APK node - the central entity
(:APK {
  sha256: "abc123...",              // primary key
  md5: "...",
  package: "com.fake.sbi",
  app_name: "SBI YONO Update",
  version: "1.2.3",
  first_seen: datetime(),
  last_analyzed: datetime(),
  risk_score: 94,
  verdict: "CRITICAL",
  file_size: 4823094,
  min_sdk: 21,
  target_sdk: 33,
  signer: "...",
  submitted_by: "analyst_jdoe"
})

// Permission node
(:Permission {
  name: "android.permission.RECEIVE_SMS",
  risk_level: "HIGH",
  category: "sms"
})

// API call node
(:API {
  fqn: "android.telephony.SmsManager.sendTextMessage",
  class: "SmsManager",
  method: "sendTextMessage",
  sensitivity: "HIGH"
})

// IP address node
(:IPAddress {
  value: "185.220.101.47",
  country: "RO",
  asn: "AS9009",
  reputation: "malicious",
  first_seen_in_parallax: datetime()
})

// Domain node
(:Domain {
  fqdn: "fake-sbi.com",
  registrar: "NameCheap",
  age_days: 14,
  dga_score: 0.2,
  ssl_issuer: "Let's Encrypt"
})

// Certificate node
(:Certificate {
  fingerprint: "A1:B2:C3:...",
  issuer: "CN=Fake,O=Evil Corp",
  self_signed: true,
  valid_from: date(),
  valid_to: date()
})

// Threat actor node
(:ThreatActor {
  name: "GoldFactory",
  aliases: ["GoldFactory APT", "GF-Group"],
  origin: "Unknown",
  first_observed: date(),
  motivation: "financial",
  ttps_summary: "Banking trojans, primarily targeting South Asian banks"
})

// Campaign node
(:Campaign {
  name: "SBI-YONO-2024-Q4",
  start_date: date(),
  end_date: date(),
  target_sector: "Banking",
  target_region: "IN",
  status: "active"
})

// Code blob node (semantic unit)
(:CodeBlob {
  hash: "...",
  semantic_vector: [/* 768-dim */],
  intent_label: "SMS_INTERCEPTION",
  language: "java",
  size_lines: 47
})

// Bank app node (target reference)
(:BankApp {
  package: "com.sbi.lotus",
  name: "SBI YONO",
  bank: "State Bank of India",
  critical: true
})
```

**Relationship types:**

```cypher
(apk:APK)-[:REQUESTS {first_seen: datetime()}]->(perm:Permission)
(apk:APK)-[:CALLS {call_count: 5}]->(api:API)
(apk:APK)-[:COMMUNICATES_WITH {protocol: "https", data_size: 4096}]->(ip:IPAddress)
(apk:APK)-[:COMMUNICATES_WITH]->(domain:Domain)
(apk:APK)-[:IMPERSONATES {confidence: 0.97}]->(bank:BankApp)
(apk:APK)-[:SIGNED_BY]->(cert:Certificate)
(apk:APK)-[:USES_PACKER {name: "DexGuard"}]->(:Packer)
(apk:APK)-[:SHARES_CODE_WITH {similarity: 0.87, method: "BinDiff"}]->(apk2:APK)
(apk:APK)-[:EVOLVED_FROM {generation: 4}]->(apk3:APK)
(apk:APK)-[:CONTAINS_BLOB]->(blob:CodeBlob)
(apk:APK)-[:ATTRIBUTED_TO {confidence: 0.78, method: "infrastructure+code"}]->(actor:ThreatActor)
(apk:APK)-[:PART_OF]->(campaign:Campaign)
(apk:APK)-[:TARGETS_SECTOR]->(sector)
(apk:APK)-[:TARGETS_REGION]->(region)
(campaign:Campaign)-[:ATTRIBUTED_TO]->(actor:ThreatActor)
(campaign:Campaign)-[:USES_INFRASTRUCTURE]->(ip:IPAddress)
(ip:IPAddress)-[:GEOLOCATES_TO]->(country)
(domain:Domain)-[:RESOLVES_TO]->(ip:IPAddress)
(cert:Certificate)-[:SIGNED_APKS {count: 5}]->(apk:APK)
```

### 5.3 Example Threat-Hunting Queries

**Q1: All APKs targeting SBI in last 30 days sharing C2 infrastructure**
```cypher
MATCH (a:APK)-[:IMPERSONATES]->(:BankApp {name: "SBI YONO"})
MATCH (a)-[:COMMUNICATES_WITH]->(ip:IPAddress)<-[:COMMUNICATES_WITH]-(b:APK)
WHERE a.first_seen > datetime() - duration('P30D')
  AND a <> b
RETURN a, b, ip
ORDER BY a.risk_score DESC
```

**Q2: Evolutionary lineage of current APK**
```cypher
MATCH path = (root:APK)-[:EVOLVED_FROM*]->(current:APK {sha256: $hash})
RETURN path
```

**Q3: Top 10 threat actors by sample count in last quarter**
```cypher
MATCH (a:APK)-[:ATTRIBUTED_TO]->(actor:ThreatActor)
WHERE a.first_seen > datetime() - duration('P90D')
RETURN actor.name, count(a) AS sample_count
ORDER BY sample_count DESC
LIMIT 10
```

**Q4: Find campaign pivots (infrastructure reuse)**
```cypher
MATCH (c1:Campaign)-[:USES_INFRASTRUCTURE]->(i:IPAddress)<-[:USES_INFRASTRUCTURE]-(c2:Campaign)
WHERE c1 <> c2
RETURN c1, c2, i
```

**Q5: Which of our bank's brand is most impersonated?**
```cypher
MATCH (a:APK)-[r:IMPERSONATES]->(b:BankApp)
RETURN b.name, count(a) AS impersonation_count
ORDER BY impersonation_count DESC
```

### 5.4 Vector Index (Qdrant)

**Stored embeddings:**
- APK-level: aggregated intent vector (mean of code blob vectors)
- Code-blob-level: per-function semantic intent embedding
- Screenshot-level: multimodal embedding for visual similarity

**Search use cases:**
- "Find APKs semantically similar to this one" (catches zero-day variants)
- "Find code blobs that look like this SMS interceptor"
- "Find UIs that look like SBI YONO"

### 5.5 MISP Integration

PARALLAX auto-pushes IOCs to a MISP instance:
- Hashes
- IPs
- Domains
- YARA rule bundles
- Campaign metadata

**STIX 2.1 format** for portability. This enables **cross-bank threat sharing** (industry-level defense).

### 5.6 Graph Population Pipeline

```
New APK analyzed
    │
    ├─► Create (:APK) node
    │
    ├─► MERGE all (:Permission), (:API), (:IPAddress), (:Domain) nodes
    │
    ├─► Create relationships (REQUESTS, CALLS, etc.)
    │
    ├─► Run BinDiff against all historical APKs
    │     └─ Create SHARES_CODE_WITH edges where similarity > 0.5
    │
    ├─► Run attribution inference
    │     └─ Query: similar C2 + similar code + similar TTPs
    │     └─ Create ATTRIBUTED_TO edges with confidence scores
    │
    ├─► Campaign detection (community detection algorithm)
    │     └─ Graph algorithms: Louvain, Label Propagation
    │     └─ Create (:Campaign) nodes + PART_OF edges
    │
    └─► Generate Neo4j summary email to analyst
```

---

## 6. Layer 5  --  Delivery & Action Layer

### 6.1 Output Channels

| Channel | Format | Audience |
|---|---|---|
| Real-time dashboard | Grafana web UI | SOC analysts, CISO |
| Auto-generated PDF report | Jinja2 template | Executive, analyst |
| STIX 2.1 bundle | JSON | SIEM, MISP, peer banks |
| YARA rule | .yar file | Bank's AV infrastructure |
| Suricata/Snort rules | .rules file | Bank's IDS/IPS |
| Fraud rule DSL | Bank-specific format | Bank's fraud engine |
| Webhook alerts | JSON over HTTPS | SIEM, fraud system, WhatsApp |
| RBI compliance report | Pre-formatted | Compliance team |

### 6.2 Risk Score Computation

```python
def compute_risk_score(agent_outputs) -> RiskScore:
    """
    Explainable, additive risk score (0-100).
    Each component contributes with documented weight.
    """
    components = {
        "permission_abuse":     compute_permission_risk(agent_outputs["static"]["permissions"]),
        "behavioral_indicators": compute_behavior_risk(agent_outputs["dynamic"]["events"]),
        "code_intent_risk":     compute_intent_risk(agent_outputs["code_interpreter"]["intents"]),
        "network_exfiltration": compute_network_risk(agent_outputs["dynamic"]["network"]),
        "code_obfuscation":     compute_obfuscation_risk(agent_outputs["static"]["obfuscation"]),
        "brand_impersonation":  compute_visual_risk(agent_outputs["visual"]["brand_impersonation"]),
        "campaign_association": compute_campaign_risk(agent_outputs["intel"]["campaign_links"]),
        "attribution_confidence": compute_attribution_risk(agent_outputs["intel"]["attribution"])
    }
    
    weights = {
        "permission_abuse": 0.12,
        "behavioral_indicators": 0.20,
        "code_intent_risk": 0.18,
        "network_exfiltration": 0.15,
        "code_obfuscation": 0.05,
        "brand_impersonation": 0.15,
        "campaign_association": 0.10,
        "attribution_confidence": 0.05
    }
    
    total = sum(components[k] * weights[k] * 100 for k in components)
    return RiskScore(score=total, components=components, weights=weights)
```

### 6.3 Report Generation (Jinja2)

The Synthesis Agent produces structured output that Jinja2 templates convert into:
- **Executive report**  --  1 page, plain English, business impact
- **Technical report**  --  full evidence chain, ATT&CK heatmap, screenshots
- **Forensic report**  --  IOC dump, signature data, replay instructions

### 6.4 Self-Evolution Outputs

Every analyzed APK automatically produces:
- New YARA rules (if new patterns observed)
- New semantic embeddings (added to Qdrant)
- New graph relationships (added to Neo4j)
- New ATT&CK mappings (refined over time)

**The system literally gets better at its job with every APK processed.**

---

## 7. Data Flow Diagram (End-to-End)

```
[WhatsApp Honeypot] ─┐
[Analyst Upload] ────┤
[Email Gateway] ─────┼─► [Ingestion API] ─► [MinIO Storage] ─► [Triage LLM]
[MISP Feed] ─────────┤                              │
[Browser Ext.] ──────┘                              ▼
                                              [Priority Queue]
                                                      │
                                                      ▼
                              ┌───────────────────────┼───────────────────────┐
                              │                       │                       │
                              ▼                       ▼                       ▼
                    [Static Analysis]         [Dynamic Analysis]         [Visual AI]
                    androguard, jadx,         AVD + Frida +              LLaVA on
                    FlowDroid, YARA,         mitmproxy +                 screenshots
                    BinDiff, Unicorn         DroidBot-GPT
                              │                       │                       │
                              └───────────────────────┼───────────────────────┘
                                                      ▼
                                          [AI Reasoning Cortex]
                                          ┌──────────┬──────────┬──────────┐
                                          │ Code     │ Behavior │ Intel    │
                                          │ Interp.  │ Analyst  │ Correl.  │
                                          └────┬─────┴────┬─────┴────┬─────┘
                                               └──────────┼──────────┘
                                                          ▼
                                                  [Debate Layer]
                                                          │
                                                          ▼
                                                  [Synthesis Agent]
                                                  -> Risk Score
                                                  -> Report
                                                  -> ATT&CK Map
                                                  -> YARA Rules
                                                          │
                              ┌───────────────────────────┼───────────────────────────┐
                              ▼                           ▼                           ▼
                    [TAIG Graph Update]            [Delivery Layer]         [Self-Evolution]
                    Neo4j + Qdrant write           PDF, STIX, YARA,        YARA rules
                    New nodes + edges              Webhooks                generated
                    Campaign detection                                     Graph enriched
```

---

## 8. Infrastructure Architecture

### 8.1 Local Development
- Single workstation (32GB RAM minimum)
- Docker Compose orchestrates all services
- Ollama for local LLMs

### 8.2 Production (On-Premise for Banks)

```
┌──────────────────────────────────────────────────────────────┐
│                     BANK DATA CENTER                         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  K8s Node 1 │  │  K8s Node 2 │  │  K8s Node 3 │         │
│  │  Ingestion  │  │  Static     │  │  Dynamic    │         │
│  │  API        │  │  Analysis   │  │  Analysis   │         │
│  │  Triagers   │  │  Workers    │  │  + AVD      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  K8s Node 4 │  │  K8s Node 5 │  │  K8s Node 6 │         │
│  │  AI Cortex  │  │  Neo4j      │  │  Qdrant +   │         │
│  │  + Ollama   │  │  Cluster    │  │  MISP       │         │
│  │  LLMs       │  │  (3-node)   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  ┌──────────────────────────────────────────────────┐       │
│  │  Shared: MinIO + PostgreSQL + Redis + Grafana   │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  Hardware: GPU server (NVIDIA A100 or 2x A10) for LLMs     │
│            256GB RAM nodes, NVMe SSD storage                │
└──────────────────────────────────────────────────────────────┘
```

### 8.3 Observability

- **OpenTelemetry** instrumentation throughout
- **Jaeger** for distributed tracing
- **Grafana** for metrics + dashboards
- **Loki** for log aggregation
- Every AI decision is **logged with full reasoning trace** for audit

---

## 9. Security Considerations for PARALLAX Itself

PARALLAX analyzes malware  --  it must be hardened against being compromised by what it analyzes.

1. **Network isolation**  --  analysis workers have no internet access except to controlled test endpoints
2. **Egress filtering**  --  captured malware traffic only goes to whitelisted analysis servers
3. **No persistent storage**  --  APK originals auto-purged after 90 days unless flagged
4. **Sandbox containment**  --  Android emulators on isolated VLANs
5. **Credential vault**  --  all secrets via HashiCorp Vault, never in code
6. **Supply chain**  --  all open-source deps pinned, SBOM generated per build
7. **Audit logging**  --  every action logged immutably
8. **Read-only file systems**  --  workers cannot modify their own containers
9. **Resource limits**  --  CPU/RAM/disk caps prevent runaway analysis
10. **Red team testing**  --  periodic adversarial testing of PARALLAX itself

---

## 10. API Design (REST)

### 10.1 Ingestion

```
POST /api/v1/analyze
Content-Type: multipart/form-data
Body: { apk_file: <binary> }
Response: { submission_id, triage_score, priority, eta_seconds }
```

### 10.2 Status

```
GET /api/v1/analysis/{submission_id}
Response: { status, progress_pct, current_stage, eta_seconds }
```

### 10.3 Results

```
GET /api/v1/analysis/{submission_id}/report
-> PDF report

GET /api/v1/analysis/{submission_id}/stix
-> STIX 2.1 bundle (JSON)

GET /api/v1/analysis/{submission_id}/yara
-> YARA rule file

GET /api/v1/analysis/{submission_id}/iocs
-> IOC list (CSV/JSON)
```

### 10.4 Graph Queries

```
POST /api/v1/graph/cypher
Body: { query, params }
Response: { results, took_ms }

POST /api/v1/graph/similar
Body: { apk_sha256, k: 10 }
Response: [ { sha256, similarity, package, risk_score } ]
```

### 10.5 TAIG Threat Hunting

```
POST /api/v1/hunt
Body: { filter: { ... }, time_range: "P30D" }
Response: { matches: [APK, ...], campaign_summary, attribution }
```

---

## 11. Database Schemas (PostgreSQL)

### 11.1 analyses table
```sql
CREATE TABLE analyses (
  submission_id UUID PRIMARY KEY,
  apk_sha256 CHAR(64) UNIQUE NOT NULL,
  submitted_at TIMESTAMPTZ NOT NULL,
  submitted_by VARCHAR(100),
  source VARCHAR(50),
  status VARCHAR(20),  -- queued, analyzing, completed, failed
  current_stage VARCHAR(50),
  risk_score SMALLINT,
  verdict VARCHAR(20),
  confidence REAL,
  report_url TEXT,
  completed_at TIMESTAMPTZ
);
```

### 11.2 iocs table
```sql
CREATE TABLE iocs (
  id BIGSERIAL PRIMARY KEY,
  analysis_id UUID REFERENCES analyses(submission_id),
  ioc_type VARCHAR(20),  -- ip, domain, hash, cert
  ioc_value TEXT NOT NULL,
  confidence REAL,
  first_seen TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_iocs_type_value ON iocs(ioc_type, ioc_value);
```

### 11.3 audit_log table
```sql
CREATE TABLE audit_log (
  id BIGSERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  user_id VARCHAR(100),
  action VARCHAR(100),
  resource VARCHAR(200),
  details JSONB
);
```

---

## 12. Self-Evolution Feedback Loop  --  Detailed

```
Analysis complete
    │
    ├─► New YARA rule generated (DSPy + signature extraction)
    │     └─► Saved to YARA rule library
    │     └─► Tested against historical samples
    │     └─► Auto-deployed to TAIG knowledge corpus
    │
    ├─► New semantic embedding added to Qdrant
    │     └─► Indexed for future similarity search
    │
    ├─► New graph nodes/relationships added to Neo4j
    │     └─► Campaign detection re-runs
    │     └─► Attribution confidence updated
    │
    ├─► New ATT&CK mapping stored
    │     └─► Refines future mapping accuracy
    │
    └─► DSPy prompt optimizer retrains on new successful analyses
          └─► Improved agent prompts
          └─► Measurable accuracy gains over time
```

**This is the flagship characteristic: the system genuinely improves itself.**

---

## 13. End-to-End Latency Budget

| Stage | Target Time |
|---|---|
| Ingestion + triage | < 5 seconds |
| Static analysis | 2-4 minutes |
| Dynamic analysis | 5-8 minutes |
| Visual AI | 1-2 minutes (parallel) |
| AI Reasoning Cortex | 30-90 seconds |
| TAIG update | 10-30 seconds |
| Report generation | 10 seconds |
| **Total** | **~10-12 minutes per APK** |

Acceptable for high-priority samples. For batch processing, throughput scales horizontally.

---

## 14. What's NOT in Scope (v1)

- iOS IPA analysis (separate track for v2)
- Real-time network IDS deployment (PARALLAX is analyzer, not detector at network edge)
- Customer-facing UI (v1 is SOC/analyst-facing)
- Mobile app (web only for v1)
- Multi-tenant SaaS (v1 is single-bank on-prem)

---

## 15. References for Architecture Design

- **TAIG pattern**  --  inspired by Palantir Foundry's object-oriented graph + Neo4j best practices
- **Multi-agent debate**  --  inspired by "Self-Consistency Improves Chain of Thought Reasoning" (Wang et al., 2022) and "Improving Factuality and Reasoning through Multiagent Debate" (Du et al., 2023)
- **LangGraph orchestration**  --  patterns from LangChain documentation
- **Self-evolution pattern**  --  inspired by AutoML and continuous learning systems
- **RAG over threat intel**  --  LlamaIndex RAG patterns
- **Binary similarity**  --  BinDiff research papers

---

*Next: See `03_TECH_STACK.md` for the complete tool inventory with versions and install commands, and `04_IMPLEMENTATION_PHASES.md` for the build plan.*
