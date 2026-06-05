# PARALLAX  --  Vision Document
## The Anchor Document  --  Everything Else Derives From This

---

## 1. The One-Sentence Definition

PARALLAX is a **GenAI-native automated malware reverse engineering and APK fraud analysis platform** that operates as an autonomous investigator  --  forming hypotheses, selecting tools, guiding runtime exploration, interpreting code, reconstructing fraud attack chains, and producing evidence-first reports with empirically calibrated risk scores.

---

## 2. The Mental Model  --  AI Investigator, Not Tool Runner

The single most important product decision is **who drives the analysis.**

### The Wrong Mental Model (Most Tools)

```
Tools analyze APK -> Output goes to LLM -> LLM summarizes -> Report
```

PARALLAX is not a wrapper. The LLM does not "wait for tools to finish." PARALLAX's AI is the **investigator**  --  the tools are its instruments.

### The Right Mental Model (PARALLAX)

```
AI forms initial hypotheses about what this APK is and what it does
   v
AI chooses which tools to run first (cheap static checks vs. expensive emulation)
   v
AI interprets intermediate findings
   v
AI updates hypotheses  --  confirms, rejects, or spawns new ones
   v
AI decides what to do next  --  which code to read deeper, what to hook at runtime,
   what environmental mutations to try, what bank app to mock-install
   v
AI launches targeted dynamic exploration  --  not generic sandboxing
   v
AI verifies or rejects each hypothesis with concrete experiments
   v
AI produces evidence-first report with clean Investigation Reasoning Trace
```

**The AI is the analyst. The tools are the analyst's microscope, sandbox, and runtime probes. The graph is the analyst's long-term memory.**

---

## 3. The Five Non-Negotiable Design Pillars

These are the architectural decisions that flow through every module. If a design choice violates one, it's the wrong choice.

### Pillar 1  --  Hypothesis-Driven, Not Pipeline-Driven

PARALLAX is a **cyclic investigation loop**, not a one-pass pipeline. Every analysis maintains a live hypothesis scratchpad. The system:

- Forms initial hypotheses from cheap signals (manifest, permissions, prior samples)
- Selects minimum-cost experiments to test them
- Updates hypotheses based on results
- Spawns new hypotheses from confirmed ones
- Abandons dead-end hypotheses with explicit "rejected" status
- Documents unresolved hypotheses with reasons and recommended next steps

**Internal trace is verbose and complete. External trace (IRT) is clean and auditable.**

### Pillar 2  --  Pattern Memory as a First-Class Subsystem

YARA rules, semantic embeddings, ATT&CK mappings, behavior timelines, code idioms, UI phishing templates, certificate reuse, packer fingerprints  --  these are not scattered features. They are one named subsystem: **Malware Pattern Memory** with seven explicit pattern categories:

1. Known fraud flows
2. Suspicious permission/API chains
3. Code idioms
4. UI phishing templates
5. C2 communication patterns
6. Certificate reuse
7. Packer/obfuscator fingerprints
8. (added) Behavioral timing fingerprints

Pattern Memory is **queryable, append-only, and self-enriching.** Every analysis produces new patterns that strengthen future detection.

### Pillar 3  --  Fraud Attack Chain, Not Just ATT&CK Mapping

Banks don't care about generic ATT&CK technique IDs. They care about **fraud chains** that map directly to their risk models:

```
Distribution Vector -> Brand Impersonation -> Permission Acquisition
    -> Credential Capture -> OTP Interception -> Device Fingerprinting
    -> Transaction Enablement -> Persistence/Evasion -> Exfiltration
    -> Recommended Fraud Control
```

This is a **dedicated output**, not a side effect of ATT&CK mapping. It's the artifact fraud teams actually use.

### Pillar 4  --  Two-Layer Risk Scoring

Risk scoring has two distinct layers, both required:

**Layer A  --  Evidence Score (deterministic, auditable)**
- Weighted sum of observed evidence components
- Reproducible, explainable, mathematically transparent
- Satisfies auditors, compliance, legal review

**Layer B  --  Calibrated Severity (empirically grounded)**
- Trained on historical analyst-labeled samples
- Calibrates the evidence score against ground truth
- Outputs analyst-adjusted confidence interval
- Uses bootstrap datasets (VirusShare, MalwareBazaar, AndroZoo) in v1
- Uses bank's own analyst labels in v2

Final score = Evidence Score x Calibration Function. Both layers are exposed in the report. Compliance gets the formula. Analysts get the calibration.

### Pillar 5  --  Evidence-First Report Schema

Every generated report separates four categories explicitly:

1. **Observed facts**  --  direct tool outputs, screenshots, hook firings
2. **Inferred conclusions**  --  agent reasoning grounded in observed facts
3. **Uncertain hypotheses**  --  flagged with low confidence and reasons
4. **Recommended actions**  --  human-approved via tiered approval modes

This is the **hallucination defense** built into the report structure itself. No claim appears in any category without supporting evidence from category 1.

---

## 4. The Investigation Loop  --  How PARALLAX Actually Works

### 4.1 Phase A  --  Initial Hypothesis Formation

**Inputs:** APK manifest, permissions, certificate, ssdeep match against known samples, package name heuristics

**Action:** Static-Triage Agent reads these and produces **5-15 initial hypotheses** ranked by plausibility:

```
H1 (high): Accessibility service abuse + overlay attack
     --  BIND_ACCESSIBILITY_SERVICE requested
     --  SYSTEM_ALERT_WINDOW permission requested
     --  Package name pattern matches known impersonation

H2 (high): SMS interception for OTP theft
     --  RECEIVE_SMS + READ_SMS permissions
     --  Manifest declares SMS receiver

H3 (medium): Credential exfiltration via HTTP
     --  INTERNET permission
     --  Code contains hardcoded URL pattern

H4 (low): Native library contains hidden payload
     --  Native .so file present
     --  No obvious function exports

H5 (low): Anti-analysis techniques
     --  Has anti-debug code patterns
     --  Detects x86 architecture
```

**Output:** Initial hypothesis scratchpad with confidence scores and proposed experiments.

### 4.2 Phase B  --  Adaptive Tool Selection

**Action:** Reverse Engineering Agent reads the hypothesis scratchpad and **selects minimum-cost tools to test top hypotheses first.**

This is **not running everything.** It is intelligent tool selection:

```
H1 (accessibility overlay) -> static intent analysis of AccessibilityService subclasses
H2 (SMS interception) -> static analysis of SmsMessage usage
H3 (HTTP exfil) -> string analysis for URLs, FlowDroid taint from SMS to network
H4 (native payload) -> only if H1-H3 inconclusive OR strong .so indicators
H5 (anti-analysis) -> deobfuscate first, then re-analyze
```

**Cost optimization:** Run cheap static checks first. Only escalate to expensive operations (Unicorn emulation, full dynamic analysis) when hypotheses warrant.

### 4.3 Phase C  --  Static Deep Dive (Reverse Engineering Workbench)

**Action:** AI Reverse Engineering Workbench processes the decompiled code, producing a structured artifact model:

```json
{
  "class_roles": [
    {
      "class": "com.fake.sbi.SmsReceiver",
      "role": "OTP interception broadcast receiver",
      "confidence": 0.96,
      "evidence": ["extends BroadcastReceiver", "calls SmsMessage.createFromPdu", "posts body to URL"]
    },
    {
      "class": "com.fake.sbi.AccessibilityStealer",
      "role": "Credential overlay via accessibility service",
      "confidence": 0.98,
      "evidence": ["extends AccessibilityService", "draws fullscreen window", "monitors foreground app"]
    }
  ],
  "method_intents": [
    {
      "method": "sendDataToServer",
      "intent": "credential exfiltration",
      "sources": ["EditText password field"],
      "sinks": ["HttpURLConnection POST to 185.220.x.x:8080"]
    }
  ],
  "attack_flow": [
    "request accessibility permission",
    "monitor foreground banking app",
    "draw fake login overlay",
    "capture credentials",
    "intercept OTP via SMS receiver",
    "exfiltrate to C2"
  ],
  "native_findings": {
    "packed": false,
    "encrypted_strings": 0,
    "suspicious_exports": ["decrypt_payload"]
  }
}
```

**This is the AI Reverse Engineering Workbench.** It is not "decompilation + LLM summarization." It is a structured semantic analysis of code that produces a precise attack model.

### 4.4 Phase D  --  Adaptive Hook Planning

**Action:** Hook Planning Agent reads the static findings and **generates a targeted Frida hook plan**:

```
Detected: SMS API usage
    -> Enable: sms_interception.js
    -> Hook targets: SmsManager, SmsMessage
    -> Capture: body, sender, timestamp

Detected: Accessibility service
    -> Enable: accessibility_abuse.js
    -> Hook targets: AccessibilityService, AccessibilityEvent
    -> Capture: package transitions, overlay windows

Detected: HttpURLConnection with hardcoded IP
    -> Enable: network_logger.js
    -> Hook targets: HttpURLConnection, URL
    -> Decode: base64 payloads

Detected: WebView
    -> Enable: webview_inspector.js
    -> Hook targets: WebView, loadUrl
    -> Capture: URLs, form data, JavaScript bridges

Detected: Crypto operations
    -> Enable: crypto_extraction.js
    -> Hook targets: Cipher, SecretKeySpec, KeyGenerator
    -> Capture: keys, IVs, plaintext before encryption
```

**The hook plan is adaptive**  --  it can be updated mid-run if new behaviors are observed:

```
T+45s: Runtime shows DexClassLoader invocation
       -> INJECT: dynamic_class_loader.js retroactively
T+60s: Crypto API fired
       -> INJECT: crypto_extraction.js retroactively
T+75s: C2 beacon detected with custom protocol
       -> INJECT: binary_protocol_decoder.js retroactively
```

### 4.5 Phase E  --  AI-Guided Dynamic Exploration

**Action:** Dynamic Exploration Agent operates the Android environment like a trained fraud investigator. **Not a passive sandbox.**

The agent operates through the Dynamic UI Explorer, which:

- Decides **what screen to explore next** based on what static found
- Generates **realistic fake inputs** (credentials, OTPs, biometrics)
- Triggers **permission grant flows** that the malware expects
- Detects **dormant behavior** and tries environmental mutations to wake it
- Installs **mock banking apps** to trigger context-aware overlays
- Watches **for C2 beacons** and decodes protocols in real-time

**Example investigation flow:**

```
T+0s:   Install APK, launch in clean emulator
T+5s:   App requests BIND_ACCESSIBILITY_SERVICE -> grant it
T+10s:  App shows generic "loading" screen
T+15s:  AI: "Per H1, this app is likely an overlay attacker.
        Let me install a mock SBI YONO package and bring it to foreground."
T+18s:  Mock SBI installed, brought to foreground
T+20s:  PARALLAX app draws fullscreen overlay on top of mock SBI
T+22s:  AI: "Overlay confirmed. Let me input fake credentials and watch what happens."
T+25s:  Fake username/password typed into overlay fields
T+27s:  Network hook fires: POST to 185.220.x.x with base64-encoded credentials
T+30s:  AI: "Credentials exfiltrated. Now testing H2  --  SMS interception."
T+35s:  Simulate incoming SMS with fake OTP "847291"
T+37s:  SMS hook fires: SmsReceiver captures body, posts to C2 within 200ms
T+40s:  AI: "Both H1 and H2 confirmed. Initiating mutation test  --  change locale."
T+45s:  Locale changed to ur-PK
T+48s:  App behavior changes  --  new C2 endpoint activated (c2-backup.evil.com)
T+50s:  AI: "Context-aware malware confirmed. Locale-dependent C2 pivot."
T+55s:  Capture final state, stop exploration
```

**This is AI-operated targeted investigation, not generic sandboxing.** Every action is hypothesis-driven. Every observation updates the scratchpad. The loop continues until hypotheses are confirmed, rejected, or explicitly marked unresolved.

### 4.6 Phase F  --  Hypothesis Update and Iteration

**Action:** Throughout Phases C-E, the Hypothesis Engine maintains a live scratchpad:

```
H1: Accessibility overlay attack
    H1a: Static found AccessibilityService subclass -> CONFIRMED
    H1b: Mock SBI installation triggered overlay -> CONFIRMED (T+20s)
    H1c: Overlay UI matches SBI YONO at 97% -> CONFIRMED (visual)
    STATUS: CONFIRMED  --  Strong evidence

H2: SMS interception for OTP theft
    H2a: Static found SmsReceiver with network post -> CONFIRMED
    H2b: Simulated SMS triggered exfiltration -> CONFIRMED (T+37s)
    STATUS: CONFIRMED  --  Strong evidence

H3: Crypto wallet targeting
    H3a: Static found no wallet APIs -> REJECTED
    H3b: No wallet app installed during test -> INCONCLUSIVE
    STATUS: UNRESOLVED  --  Recommended re-run with wallet app

H4: Native library hidden payload
    H4a: r2pipe analysis of .so found no suspicious strings -> REJECTED
    H4b: Unicorn emulation of decrypt_payload found hidden URL -> CONFIRMED
    STATUS: CONFIRMED  --  secondary loader detected
```

### 4.7 Phase G  --  Distillation to External Report

**Action:** Synthesis Agent reads the full internal hypothesis trace and produces a **clean Investigation Reasoning Trace (IRT)** for external consumption.

**Internal trace (verbose, technical, complete):**
- Timestamps of every event
- Failed experiments
- Intermediate states
- Tool calls and retries
- Agent reasoning at each step

**External IRT (clean, business-readable, auditable):**
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
   No wallet app present in test environment. Recommended:
   re-run with wallet app installed.

RECOMMENDED ACTIONS (analyst approval required):
   - Block 185.220.x.x:8080 at perimeter
   - Block c2-backup.evil.com at DNS level
   - Add YARA rule: BankingTrojan_GoldPickaxe_variant
   - Issue customer alert: SBI YONO "update" circulating via WhatsApp
   - File RBI CERT-In report (auto-drafted)
```

The IRT is the **only artifact** analysts and executives see. The internal trace is stored immutably in the audit DB, accessible via `trace_id` if a deep audit is ever needed.

---

## 5. The Recursive Loop  --  Why It's Powerful

The phases above are not strictly sequential. PARALLAX loops:

```
Hypothesis Update -> New Tool Selection -> New Static Findings
    -> Updated Hook Plan -> New Dynamic Findings -> New Hypotheses
        -> Continues until convergence or time budget exhausted
```

A real investigation might look like:

```
Cycle 1: Static finds accessibility + SMS permissions
    -> Initial hypotheses H1, H2
    -> Run cheap static checks
    
Cycle 2: Static finds hardcoded C2 IP
    -> New hypothesis H3 (network exfiltration)
    -> Add network hook
    -> Run targeted dynamic test
    
Cycle 3: Dynamic reveals overlay on mock SBI
    -> H1 confirmed strongly
    -> H4 spawned (what does overlay do with inputs?)
    -> Inject credential-capture hooks
    -> Re-run targeted test
    
Cycle 4: Hooks capture credentials posted to C2
    -> H4 confirmed
    -> H5 spawned (does it work without banking app?)
    -> Run mutation test with no banking app
    -> Confirms it stays dormant
    -> H5 confirmed (dormancy confirmed)
    
Cycle 5: Reached convergence
    -> All major hypotheses resolved
    -> Distill to IRT
    -> Generate report
```

**This is the AI Investigator.** It doesn't run a fixed pipeline. It investigates, like a human would  --  but at machine speed and machine scale.

---

## 6. The Twelve Core Modules

PARALLAX is built from twelve named modules, each with a clear purpose.

| # | Module | Role |
|---|---|---|
| 1 | **Ingestion & Triage Layer** | Accept APKs, pre-screen, prioritize |
| 2 | **AI Reverse Engineering Workbench** | Structured code interpretation (class roles, method intents, attack flow) |
| 3 | **Static Analysis Engine** | androguard, jadx, FlowDroid, YARA, Semgrep, binary diffing |
| 4 | **Hook Planning Agent** | Adaptive Frida instrumentation based on static findings |
| 5 | **Dynamic Analysis Engine** | AVD + Frida + mitmproxy + DroidBot-GPT |
| 6 | **Dynamic Exploration Agent** | AI-operated targeted investigation, not passive sandbox |
| 7 | **Visual Intelligence Engine** | CLIP + OCR + logo detection + LLaVA  --  hybrid brand impersonation |
| 8 | **AI Reasoning Cortex** | 5 specialized agents + Debate Layer + Synthesis |
| 9 | **Malware Pattern Memory** | Named subsystem: 8 pattern categories, queryable, self-enriching |
| 10 | **TAIG Knowledge Graph** | Cross-APK intelligence, Neo4j + Qdrant |
| 11 | **Risk Calibration Engine** | Two-layer scoring: evidence + empirical calibration |
| 12 | **Evidence Validator & Report Generator** | Distills to clean IRT, generates fraud attack chain output |

**Supporting modules:**
- **Approval Mode Controller**  --  tiered human-in-the-loop for recommendations
- **Pattern Memory Engine**  --  append-only pattern storage
- **Sample Lineage Classifier**  --  known family / variant / new cluster / template reuse
- **Brand Reference Corpus Manager**  --  known bank app references for visual comparison
- **Analyst Feedback Trainer**  --  calibration improvement from human labels

---

## 7. Output Artifacts  --  What Banks Actually Get

### 7.1 Investigation Report (PDF + JSON)

```
Section 1: Executive Summary
   Plain English, business impact, 1 paragraph

Section 2: Risk Score (Two Layers)
   Evidence Score: 87/100 (explainable breakdown)
   Calibrated Severity: CRITICAL (95% confidence)
   Analyst-Adjusted Confidence: ±3 points

Section 3: Fraud Attack Chain
   Distribution -> Impersonation -> Permission Acquisition
   -> Credential Capture -> OTP Interception -> Device Fingerprinting
   -> Transaction Enablement -> Exfiltration

Section 4: Investigation Reasoning Trace (IRT)
   ✅ CONFIRMED hypotheses
   ⚠️ UNRESOLVED hypotheses (with reason + next step)
   ❌ REJECTED hypotheses (collapsed, not exposed)

Section 5: Evidence
   Tool outputs (citations)
   Screenshots (visual evidence)
   Network captures (C2 evidence)
   Code excerpts (function-level)

Section 6: Pattern Matches
   Pattern Memory hits (which known patterns matched)

Section 7: Recommended Actions (with approval status)
   [SUGGEST] Issue customer alert
   [APPROVED] Block IP 185.220.x.x
   [AUTO] Add YARA rule to library
   [HELD] Modify fraud rule (requires analyst sign-off)
```

### 7.2 Machine-Readable Outputs

- **STIX 2.1 bundle**  --  for MISP, OpenCTI, SIEM
- **YARA rule**  --  auto-generated, tested, deployable
- **Suricata/Snort rules**  --  for network detection
- **Fraud rule DSL**  --  for bank's fraud engine
- **Threat intel feed**  --  for peer banks via MISP

---

## 8. The Strategic Moat  --  Why PARALLAX Wins

| Moat Element | How It Compounds |
|---|---|
| **Malware Pattern Memory** | Every APK makes pattern detection sharper |
| **TAIG Knowledge Graph** | Cross-sample intelligence no competitor can replicate |
| **Calibration Engine** | Better calibrated with every labeled sample |
| **Self-evolution loop** | System measurably improves without human retraining |
| **Analyst Feedback Trainer** | Each bank's labels make their instance sharper |
| **Fraud Attack Chain** | Bank-specific output competitors don't even attempt |
| **Hypothesis-driven design** | AI-native architecture, not retrofitted LLM |

After 6 months in production:
- 10,000+ APKs analyzed
- 500+ threat actors mapped in TAIG
- 50,000+ IOCs in graph
- 1,000+ patterns in Pattern Memory
- Calibration trained on thousands of analyst labels

A new competitor starting today is **6 months behind**  --  and falling further.

---

## 9. What PARALLAX Is NOT

To be unambiguous:

- **Not a single-LLM wrapper.** PARALLAX is a multi-agent system with adaptive tool orchestration.
- **Not just static analysis.** PARALLAX is hypothesis-driven dynamic investigation, not passive sandboxing.
- **Not just ATT&CK mapping.** PARALLAX outputs **fraud attack chains** specific to banking fraud.
- **Not a black box.** PARALLAX's reasoning is exposed in the clean IRT with full evidence chain.
- **Not auto-deploying customer-impacting controls.** PARALLAX uses tiered approval modes.
- **Not a point tool.** PARALLAX is a **platform** with growing intelligence.

---

## 10. The Mandate  --  Why This Satisfies the Funder's Requirements

The funder asked specifically for:
- ✅ **GenAI for automated reverse engineering** -> AI Reverse Engineering Workbench (Module 2) + structured artifact model
- ✅ **Malware pattern recognition** -> Malware Pattern Memory (Module 9) as a named subsystem
- ✅ **Automated code interpretation** -> Hypothesis-driven static analysis with class role maps, method intents, attack flow
- ✅ **Intelligent threat summarization** -> Synthesis Agent + Evidence Validator + clean IRT distillation

Plus what the funder didn't ask for but banks need:
- ✅ **AI-guided dynamic exploration** (not passive sandboxing)
- ✅ **Fraud attack chain reconstruction** (bank-specific)
- ✅ **Two-layer calibrated risk scoring** (empirically grounded)
- ✅ **Adaptive hook planning** (mid-run instrumentation updates)
- ✅ **Pattern Memory as first-class subsystem** (named, queryable, self-enriching)

---

## 11. Closing Statement

PARALLAX is what happens when GenAI is positioned as the **investigator** rather than the **narrator**. The platform is an AI that thinks  --  that forms hypotheses, tests them, updates them, and concludes with auditable evidence.

It is built for banks. It speaks the language of fraud. It is defensible by its compounding intelligence. It is auditable by design.

Everything that follows in the architecture, tech stack, implementation phases, and supporting documents is derived from this vision.

---

*This is the anchor. Every other document is interpreted through this lens.*
