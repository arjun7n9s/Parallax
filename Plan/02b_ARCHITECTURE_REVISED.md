# PARALLAX  --  Revised System Architecture
## Version 2.0: Hypothesis-Driven, AI-Native, Bank-Focused

> **This document supersedes the original architecture.** It implements the vision defined in `PARALLAX_VISION.md`  --  particularly the hypothesis-driven loop, the AI Reverse Engineering Workbench, the AI-guided dynamic exploration, the Malware Pattern Memory, the two-layer risk scoring, and the clean Investigation Reasoning Trace (IRT).

---

## 1. Architecture Philosophy

### 1.1 The Wrong Architecture (v1, rejected)

```
APK -> [Ingestion] -> [Static Tools] -> [Dynamic Sandbox] -> [LLM Summary] -> Report
```

Tools run unconditionally. LLM summarizes after the fact. **AI is passive narrator.**

### 1.2 The Right Architecture (v2, this document)

```
APK -> [Hypothesis Engine]
         v (initial hypotheses)
      [Tool Selector] <- AI Reverse Engineering Workbench
         v (chosen tools)
      [Static Analysis Engine]
         v (artifact model)
      [Hook Planning Agent]
         v (adaptive hook plan)
      [Dynamic Analysis Engine]
         v (raw events)
      [Dynamic Exploration Agent] <- AI-operated investigation
         v (verified behaviors)
      [Visual Intelligence Engine]
         v (brand impersonation evidence)
      [Hypothesis Engine] <- scratchpad update
         v (loop continues until convergence)
      [Pattern Memory Query] <- what does the system remember?
         v (similar samples, family links)
      [AI Reasoning Cortex] <- 5 agents + Debate Layer
         v (verdicts)
      [Risk Calibration Engine] <- two-layer scoring
         v (calibrated score)
      [Fraud Attack Chain Builder] <- bank-specific output
         v (chain reconstruction)
      [Evidence Validator + IRT Distillation]
         v (clean external report)
      [Report Generator] -> PDF, STIX, YARA, fraud rules
```

**The AI is the investigator. Tools are instruments. Graph is memory. IRT is the report.**

---

## 2. Top-Level Architecture: The Recursive Loop

```
                       ┌──────────────────────────────────┐
                       │     HYPOTHESIS ENGINE            │
                       │  (live scratchpad, internal)     │
                       └────┬─────────────────────────────┘
                            │ hypotheses + experiments
              ┌─────────────┼──────────────┐
              v             v              v
      ┌──────────────┐ ┌──────────┐ ┌──────────────┐
      │  REVERSE     │ │ DYNAMIC  │ │  PATTERN     │
      │  ENGINEERING │ │ EXPLOR-  │ │  MEMORY      │
      │  WORKBENCH   │ │ ATION    │ │  (queries)   │
      │              │ │ AGENT    │ │              │
      └──────┬───────┘ └────┬─────┘ └──────┬───────┘
             │              │              │
             └──────────────┼──────────────┘
                            v
                  ┌──────────────────────┐
                  │  AI REASONING        │
                  │  CORTEX              │
                  │  (5 agents + debate) │
                  └──────────┬───────────┘
                             v
                  ┌──────────────────────┐
                  │  RISK CALIBRATION    │
                  │  ENGINE              │
                  └──────────┬───────────┘
                             v
                  ┌──────────────────────┐
                  │  FRAUD ATTACK CHAIN  │
                  │  BUILDER             │
                  └──────────┬───────────┘
                             v
                  ┌──────────────────────┐
                  │  EVIDENCE VALIDATOR  │
                  │  + IRT DISTILLATION  │
                  └──────────┬───────────┘
                             v
                        [REPORT]
```

The loop is **recursive**  --  Hypothesis Engine can request another cycle of investigation at any point. The loop terminates when:
- All high-priority hypotheses are confirmed or rejected
- Time budget exhausted
- Analyst manually terminates

---

## 3. The Twelve Core Modules  --  Detailed Specifications

### Module 1: Ingestion & Triage Layer

**Purpose:** Accept APKs from any source, pre-screen, prioritize.

**Inputs:**
- APK file (multipart upload, MISP feed, honeypot capture, email gateway, browser extension)
- Source metadata

**Process:**
1. **Triage LLM** (Phi-3 Mini, <2s) reads manifest + permissions only -> pre-score
2. **ssdeep fuzzy hash** -> fast similarity check against known samples
3. **APKiD** -> packer/protector fingerprint
4. **Certificate check** -> self-signed, validity, known abuse
5. **Priority routing** -> CRITICAL jumps queue, LOW batches

**Output:**
```json
{
  "submission_id": "uuid",
  "apk_sha256": "...",
  "triage_score": 78,
  "priority": "HIGH",
  "flag_reasons": ["accessibility_service", "sms_intercept_capable"],
  "ssdeep_match": {"sha256": "...", "similarity": 0.92, "verdict": "CRITICAL"}
}
```

**Storage:** Original APK in MinIO (`parallax-apks/{sha256}.apk`)

---

### Module 2: AI Reverse Engineering Workbench ⭐ (NEW, CENTRAL)

**Purpose:** This is the core AI-native reverse engineering layer. Produces a **structured semantic artifact model** of the decompiled APK, not raw decompiled code.

**Position:** Between static tools and dynamic analysis. Consumes decompiled Java + static tool outputs. Produces a structured artifact that drives the hook plan and dynamic exploration.

**Process:**

```
Decompiled Java + Smali
        v
[Code Preprocessor] -> chunks of 200-500 lines, framework code filtered
        v
[Class Role Mapper] (LLM per chunk)
        v
[Method Intent Classifier] (LLM per method)
        v
[Call Graph Summarizer] (LLM over call graph)
        v
[Data-Flow Reasoner] (LLM over FlowDroid taint flows)
        v
[Attack Flow Synthesizer] (LLM over all artifacts)
        v
STRUCTURED ARTIFACT MODEL
```

**Output (the artifact model  --  what makes this AI-native):**

```json
{
  "class_roles": [
    {
      "class": "com.fake.sbi.SmsReceiver",
      "role": "OTP interception broadcast receiver",
      "confidence": 0.96,
      "evidence": [
        "extends android.content.BroadcastReceiver",
        "calls android.telephony.SmsMessage.createFromPdu",
        "posts message body to URL via HttpURLConnection",
        "registered for SMS_RECEIVED action in manifest"
      ],
      "attck_techniques": ["T1412"]
    },
    {
      "class": "com.fake.sbi.AccessibilityStealer",
      "role": "Credential overlay via accessibility service abuse",
      "confidence": 0.98,
      "evidence": [
        "extends android.accessibilityservice.AccessibilityService",
        "overrides onAccessibilityEvent",
        "draws fullscreen TYPE_APPLICATION_OVERLAY window",
        "monitors package name transitions in event.getPackageName()"
      ],
      "attck_techniques": ["T1516", "T1655"]
    },
    {
      "class": "com.fake.sbi.MainActivity",
      "role": "Legitimate-looking entry point with no malicious behavior",
      "confidence": 0.85,
      "evidence": ["only loads layout, no network or SMS operations"]
    }
  ],
  "method_intents": [
    {
      "method": "com.fake.sbi.NetworkHelper.sendDataToServer",
      "intent": "credential exfiltration",
      "sources": [
        "EditText.getText() from login form",
        "SmsMessage.getMessageBody() from SMS receiver"
      ],
      "sinks": [
        "HttpURLConnection POST to http://185.220.101.47:8080/exfil",
        "Base64 encoding applied before transport"
      ],
      "data_classes": ["banking_credentials", "sms_otp"],
      "confidence": 0.95
    }
  ],
  "call_graph_summary": {
    "entry_points": ["MainActivity", "SmsReceiver", "AccessibilityStealer"],
    "critical_paths": [
      "MainActivity -> AccessibilityStealer.onServiceConnected -> onAccessibilityEvent",
      "SmsReceiver.onReceive -> NetworkHelper.sendDataToServer",
      "AccessibilityStealer.onAccessibilityEvent -> OverlayManager.drawOverlay"
    ],
    "dead_code_candidates": ["com.fake.sbi.SettingsActivity (never invoked)"]
  },
  "data_flow_map": {
    "credential_flow": {
      "source": "EditText password field (R.id.password)",
      "intermediaries": ["AccessibilityStealer.onAccessibilityEvent"],
      "sink": "NetworkHelper.sendDataToServer -> 185.220.101.47:8080",
      "taint_confidence": 0.94
    },
    "otp_flow": {
      "source": "SmsReceiver.onReceive (SMS_RECEIVED intent)",
      "intermediaries": ["SmsMessage.createFromPdu"],
      "sink": "NetworkHelper.sendDataToServer",
      "taint_confidence": 0.97
    }
  },
  "string_analysis": {
    "hardcoded_urls": ["http://185.220.101.47:8080/exfil", "http://c2-backup.evil.com/panel"],
    "encrypted_strings": 0,
    "suspicious_constants": [
      {"offset": "0x4A20", "value": "...", "interpretation": "AES key, plaintext"}
    ]
  },
  "native_findings": {
    "libraries": ["libhelper.so"],
    "packed": false,
    "suspicious_exports": [
      {
        "name": "decrypt_payload",
        "module": "libhelper.so",
        "purpose": "decrypts hardcoded ciphertext to URL string at runtime",
        "evidence": "r2pipe analysis + Unicorn emulation"
      }
    ]
  },
  "dynamic_loading": {
    "uses_dex_class_loader": false,
    "uses_path_class_loader": false,
    "loads_native_libs_at_runtime": true,
    "loads_native_libs": ["libhelper.so"]
  },
  "stage_2_loader": {
    "detected": true,
    "trigger": "first launch",
    "loader_url": "http://185.220.101.47:8080/stage2.apk",
    "evidence": "decrypt_payload returns this URL via Unicorn emulation"
  },
  "credential_paths": [
    {
      "path": "EditText -> AccessibilityStealer -> NetworkHelper",
      "captures": ["username", "password"],
      "exfiltrates_to": "185.220.101.47:8080"
    }
  ],
  "attack_flow": [
    "App requests BIND_ACCESSIBILITY_SERVICE",
    "User grants permission",
    "App registers AccessibilityStealer as persistent service",
    "User opens legitimate banking app (SBI YONO)",
    "App draws fullscreen overlay matching SBI YONO login",
    "User types credentials into fake overlay",
    "Credentials captured and POSTed to C2 within 200ms",
    "App dismisses overlay, user sees real banking app",
    "Next incoming SMS (containing OTP) is intercepted by SmsReceiver",
    "OTP body POSTed to C2 within 200ms",
    "Attacker now has both credentials and OTP -> can complete fraudulent transaction"
  ]
}
```

**This artifact is the heart of PARALLAX.** It is what the Hook Planning Agent reads, what the Dynamic Exploration Agent acts on, what the Synthesis Agent reasons over.

**Models used:** DeepSeek-Coder-V2 (16B, local via Ollama) for code analysis. Few-shot examples from known banking trojan code.

---

### Module 3: Static Analysis Engine

**Purpose:** Run the actual static analysis tools. Output is **consumed by the AI Reverse Engineering Workbench**, not directly interpreted by the LLM.

**Tools:**
- `androguard`  --  permission/API/manifest extraction
- `jadx`  --  DEX -> Java decompilation
- `apktool`  --  resource decoding
- `FlowDroid`  --  taint analysis
- `Semgrep`  --  custom banking malware rules
- `YARA`  --  pattern matching
- `BinDiff` / `Diaphora`  --  binary similarity
- `Unicorn Engine`  --  micro-emulation of obfuscated routines
- `r2pipe` (Radare2)  --  native library analysis
- `simplify`  --  deobfuscation
- `NetworkX`  --  permission graph construction

**Output (unified JSON):**
```json
{
  "static_analysis": {
    "permissions": [...],
    "api_calls": [...],
    "hardcoded_strings": [...],
    "certificate": {...},
    "obfuscation": {...},
    "binary_similarity": [...],
    "taint_flows": [...],
    "semgrep_matches": [...],
    "yara_matches": [...],
    "permission_graph": {...}
  }
}
```

The Workbench (Module 2) **translates this into the structured artifact model**.

---

### Module 4: Hook Planning Agent ⭐ (NEW)

**Purpose:** Generate a **targeted, adaptive Frida hook plan** based on static findings. Update mid-run when new behaviors are observed.

**Input:** The structured artifact model from Module 2.

**Process:**

```python
# Hook Planner reads class_roles and method_intents
# and selects which hook scripts to enable

def plan_hooks(artifact_model: dict) -> HookPlan:
    hooks = []
    
    # Accessibility service detected?
    if any(c["role"].contains("accessibility") for c in artifact_model["class_roles"]):
        hooks.append({
            "script": "accessibility_abuse.js",
            "targets": ["AccessibilityService", "AccessibilityEvent"],
            "capture": ["package_transitions", "overlay_windows", "event_text"]
        })
    
    # SMS interception detected?
    if any(c["role"].contains("OTP") or c["role"].contains("SMS") for c in artifact_model["class_roles"]):
        hooks.append({
            "script": "sms_interception.js",
            "targets": ["SmsMessage", "SmsManager"],
            "capture": ["body", "sender", "timestamp"]
        })
    
    # Network exfiltration detected?
    if any(m["intent"] == "credential exfiltration" for m in artifact_model["method_intents"]):
        hooks.append({
            "script": "network_logger.js",
            "targets": ["HttpURLConnection", "URL", "OkHttpClient"],
            "capture": ["url", "method", "body", "headers"]
        })
    
    # Crypto operations detected?
    if any("encrypt" in str(m).lower() for m in artifact_model["method_intents"]):
        hooks.append({
            "script": "crypto_extraction.js",
            "targets": ["Cipher", "SecretKeySpec", "KeyGenerator", "MessageDigest"],
            "capture": ["algorithm", "key", "iv", "plaintext"]
        })
    
    # WebView detected?
    if any("webview" in str(c).lower() for c in artifact_model["class_roles"]):
        hooks.append({
            "script": "webview_inspector.js",
            "targets": ["WebView", "WebViewClient", "WebChromeClient"],
            "capture": ["loadUrl", "form_data", "javascript_bridges"]
        })
    
    # Dynamic class loading detected?
    if artifact_model["dynamic_loading"]["uses_dex_class_loader"]:
        hooks.append({
            "script": "dynamic_class_loader.js",
            "targets": ["DexClassLoader", "PathClassLoader"],
            "capture": ["loaded_class_names", "source_paths"]
        })
    
    return HookPlan(hooks=hooks)
```

**Mid-run adaptation:**

```python
# When dynamic agent observes a new behavior, it requests hook update
class HookPlanningAgent:
    def update_plan(self, observation: Observation, current_plan: HookPlan) -> HookPlan:
        if observation.type == "DEX_CLASS_LOADER_INVOCATION":
            current_plan.add("dynamic_class_loader.js")  # wasn't pre-planned
        if observation.type == "CRYPTO_API_FIRED":
            current_plan.add("crypto_extraction.js")
        if observation.type == "C2_BEACON_DETECTED":
            current_plan.add("binary_protocol_decoder.js")
        return current_plan
```

**Output:** `HookPlan` object with active scripts, hook targets, capture instructions, dynamically updated as investigation progresses.

---

### Module 5: Dynamic Analysis Engine

**Purpose:** Provide the runtime substrate  --  instrumented Android environment, traffic capture, system call monitoring.

**Components:**
- **Android AVD**  --  headless x86_64 emulator on isolated VLAN
- **Frida runtime**  --  receives HookPlan from Module 4
- **mitmproxy**  --  full HTTPS traffic capture
- **Scapy**  --  custom protocol dissectors
- **Strace / ltrace**  --  system call tracing
- **DroidBot-GPT**  --  UI exploration driver (called by Module 6, not autonomous)
- **Mock Banking Apps**  --  installed dynamically by Module 6 to trigger context-aware behavior

**Output:** Stream of timestamped events to the Dynamic Exploration Agent.

---

### Module 6: Dynamic Exploration Agent ⭐ (CENTRAL)

**Purpose:** Operate the Android environment like a **trained fraud investigator**, not a passive sandbox. AI-guided, hypothesis-driven, targeted.

**Position:** The agent reads the artifact model (Module 2), the hook plan (Module 4), and the live hypothesis scratchpad. It **decides** what to do next and **operates** the environment.

**Capabilities:**

1. **What screen to explore next**  --  reads current UI state, decides next tap
2. **What fake credentials to input**  --  generates realistic-looking inputs
3. **What permission paths to trigger**  --  handles permission grant flows malware expects
4. **What environmental mutations to try**  --  locale, SIM, time, installed apps
5. **What Frida hooks to enable next**  --  requests hook updates from Module 4
6. **Whether the sample is dormant, evasive, or staged**  --  interprets runtime signals

**Example investigation session:**

```
T+0s:    Install APK
T+5s:    Launch app in clean emulator
T+8s:    [OBSERVED] Permission request: BIND_ACCESSIBILITY_SERVICE
         [HYPOTHESIS UPDATE] H1 elevated to HIGH priority
T+10s:   [ACTION] Grant accessibility permission
T+15s:   [OBSERVED] App shows generic "loading" screen
         [HYPOTHESIS UPDATE] App may be waiting for trigger event
T+17s:   [ACTION] Install mock SBI YONO package
T+20s:   [ACTION] Bring mock SBI to foreground
T+22s:   [OBSERVED] PARALLAX app draws fullscreen overlay on top
         [HYPOTHESIS UPDATE] H1 CONFIRMED (overlay attack)
T+25s:   [ACTION] Input fake username "user@bank.com" and password "Test123!"
T+27s:   [OBSERVED] Network hook fires: POST to 185.220.x.x with base64 creds
         [HYPOTHESIS UPDATE] H2 (exfiltration) CONFIRMED
T+30s:   [ACTION] Switch app to background, simulate incoming SMS with OTP "847291"
T+33s:   [OBSERVED] SmsReceiver fires, body captured, POSTed to C2 within 200ms
         [HYPOTHESIS UPDATE] H3 (OTP theft) CONFIRMED
T+35s:   [ACTION] Initiate mutation: change locale to ur-PK
T+38s:   [OBSERVED] New C2 endpoint activated: c2-backup.evil.com
         [HYPOTHESIS UPDATE] H4 (context-aware) CONFIRMED
T+40s:   [ACTION] Initiate mutation: remove mock banking app
T+45s:   [OBSERVED] App goes dormant, no network activity
         [HYPOTHESIS UPDATE] H5 (banking-app-triggered) CONFIRMED
T+50s:   [ACTION] Stop exploration, capture final state
T+52s:   [REPORT TO HYPOTHESIS ENGINE] Investigation complete
```

**Implementation:** LangGraph agent with stateful graph, tool-use capabilities for AVD control, UI driver, Frida hook management, mutation parameters.

**Models used:** Mistral-Large or Llama-3.1-70B (local) for reasoning. Fast iteration on action decisions.

---

### Module 7: Visual Intelligence Engine (Multi-Modal Brand Impersonation) ⭐ (UPGRADED)

**Purpose:** Detect brand impersonation, phishing UI, overlay attacks via a **hybrid of multiple signals**, not just LLM vision.

**Position:** Runs parallel to dynamic analysis. Consumes screenshot stream from Module 5.

**Components (hybrid, not LLM-only):**

```
Screenshot
    v
[CLIP Embedding] -> similarity to known bank app reference screenshots
    v
[OCR (Tesseract)] -> extract visible text -> compare to known bank branding strings
    v
[Logo Detection (YOLO)] -> detect bank logos -> match against reference corpus
    v
[Package Name Similarity] -> compare declared package to known bank packages
    v
[Color/Layout Diff] -> OpenCV compare against reference UI
    v
[LLaVA-OneVision] -> final semantic interpretation
    v
[Score Aggregator] -> weighted combination of all signals
```

**Why hybrid:** Any single signal is weak. CLIP alone can miss text-swap attacks. LLM alone can hallucinate. Combining 5 signals gives high confidence.

**Output:**
```json
{
  "brand_impersonation": {
    "is_impersonation": true,
    "target_app": "com.sbi.lotus",
    "target_name": "SBI YONO",
    "overall_similarity_score": 0.97,
    "signal_breakdown": {
      "clip_visual_similarity": 0.96,
      "ocr_text_match": 0.95,
      "logo_detection": 0.99,
      "package_name_similarity": 0.94,
      "color_layout_match": 0.98
    },
    "llava_description": "Pixel-perfect clone of SBI YONO login screen. Slight gradient shift and field positioning offset by 4px.",
    "evidence_screenshot": "s3://parallax-screens/{sha256}/screen_5.png"
  },
  "overlay_attacks": [
    {
      "type": "accessibility_overlay",
      "trigger_condition": "when com.sbi.lotus is in foreground",
      "evidence": "Overlay appears with identical UI but different package"
    }
  ]
}
```

---

### Module 8: AI Reasoning Cortex

**Purpose:** Combine all signals (static artifact, dynamic observations, visual analysis, intel correlation) into a final verdict with debate handling.

**Agents (5 specialized, as before):**

| Agent | Model | Input | Output |
|---|---|---|---|
| Code Interpreter | DeepSeek-Coder-V2 | Artifact model from Module 2 | Per-class risk, intent confirmation |
| Behavior Analyst | Mistral-Large | Runtime event stream from Module 6 | Kill chain narrative, behavior risk |
| Intel Correlator | RAG over MITRE + MISP | IOCs from all sources | ATT&CK mapping, attribution |
| Visual Intelligence | LLaVA-OneVision | Screenshots from Module 7 | Phishing UI confirmation |
| Synthesis | GPT-4o / Claude Opus | All 4 agent outputs + debate | Final verdict + risk + report |

**Debate Layer (unchanged from v1, well-designed):**
- Treats contradictions as high-confidence signals (evasion signature)
- Doesn't average away disagreements
- Specific patterns: POLYMORPHIC_EVASION_SUSPECTED, DORMANT_CAPABILITY, PHISHING_UI_DETECTED

---

### Module 9: Malware Pattern Memory ⭐ (NEW, NAMED SUBSYSTEM)

**Purpose:** A **named, queryable, self-enriching subsystem** storing 8 categories of patterns. Not scattered features  --  one module with clear ownership.

**Pattern Categories:**

```python
PATTERN_CATEGORIES = {
    "fraud_flows": {
        "description": "Known attack chain sequences",
        "examples": [
            "accessibility_overlay -> credential_capture -> otp_intercept -> transaction",
            "fake_kyc -> contact_exfil -> smishing_campaign"
        ],
        "storage": "Neo4j + sequence embeddings"
    },
    "permission_api_chains": {
        "description": "Suspicious permission + API combinations",
        "examples": [
            "BIND_ACCESSIBILITY_SERVICE + SYSTEM_ALERT_WINDOW + HttpURLConnection",
            "RECEIVE_SMS + READ_SMS + INTERNET + dynamic class loading"
        ],
        "storage": "Neo4j graph + rule signatures"
    },
    "code_idioms": {
        "description": "Recognizable code patterns from known malware families",
        "examples": [
            "SmsReceiver extends BroadcastReceiver + posts to URL",
            "AccessibilityService subclass + onAccessibilityEvent + addView"
        ],
        "storage": "Qdrant embeddings + AST fingerprints"
    },
    "ui_phishing_templates": {
        "description": "Visual UI templates from known phishing kits",
        "examples": [
            "SBI YONO login template (97% visual match)",
            "HDFC mobile banking OTP template"
        ],
        "storage": "Qdrant + reference image hash DB"
    },
    "c2_communication_patterns": {
        "description": "Network behavior fingerprints",
        "examples": [
            "60-second beacon interval + POST + base64 body",
            "Domain generation algorithm: {weekday}-{random}.{tld}"
        ],
        "storage": "Network pattern DB + YARA-NET rules"
    },
    "certificate_reuse": {
        "description": "Certificate fingerprints seen across multiple APKs",
        "examples": [
            "Cert A1:B2:C3...:ED used in 14 prior samples, 89% malicious"
        ],
        "storage": "Neo4j CERTIFICATE nodes with observation_count"
    },
    "packer_obfuscator_fingerprints": {
        "description": "APKiD signatures from packers/protectors",
        "examples": [
            "DexGuard v8.5.0 + string encryption + class renaming"
        ],
        "storage": "APKiD signature DB + YARA rules"
    },
    "behavioral_timing_fingerprints": {
        "description": "Temporal patterns in runtime behavior",
        "examples": [
            "Dormant for exactly 72 hours before activation",
            "C2 beacon at exactly 60s intervals (GoldPickaxe signature)",
            "Permission request always after 3 user interactions, not on launch"
        ],
        "storage": "Timed event log + signature templates"
    }
}
```

**Operations:**
- **Query**: Given a sample, find matching patterns across all 8 categories
- **Append**: Every analysis produces new patterns that strengthen future detection
- **Self-enrich**: Patterns become more specific with more observations

**Why named subsystem:** Allows clean ownership, clear API, testable independently, queryable by other modules, defensible as a feature.

---

### Module 10: TAIG Knowledge Graph

**Purpose:** Cross-APK intelligence. **Unchanged from v1**  --  the schema and design were solid. Just now consumed by the Pattern Memory module and the revised agent loop.

**Note:** Sample Lineage Classifier (NEW sub-component) extends TAIG with active classification:
- Known family match (binary similarity > 0.85)
- Possible variant (similarity 0.6-0.85)
- New cluster (similarity < 0.6 but shares infrastructure with known cluster)
- UI-template reuse (visual similarity > 0.9 to known phishing UI)
- Code-template reuse (shared code blob > 50 lines)
- Behavior-template reuse (similar kill chain)

Even if threat actor attribution is unknown, this classification is valuable for banks.

---

### Module 11: Risk Calibration Engine ⭐ (NEW LAYER)

**Purpose:** Add an empirical calibration layer on top of the evidence score. Two-layer scoring.

**Layer A  --  Evidence Score (deterministic, unchanged):**
```
risk_score = 0.12 x permission_abuse
           + 0.20 x behavioral_indicators
           + 0.18 x code_intent_risk
           + 0.15 x network_exfiltration
           + 0.05 x code_obfuscation
           + 0.15 x brand_impersonation
           + 0.10 x campaign_association
           + 0.05 x attribution_confidence
```
Fully explainable, fully auditable.

**Layer B  --  Calibration (empirical):**

```python
class RiskCalibrationEngine:
    def __init__(self):
        # Bootstrap from public ground-truth datasets
        self.calibrator = train_calibration_model(
            dataset=load_virusshare_labeled_samples() + load_malwarebazaar_labeled(),
            feature_extractor=self._extract_calibration_features
        )
    
    def calibrate(self, evidence_score: float, calibration_features: dict) -> CalibratedScore:
        # Calibration features: pattern matches, infra confidence, family known, etc.
        calibrated_severity = self.calibrator.predict_proba(calibration_features)
        confidence_interval = self.calibrator.predict_interval(calibration_features, alpha=0.05)
        
        return CalibratedScore(
            evidence_score=evidence_score,
            calibrated_severity=calibrated_severity,  # categorical: BENIGN/SUSPICIOUS/MALICIOUS/CRITICAL
            analyst_adjusted_confidence=confidence_interval,
            reasoning="Calibrated against N public labeled samples"
        )
```

**Output:**
```json
{
  "evidence_score": 87,
  "evidence_breakdown": {
    "permission_abuse": 0.9,
    "behavioral_indicators": 0.95,
    ...
  },
  "calibrated_severity": "CRITICAL",
  "calibrated_confidence": 0.92,
  "confidence_interval": [0.85, 0.97],
  "calibration_basis": "Trained on 5,234 public labeled samples (VirusShare + MalwareBazaar + AndroZoo)",
  "explainable": true
}
```

**v2 evolution:** As bank analysts provide labels, calibration is **retrained with bank-specific data**, becoming sharper for the bank's threat landscape.

---

### Module 12: Evidence Validator + IRT Distillation ⭐ (NEW, CRITICAL)

**Purpose:** Read the verbose internal hypothesis trace and distill it into a **clean Investigation Reasoning Trace (IRT)** for external consumption.

**Internal Trace (verbose, complete, internal-only):**
```json
{
  "trace_id": "tr-abc-123",
  "hypotheses": [
    {
      "id": "H1",
      "claim": "Accessibility service abuse for overlay",
      "initial_confidence": 0.85,
      "experiments": [
        {
          "id": "H1a",
          "type": "static_check",
          "tool": "class_role_mapper",
          "result": "confirmed - AccessibilityService subclass found",
          "timestamp": "T+12s"
        },
        {
          "id": "H1b",
          "type": "dynamic_test",
          "tool": "dynamic_exploration",
          "experiment": "install mock SBI, bring to foreground",
          "result": "overlay fired at T+22s",
          "timestamp": "T+22s"
        }
      ],
      "final_status": "CONFIRMED",
      "final_confidence": 0.98,
      "evidence_citations": ["static:H1a", "dynamic:H1b", "visual:screen_5.png"]
    },
    ...
  ],
  "failed_experiments": [
    {
      "hypothesis": "H1a",
      "attempt": "launch real SBI app via DroidBot",
      "result": "real SBI not installed in test environment",
      "fallback": "installed mock SBI package instead"
    }
  ],
  "rejected_hypotheses": [...],
  "unresolved_hypotheses": [...],
  "trace_complete": true
}
```

**External IRT (clean, business-readable, what banks see):**
```
INVESTIGATION REASONING TRACE

✅ CONFIRMED: Accessibility service overlay attack
   The APK requests accessibility service permission and draws a
   pixel-perfect overlay (97% visual match) over the legitimate
   SBI YONO app, capturing user credentials.
   Evidence: Static analysis of AccessibilityService subclass;
   dynamic verification with mock SBI installation.

✅ CONFIRMED: SMS OTP interception
   A broadcast receiver intercepts incoming SMS messages and
   forwards the body to attacker infrastructure within 200ms.
   Evidence: Static analysis of SmsReceiver; simulated SMS
   triggered immediate C2 exfiltration.

✅ CONFIRMED: Context-aware C2 infrastructure
   The APK activates different C2 endpoints based on device locale.
   Evidence: Locale mutation test revealed fallback C2 activation
   on ur-PK locale.

✅ CONFIRMED: Secondary payload loader
   Encrypted URL hidden in native library, decrypts to secondary
   loader URL via Unicorn Engine emulation.

⚠️ UNRESOLVED: Possible crypto wallet targeting
   Reason: No wallet app present in test environment.
   Recommended: Re-run with wallet app installed.

RECOMMENDED ACTIONS:
   - Block 185.220.x.x:8080 at perimeter
   - Block c2-backup.evil.com at DNS level
   - Add YARA rule: BankingTrojan_GoldPickaxe_variant
   - Issue customer alert: SBI YONO "update" circulating via WhatsApp
   - File RBI CERT-In report (auto-drafted)
```

**Key principle:** **The internal trace is for the system and deep audit. The external IRT is what banks see.** Audit teams can request the full trace via `trace_id` if needed, but the default surface is always clean.

---

## 4. New Modules Added in v2

| Module | Purpose |
|---|---|
| **Fraud Attack Chain Builder** | Bank-specific output replacing generic ATT&CK as primary fraud narrative |
| **Approval Mode Controller** | Tiered human-in-the-loop for recommendations (suggest / approved / auto-push low-risk / held) |
| **Pattern Memory Engine** | The named subsystem above (Module 9) |
| **Risk Calibration Engine** | Two-layer scoring (Module 11) |
| **Evidence Validator** | The IRT distillation logic (Module 12) |
| **Sample Lineage Classifier** | TAIG sub-component for family/variant/cluster classification |
| **Brand Reference Corpus Manager** | Maintains reference screenshots/UI of legitimate bank apps for visual comparison |
| **Analyst Feedback Trainer** | Collects labels, retrains calibration and prompt optimization |

---

## 5. Fraud Attack Chain Builder ⭐ (NEW OUTPUT)

**Purpose:** Produce a **bank-specific fraud narrative**, not just generic ATT&CK mapping.

**Chain Stages (bank-specific):**

```
1. Distribution Vector
   How is the APK reaching victims? (WhatsApp, SMS, phishing site, etc.)

2. Brand Impersonation
   What legitimate app is being impersonated? How convincing?

3. Permission Acquisition
   What permissions does it request, and in what order?
   (Often the order is the signature.)

4. Credential Capture
   How does it capture user credentials?
   (Overlay, keylogger, accessibility, fake form)

5. OTP Interception
   How does it intercept OTPs?
   (SMS receiver, accessibility, notification listener)

6. Device Fingerprinting
   What device data is collected? (IMEI, contacts, location, app list)

7. Transaction Enablement
   Does it enable UPI/netbanking transactions? Add payee? Auto-trigger?

8. Persistence / Evasion
   Does it survive reboot? Hide from launcher? Detect analysis?

9. Exfiltration
   Where does stolen data go? (C2, Telegram, SMS, email)

10. Recommended Fraud Control
    What specific fraud rule change would catch this?
    (Bank's DSL format)
```

**Output Example:**
```json
{
  "fraud_attack_chain": {
    "distribution_vector": {
      "channel": "WhatsApp forwarded message with shortened URL",
      "evidence": "honeypot capture, also seen in 4 prior samples"
    },
    "brand_impersonation": {
      "impersonated_app": "com.sbi.lotus (SBI YONO)",
      "visual_similarity": 0.97,
      "package_name_strategy": "com.sbi.yono.update (typosquat)"
    },
    "permission_acquisition": {
      "requested_permissions": ["BIND_ACCESSIBILITY_SERVICE", "SYSTEM_ALERT_WINDOW", "RECEIVE_SMS", "READ_SMS"],
      "request_order": ["INTERNET (immediate)", "BIND_ACCESSIBILITY_SERVICE (T+5s)", "RECEIVE_SMS (T+10s)"],
      "deception_pattern": "Requests accessibility FIRST, before SMS  --  to enable OTP interception setup"
    },
    "credential_capture": {
      "method": "Accessibility overlay with pixel-perfect UI clone",
      "triggers": "When com.sbi.lotus is in foreground",
      "evidence": "Verified via mock SBI installation in emulator"
    },
    "otp_interception": {
      "method": "SMS receiver + accessibility service dual interception",
      "latency_to_c2": "187ms average (measured)",
      "evidence": "Simulated OTP '847291' intercepted and POSTed"
    },
    "device_fingerprinting": {
      "data_collected": ["IMEI", "phone_number", "installed_apps", "contacts"],
      "transmitted_to": "185.220.101.47:8080/device-info (initial POST)"
    },
    "transaction_enablement": {
      "adds_payee": false,
      "triggers_transaction": false,
      "note": "Attack is credential + OTP exfiltration only; attacker completes transaction manually from outside"
    },
    "persistence": {
      "survives_reboot": true,
      "hides_from_launcher": true,
      "anti_analysis": ["detects x86", "checks for frida server", "checks for Magisk"]
    },
    "exfiltration": {
      "primary_c2": "185.220.101.47:8080",
      "backup_c2": "c2-backup.evil.com (locale-triggered)",
      "encryption": "Base64 only (no real encryption  --  vulnerability for defender)"
    },
    "recommended_fraud_controls": [
      {
        "control_type": "transaction_rule",
        "rule": "Block transaction if device has app with package_pattern='com.sbi.yono.*' installed AND accessibility service is active",
        "confidence": 0.91
      },
      {
        "control_type": "network_rule",
        "rule": "Block all traffic to ASN AS9009 (Romanian hosting) from customer devices"
      },
      {
        "control_type": "customer_alert",
        "rule": "Send WhatsApp alert to customer if app matching pattern is installed"
      }
    ]
  }
}
```

This is what fraud teams **actually use**. ATT&CK is for security researchers. Fraud Attack Chain is for banks.

---

## 6. Approval Mode Controller ⭐ (NEW)

**Purpose:** Every recommendation is tagged with an **approval mode** that determines whether it can be auto-deployed or requires human sign-off.

```python
class ApprovalMode(Enum):
    SUGGEST = "suggest"           # Show in report, no action
    APPROVED = "approved"         # Deploy if analyst clicks approve
    AUTO_LOW_RISK = "auto_low_risk"  # Auto-deploy if classified as low risk
    HELD = "held"                 # Never auto-deploy, always requires human

# Examples
APPROVAL_MODES = {
    # YARA rule: adding to bank's rule library
    "add_yara_rule": ApprovalMode.AUTO_LOW_RISK,
    
    # Block IP at firewall
    "block_ip": ApprovalMode.APPROVED,
    
    # Block domain at DNS
    "block_domain": ApprovalMode.APPROVED,
    
    # Modify fraud rule
    "modify_fraud_rule": ApprovalMode.HELD,
    
    # Customer alert
    "send_customer_alert": ApprovalMode.APPROVED,
    
    # RBI compliance report
    "file_compliance_report": ApprovalMode.SUGGEST,
    
    # Disable customer account
    "disable_account": ApprovalMode.HELD,  # NEVER auto
    
    # Add to threat intel feed (MISP)
    "push_to_misp": ApprovalMode.AUTO_LOW_RISK,
}
```

Banks will require this. Default is conservative.

---

## 7. The Investigation Loop  --  Concrete Data Flow

### 7.1 Full Investigation Cycle

```
[CYCLE 1]
Hypothesis Engine: Initial hypotheses from triage
    H1 (high): Accessibility overlay attack
    H2 (high): SMS interception
    H3 (medium): Network exfiltration
    H4 (low): Native payload
    H5 (low): Anti-analysis

Tool Selector (Module 2/3):
    Run static tools: androguard, jadx, FlowDroid, YARA, Semgrep
    (cheap, fast)

Reverse Engineering Workbench (Module 2):
    Produces artifact model:
    - class_roles: AccessibilityStealer (CONFIRMED), SmsReceiver (CONFIRMED)
    - method_intents: sendDataToServer -> credential exfiltration
    - attack_flow: full chain identified

Hypothesis Update:
    H1 -> CONFIRMED (artifact model)
    H2 -> CONFIRMED (artifact model)
    H3 -> CONFIRMED (artifact model)
    H4 -> UNRESOLVED (no .so analysis yet)
    H5 -> CONFIRMED (anti-debug code found)

[CYCLE 2]
Hypothesis Engine: New hypotheses from confirmed
    H6 (new): Does the overlay actually capture credentials at runtime?
    H7 (new): Does SMS interception actually fire?
    H8 (new): Is there an environmental trigger?
    H4 (revisit): Native library analysis

Tool Selector:
    Run Hook Planning Agent (Module 4)
    Hook plan: accessibility + SMS + network + crypto hooks
    Run DroidBot-GPT UI exploration (Module 5/6)

Dynamic Exploration Agent (Module 6):
    Investigation as described in v2
    Mock SBI installation -> overlay confirmed
    Credential input -> exfiltration confirmed
    SMS simulation -> OTP theft confirmed
    Locale mutation -> C2 pivot confirmed

Hypothesis Update:
    H6 -> CONFIRMED
    H7 -> CONFIRMED
    H8 -> CONFIRMED
    H4 -> CONFIRMED (Unicorn emulation found hidden URL)

[CYCLE 3]
Hypothesis Engine: Convergence check
    All major hypotheses resolved
    Some minor unresolved (e.g., wallet targeting)
    -> Distill to IRT

[OUTPUT]
- Internal trace (immutable, audit DB)
- External IRT (clean, what banks see)
- Fraud attack chain (bank-specific)
- Risk score (two-layer, calibrated)
- Recommendations (with approval modes)
- Pattern Memory updates (new patterns added)
- TAIG updates (new relationships)
- YARA rules (auto-generated)
- STIX 2.1 bundle
- MISP sync
```

---

## 8. Updated Module Stack Diagram

```
┌──────────────────────────────────────────────────────────────┐
│  MODULE 1: Ingestion & Triage                                │
│  FastAPI, Phi-3 Mini, APKiD, ssdeep                         │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 2: AI Reverse Engineering Workbench ⭐               │
│  DeepSeek-Coder-V2, structured artifact model               │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 3: Static Analysis Engine                            │
│  androguard, jadx, FlowDroid, YARA, Semgrep, BinDiff        │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 4: Hook Planning Agent ⭐                            │
│  Adaptive Frida plan based on static findings              │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 5: Dynamic Analysis Engine                           │
│  AVD, Frida, mitmproxy, Scapy, Strace                      │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 6: Dynamic Exploration Agent ⭐ (CENTRAL)            │
│  Mistral-Large, AI-operated targeted investigation          │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 7: Visual Intelligence Engine ⭐ (UPGRADED)          │
│  CLIP + OCR + Logo + Layout + LLaVA hybrid                 │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  HYPOTHESIS ENGINE (loops back if not converged) ⭐          │
│  Live scratchpad, internal trace                            │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 8: AI Reasoning Cortex                               │
│  5 agents + Debate Layer                                    │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 9: Malware Pattern Memory ⭐ (NAMED SUBSYSTEM)        │
│  8 pattern categories, queryable, self-enriching           │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 10: TAIG Knowledge Graph                             │
│  Neo4j + Qdrant, Sample Lineage Classifier                  │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 11: Risk Calibration Engine ⭐                       │
│  Two-layer scoring: evidence + empirical                   │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  MODULE 12: Evidence Validator + IRT Distillation ⭐         │
│  Clean external report from verbose internal trace         │
└───────────────────────┬──────────────────────────────────────┘
                        v
┌──────────────────────────────────────────────────────────────┐
│  Fraud Attack Chain Builder ⭐ + Approval Mode Controller ⭐ │
│  Bank-specific output + tiered human-in-the-loop           │
└───────────────────────┬──────────────────────────────────────┘
                        v
                       REPORT
```

---

## 9. Why This Architecture Wins

| Property | Achieved By |
|---|---|
| **AI-native, not AI-wrapped** | AI Reverse Engineering Workbench + Dynamic Exploration Agent |
| **Hypothesis-driven** | Hypothesis Engine + recursive loop |
| **Adaptive** | Hook Planning Agent updates mid-run |
| **Bank-specific** | Fraud Attack Chain Builder |
| **Explainable** | Two-layer risk scoring + clean IRT |
| **Auditable** | Internal trace stored immutably |
| **Self-improving** | Pattern Memory + TAIG + calibration |
| **Safe to deploy** | Approval Mode Controller |
| **Anti-hallucination** | Evidence Validator + tool-grounded agents |
| **Compounding moat** | All 12 modules enrich each other |

---

*This is the architecture. Implementable today. Defensible tomorrow.*
