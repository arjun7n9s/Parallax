# PARALLAX — Ideation Document
## Persistent APK Risk Analysis via Lateral LLM-Augmented eXpertise

---

## 1. Problem Statement

### 1.1 The Threat Landscape

Fraudsters increasingly distribute malicious mobile applications (APKs) through:
- **WhatsApp** (forwarded links, contact-trading apps, fake KYC)
- **SMS** (smishing with shortened links)
- **Email** (phishing attachments)
- **Social media** (Telegram, Instagram DMs)
- **Phishing domains** (fake bank portals hosting the APK)
- **Third-party app stores** (sideloaded APKs bypassing Play Protect)

These fraudulent APKs are engineered to:
- Steal customer credentials (banking login, UPI PIN, card details)
- Intercept OTPs from SMS / authenticator apps
- Hijack accessibility services to draw fake UI overlays
- Perform unauthorized financial transactions via UPI/net-banking deep-links
- Exfiltrate contacts, photos, location, and device metadata
- Establish persistent C2 channels for staged payload delivery

### 1.2 Why Current Solutions Fail

| Existing Approach | Failure Mode |
|---|---|
| **Manual analysis by humans** | Slow (4–24 hours per APK), expensive, depends on scarce expertise |
| **VirusTotal / signature AV** | 3–6 months behind novel malware; useless against polymorphic packers |
| **MobSF standalone** | No reasoning layer; produces dumps, not intelligence |
| **Sandboxes (Cuckoo/CAPE)** | Detected and evaded by context-aware malware |
| **Single-LLM wrappers** | Hallucinate; no grounding in actual tool outputs; no knowledge retention |
| **Rule-based fraud systems** | Brittle; defeated by minor code mutation |

### 1.3 The Core Gap

**No existing system combines:**
1. Deep static + dynamic + visual analysis
2. Multi-agent AI reasoning grounded in real tool outputs
3. Cross-APK intelligence (each new sample enriches a living knowledge graph)
4. Self-evolution (system gets smarter without human retraining)
5. Actionable outputs (fraud rules, blocklists, ATT&CK mappings — not just PDFs)

---

## 2. The PARALLAX Vision

> *A flagship, flagship-grade cyber-defense platform that thinks, reasons, and evolves like a human expert team — but operates at machine speed and machine scale.*

### 2.1 One-Line Definition
PARALLAX is a **Generative-AI-orchestrated, multi-agent, self-evolving malware analysis platform** that ingests suspicious APKs, performs deep multi-dimensional analysis using the best open-source security tools, reasons about the results with specialized AI agents grounded in a living threat knowledge graph, and produces actionable intelligence for banks.

### 2.2 Architectural Philosophy

```
Traditional:    APK → [single tool] → human reads output → verdict
PARALLAX:       APK → [multi-tool] → [AI agents reason] → [graph enriched]
                                                            ↓
                                            system is now smarter
                                            for next APK arrival
```

---

## 3. The Three Differentiating Innovations

### 3.1 Innovation 1 — The Temporal Adversarial Intelligence Graph (TAIG)

**The single biggest architectural breakthrough.**

Every existing tool analyzes APKs **in isolation, at a point in time.** TAIG treats APKs as **nodes in a living, persistent, queryable knowledge graph** — and the graph itself becomes the intelligence source.

```
                    TAIG — Living Knowledge Graph

    APK_001 ──[SHARES_CODE_WITH 0.87]──► APK_047
       │                                     │
    [SPAWNS]                            [EVOLVED_FROM]
       │                                     │
    APK_023 ──[TARGETS]──► HDFC_App       APK_089
       │                                     │
    [USES_C2]                            [USES_C2]
       └──────────► IP:185.x.x.x ◄───────────┘
                          │
                   [GEOLOCATES_TO]
                       Romania/VPS
                          │
                   [LINKED_TO]
                   ThreatActor:GoldFactory
```

**What this enables that no single-APK tool can answer:**

- *"Is this APK part of an active campaign targeting Indian banks right now?"*
- *"Which threat actor wrote this — and what did their last 6 APKs do?"*
- *"This C2 IP appeared in 3 other APKs last week — it's an infrastructure pivot"*
- *"This code block was in BankBot 2022 → modified in 2023 → this is generation 4"*
- *"If we block this campaign's infrastructure, what's the predicted next move?"*

**Schema highlights (Neo4j):**
- 10 node types: `APK`, `Permission`, `API`, `IPAddress`, `Domain`, `Certificate`, `ThreatActor`, `Campaign`, `CodeBlob`, `BankApp`
- 20+ relationship types: `REQUESTS`, `CALLS`, `COMMUNICATES_WITH`, `IMPERSONATES`, `SHARES_CODE_WITH`, `EVOLVED_FROM`, `ATTRIBUTED_TO`, `PART_OF`, `TARGETS_SECTOR`, `USES_PACKER`, `SIGNED_BY`, etc.
- Each relationship carries a confidence score and timestamp

**Two-graph architecture:**
- **Neo4j** — the structural knowledge graph (relationships, attribution, campaigns)
- **Qdrant** — the semantic vector space (code-intent embeddings for similarity search)

### 3.2 Innovation 2 — Multi-Agent AI Reasoning Cortex with Debate Layer

**The right model for the right job, with contradiction as a signal.**

PARALLAX does not use one LLM. It uses a **specialized agent team** with defined roles, a debate protocol, and confidence arbitration:

| Agent | Model | Specialization |
|---|---|---|
| Triage Agent | Phi-3 Mini (local, <2s response) | Fast pre-scoring from manifest + permissions only |
| Code Interpreter Agent | DeepSeek-Coder-V2 (32B, local via Ollama) | Reads decompiled smali/Java, classifies intent per code block |
| Behavior Analyst Agent | Mistral-Large / Llama-3.1-70B | Interprets runtime event stream, narrates what app *did* |
| Intel Correlator Agent | RAG over MITRE ATT&CK + MISP (via LlamaIndex) | Maps behaviors to ATT&CK techniques, finds campaign links |
| Visual Intelligence Agent | LLaVA-OneVision or InternVL (multimodal) | Analyzes UI screenshots for phishing overlays |
| Synthesis Agent | GPT-4o or Claude Opus (API) | Final risk scoring, report generation, reasoning arbitration |

**Orchestrated via LangGraph** (stateful multi-agent graph) + **CrewAI** (role-based agent management).

**The Debate Layer — the most underappreciated architectural element:**

When agents disagree (e.g., Static says benign, Dynamic says malicious), PARALLAX does not just average scores. It **surfaces the contradiction as a high-confidence alert** — because **evasion IS the signature.** An APK that looks clean but behaves dirty is exactly what sophisticated malware does.

```python
# Conceptual debate layer logic
if static_score < 0.3 and dynamic_score > 0.8:
    alert_level = "CRITICAL_EVASION_SUSPECTED"
    reason = "Clean code surface, malicious runtime behavior — likely polymorphic staging"
    confidence += 0.15  # contradictions are informative
```

### 3.3 Innovation 3 — Visual Intelligence Layer (Multimodal LLM)

**The underused superpower no existing tool has.**

Sophisticated APKs don't just have malicious code — they have **malicious UI**. Phishing overlays, fake bank login screens, accessibility-service-driven UI hijacking. String matching can't catch this. Code analysis often misses it.

PARALLAX captures **every screen state during dynamic analysis** and feeds screenshots to a multimodal LLM (LLaVA-OneVision / InternVL):

- *"This screen is a pixel-perfect clone of ICICI iMobile"*
- *"This overlay appears only when the real bank app is in foreground"*
- *"The fake login form fields are positioned identically to the legitimate target"*
- *"Accessibility service is reading screen content to the attacker every 200ms"*

**Outputs:**
- Brand impersonation score (visual similarity %)
- Phishing overlay attack proof (with screenshot evidence)
- Accessibility-service abuse detection

**No string-matching AV can do this. No static analyzer can do this. Only multimodal vision can.**

---

## 4. Why This Is a Flagship Product

### 4.1 Comparison Matrix

| Dimension | Existing Tools | PARALLAX |
|---|---|---|
| Multi-tool analysis | ❌ Single-tool focus | ✅ 15+ tools orchestrated |
| AI reasoning | ❌ None or single-LLM | ✅ Specialized agent team |
| Cross-APK intelligence | ❌ Isolated analysis | ✅ Living knowledge graph |
| Code similarity search | ❌ Hash only | ✅ Semantic embedding search |
| Visual UI detection | ❌ None | ✅ Multimodal LLM |
| Campaign attribution | ❌ None | ✅ TAIG graph traversal |
| Self-evolution | ❌ Static rules | ✅ Auto YARA + graph enrichment |
| ATT&CK mapping | ⚠️ Manual | ✅ Auto-generated per sample |
| Fraud rule output | ❌ None | ✅ DSL recommendations |
| RBI compliance format | ❌ None | ✅ Built-in |
| MISP / STIX output | ⚠️ Partial | ✅ Full STIX 2.1 |
| On-premise deployable | ⚠️ Some | ✅ Fully local with Ollama |
| Speed | ⚠️ Hours-days | ✅ Minutes per APK |

### 4.2 Flagship Product Traits (All Present)

1. **Architectural innovation** — TAIG is genuinely novel
2. **Right use of AI** — LLM for reasoning, not magic; right model for right job
3. **Open-source leverage** — every tool in the stack is best-in-class
4. **Self-improvement** — measurable gains over time without human input
5. **Actionable outputs** — not reports, but *machine-actionable intelligence*
6. **Standards-compliant** — STIX 2.1, MITRE ATT&CK, MISP
7. **Deployable** — runs on a bank's on-prem infrastructure
8. **Defensible moat** — the knowledge graph is the moat; competitors can't replicate accumulated threat intel easily

### 4.3 The Strategic Moat

```
APK analyzed by PARALLAX
        ↓
New YARA rules generated
New IOCs added to graph
New semantic embeddings indexed
New ATT&CK mappings stored
        ↓
System is measurably smarter
        ↓
        × Repeat for every APK
        ↓
After 6 months, PARALLAX has:
- 10,000+ APK samples analyzed
- 500+ threat actors mapped
- 1,000+ active campaigns tracked
- 50,000+ IOCs in graph
- Local YARA rules catching novel variants

→ Competitor starting today is 6 months behind
```

---

## 5. Open-Source Ecosystem Map (The Arsenal)

PARALLAX is built entirely on battle-tested open-source tools. No proprietary malware engine required.

### 5.1 Static Analysis Stack

| Tool | Purpose | Why Chosen |
|---|---|---|
| **androguard** | Python APK/DEX parsing | Mature, well-documented Python API |
| **jadx** | Java decompilation | Best Smali→Java output quality |
| **apktool** | Resource decoding, smali disassembly | Industry standard |
| **r2pipe** (Radare2) | Binary-level analysis | Open-source alternative to IDA Pro |
| **BinDiff** / **Diaphora** | Binary similarity / diffing | Find reused code across samples |
| **FlowDroid** | Taint analysis (data flow) | Precise: traces where data goes |
| **Unicorn Engine** | CPU emulation | Execute obfuscated decryptors without full OS |
| **APKiD** | Packer/protector detection | Fast pre-screening |
| **ssdeep** | Fuzzy hashing | Similarity pre-filter |
| **Semgrep** | Pattern-based code scanning | Custom rules for banking malware |
| **YARA** | Industry-standard malware rules | Self-generated rules in feedback loop |
| **NetworkX** | Graph analysis | Permission-API-call graphs |
| **simplify** (deobfuscator) | Undo ProGuard/DexGuard | See through obfuscation |

### 5.2 Dynamic Analysis Stack

| Tool | Purpose | Why Chosen |
|---|---|---|
| **Frida** | Runtime instrumentation | Hook any function live, JS/Python API |
| **mitmproxy** | HTTPS traffic interception | Decrypts SSL with installed CA |
| **Scapy** | Custom protocol analysis | Beyond HTTP — any binary protocol |
| **Android AVD** (emulator) | Sandboxed execution | Headless, scriptable, scalable |
| **Strace / ltrace** | System call tracing | File/process/IPC observation |
| **CAPE Sandbox** (fallback) | Behavioral monitoring | When Frida insufficient |

### 5.3 Visual AI Stack

| Tool | Purpose | Why Chosen |
|---|---|---|
| **LLaVA-OneVision** | Multimodal LLM | State-of-the-art open multimodal |
| **InternVL 2.0** | Multimodal LLM | Strong on UI/document understanding |
| **Pillow** | Image processing | Pre-processing |
| **OpenCV** | Image diffing | Pixel-level comparison |

### 5.4 AI/LLM Stack

| Model | Size | Purpose | Deployment |
|---|---|---|---|
| Phi-3 Mini | 3.8B | Triage (<2s pre-score) | Ollama (local) |
| DeepSeek-Coder-V2 | 16B-236B | Code interpretation | Ollama (local) |
| Mistral-Large / Llama-3.1-70B | 70-123B | Behavior analysis | Ollama (local) or vLLM |
| LLaVA-OneVision | 7B-13B | Visual UI analysis | Ollama (local) |
| GPT-4o / Claude Opus | API | Final synthesis & scoring | API (optional, can be local) |

### 5.5 Orchestration & Knowledge

| Tool | Purpose |
|---|---|
| **LangGraph** | Stateful multi-agent graph orchestration |
| **CrewAI** | Role-based agent team management |
| **LlamaIndex** | RAG over threat intel corpora |
| **DSPy** | Compiled, optimized LLM pipelines (not raw prompts) |

### 5.6 Knowledge Graph & Vector

| Tool | Purpose |
|---|---|
| **Neo4j** | Primary knowledge graph (structural relationships) |
| **NebulaGraph** | Scale-out option for billions of edges |
| **Qdrant** | Vector similarity search (semantic APK embeddings) |
| **MISP** | Threat intelligence sharing platform |
| **OpenCTI** | Cyber threat intel platform (alternative) |

### 5.7 Infrastructure

| Tool | Purpose |
|---|---|
| **Docker** | Container packaging |
| **Kubernetes** | Orchestration (production scale) |
| **FastAPI** | REST API layer |
| **Celery + Redis** | Async task queue |
| **MinIO** | S3-compatible APK storage |
| **PostgreSQL** | Metadata store |
| **Grafana** | Dashboards |
| **OpenTelemetry + Jaeger** | Distributed tracing |

---

## 6. Business Value for Banks

### 6.1 Direct Value

- **Faster detection**: Hours/days → minutes
- **Earlier warnings**: Customer-reported → system-pre-flageed
- **Reduced fraud losses**: Proactive blocking vs reactive reimbursement
- **Lower analyst cost**: Automation of 80%+ of routine analysis
- **Compliance ready**: RBI CERT-In, SEBI cyber reporting formats auto-generated
- **Audit trail**: Every claim cited to tool output + evidence

### 6.2 Strategic Value

- **Threat actor visibility**: Know who's targeting your bank specifically
- **Campaign prediction**: TAIG enables forecasting of next attack waves
- **Defense tuning**: AI-recommended fraud rule changes
- **Cross-bank intel** (with MISP sharing): Industry-wide awareness
- **Brand protection**: Detect phishing apps impersonating your bank instantly

### 6.3 Compliance

- RBI Master Direction on Digital Lending (2022)
- RBI Cyber Security Framework (2016, updated)
- SEBI CSCRF (Cybersecurity & Cyber Resilience Framework)
- IT Act 2000 / 2008 amendments
- DPDP Act 2023 (Digital Personal Data Protection)

PARALLAX outputs are pre-formatted for these reporting requirements.

---

## 7. Competitive Landscape

### 7.1 Direct Competitors (Limited Overlap)

| Competitor | Strength | PARALLAX Advantage |
|---|---|---|
| **MobSF** (open source) | Mature static analyzer | PARALLAX adds AI reasoning + graph + visual |
| **VirusTotal** (Google) | Massive signature DB | Useless against novel; no reasoning |
| **Any.Run** (commercial) | Interactive sandbox | Manual; no autonomous reasoning |
| **Joe Sandbox** (commercial) | Deep behavior analysis | No cross-sample intelligence |
| **Yoroi** / **Todyl** (commercial) | Managed detection | Not specialized for APKs |
| **Lookout** (mobile security) | Consumer/enterprise | Not an analysis platform |

### 7.2 PARALLAX's Defensible Position

- **Knowledge graph as moat** — accumulated threat intel not easily replicable
- **Multi-agent AI reasoning** — no competitor has this layer
- **Visual intelligence** — unique differentiator
- **Open-source stack** — lower cost, audit-friendly, no vendor lock-in
- **On-premise** — meets bank data residency requirements

---

## 8. Research References & Inspirations

| Source | Inspiration |
|---|---|
| **MITRE ATT&CK for Mobile** | Behavior categorization taxonomy |
| **STIX 2.1** (OASIS) | Threat intel output standard |
| **MISP Project** (circl.lu) | Threat sharing platform architecture |
| **MobSF** (ajinabraham) | Mobile security framework foundation |
| **APKiD** (rednaga) | Packer detection inspiration |
| **CAPE Sandbox** | Behavioral analysis patterns |
| **OpenCTI** (Filigran) | Threat intel platform UI/UX |
| **DSPy** (Stanford) | Compiled LLM pipeline design |
| **LangGraph** (LangChain) | Multi-agent orchestration patterns |
| **Neo4j Graph Data Science** | Graph-based threat hunting |
| **Any.Run research blog** | Real-world APK analysis case studies |
| **ThreatFabric** reports | Banking trojan analysis publications |
| **Group-IB / Kaspersky APT reports** | Threat actor attribution methodology |

---

## 9. Project Naming & Branding (Optional)

- **PARALLAX** — Self-Evolving Neural Threat Intelligence Engine for Lateral Analysis
- Tagline: *"Multiple perspectives. One persistent truth."*
- Logo concept: Owl with neural network eyes over an APK shape

---

## 10. Success Metrics

A flagship product must be measurable:

| Metric | Target |
|---|---|
| APK analysis time | < 10 minutes end-to-end |
| Detection rate (known malware) | > 99% |
| Detection rate (novel variants, 0-day) | > 85% |
| False positive rate | < 2% |
| YARA rules auto-generated | 5+ per analyzed sample |
| New graph relationships per APK | 20+ |
| ATT&CK techniques mapped | 10+ per malicious APK |
| Fraud rule recommendations | 3+ actionable per critical APK |
| Self-improvement measurement | Measurable precision/recall gain per 100 samples |

---

## 11. Ethical & Legal Considerations

- All malware samples handled in isolated analysis environment
- No customer PII processed without explicit consent
- Honeypot operations require legal review (jurisdiction-dependent)
- Threat intel sharing via MISP must respect sharing community rules
- AI outputs reviewed for hallucination before action recommendations
- Audit trail mandatory for all automated fraud rule deployments

---

## 12. What Comes Next

This ideation document establishes the **WHY**. The next documents establish:
- **`02_ARCHITECTURE.md`** — the HOW (system design)
- **`03_TECH_STACK.md`** — the WHAT (every tool, every version)
- **`04_IMPLEMENTATION_PHASES.md`** — the WHEN (phased build plan)
- **`05_API_DESIGN.md`** — the INTERFACE (REST endpoints)
- **`06_TAIG_SCHEMA.md`** — the GRAPH (Neo4j schema specification)
- **`07_AGENT_PROMPTS.md`** — the BRAIN (LLM agent prompt library)
- **`08_TESTING_STRATEGY.md`** — the VERIFICATION (how we know it works)
- **`09_DEPLOYMENT.md`** — the RUN (production deployment)
- **`10_INNOVATION_LOG.md`** — what makes each piece novel (for stakeholders)

All files live in `~/Desktop/PSBs/`.
