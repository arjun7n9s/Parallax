# Band of Agents Hackathon — PARALLAX-CASE Submission Plan

> **Status:** Confirmed go-decision. Track 3 (Regulated & High-Stakes Workflows). Building only after main PARALLAX is complete — this file is the resume point for future planning sessions.

---

## 1. Hackathon decoded — what they actually want

### Stated criteria (verbatim priorities)
- **At least 3 agents** collaborating through Band (Track 3 examples use 5-7+ — this is a minimum, not a target)
- **Band must be the actual collaboration layer**, not a final notification ping or thin wrapper
- Agents must **@mention each other, challenge each other, recruit peers, hand off tasks, share structured context** *during* the workflow
- The **room transcript is the product**

### The implicit bar (what actually wins)
- Rejecting the Track 3 example list as generic ("compliance review," "legal contract") — winners use Band as a **governance surface**, not a chat surface
- Showing visible **agent-to-agent disagreement and resolution**, not sequential handoffs
- Domain depth — Track 3 explicitly lists "compliance, risk, or **cybersecurity investigation** workflows" and "**financial services approval** workflows"
- 5+ agents minimum, ideally 8+ to clearly exceed the bar

### Tracks
| Track | Domain | Fit for PARALLAX |
|---|---|---|
| Track 1 | Internal Enterprise Workflows | Misfit — HR/finance/procurement is generic |
| Track 2 | Multi-Agent Software Development | Misfit — coding teams, not our domain |
| **Track 3** | **Regulated & High-Stakes Workflows** | **Direct match — bank fraud investigation** |

**Track 3 chosen.**

---

## 2. The submission: PARALLAX-CASE on Band

### One-line pitch
A bank APK-fraud investigation cockpit where 8+ specialist agents collaborate inside a Band room per fraud case, challenging each other's findings and producing a final action packet (freeze request, reimbursement recommendation, cyber-cell complaint, IOC package) for human officer approval.

### Why this passes the "PARALLAX is the center, not a wrapper" bar
PARALLAX's v2 architecture already designs 10+ specialist agents. Band becomes the **room** they collaborate in. Zero rewrite of PARALLAX core — only a new adapter layer wires existing agents to Band.

The submission's center is PARALLAX. The hackathon's tech (Band + AI/ML API + Featherless) snaps onto PARALLAX as:
- **Band** → the agent collaboration room (governance surface, not chat)
- **Featherless AI** → serverless fallback inference for open-source models
- **AI/ML API** → multi-model cloud API for specialized agent roles

---

## 3. The 8+ agent team

| # | Agent name | PARALLAX module source | Framework | Model |
|---|---|---|---|---|
| 1 | Intake Agent | Triage Agent (Pydantic AI) | Pydantic AI | Phi-3 / Llama 3 8B (small, fast) |
| 2 | Transaction Trace Agent | (new) Money flow reconstructor | LangGraph | DeepSeek-V3 / Claude (reasoning) |
| 3 | Device Compromise Agent | Hypothesis Engine + Frida Hook Planner | LangGraph | DeepSeek-Coder-V2 (code) |
| 4 | Mule Graph Agent | Pattern Memory Engine + TAIG | LangGraph | DeepSeek-V3 (reasoning) |
| 5 | Telecom / SIM Risk Agent | (new) SIM swap, call forwarding, device binding | Pydantic AI | Mistral / Llama 3 70B |
| 6 | Customer Liability Agent | (new) RBI-style liability reasoning | Pydantic AI | Claude (careful reasoning) |
| 7 | Legal Evidence Agent | (new) Cyber-cell-ready evidence | Pydantic AI | Claude (careful narrative) |
| 8 | Visual Phishing Agent | Brand Impersonation Engine (CLIP + LLaVA/InternVL) | Custom | LLaVA / InternVL (multimodal) |
| 9 | Evidence Validator Agent | (new) v2 skeptical reviewer | Pydantic AI | Claude (challenge mode) |
| 10 | Decision Convenor Agent | Recommendation Engine + Risk Calibration | LangGraph | Claude (synthesis) |
| 11 | (optional) Regulatory Reporting Agent | RBI/CERT-In report generator | Pydantic AI | Mistral (structured output) |

**Cross-framework is intentional and visible to judges:**
- Pydantic AI: structured extraction/validation (agents 1, 5, 6, 7, 11)
- LangGraph: stateful multi-step reasoning (agents 2, 3, 4, 10)
- Custom: multimodal visual analysis (agent 8)
- Anthropic adapter: careful narrative/synthesis (agents 6, 7, 9, 10)
- This is exactly what Band's "cross-framework" requirement rewards

---

## 4. Band room protocol — the "meaningful usage" surface

### Room creation
- One Band room per fraud case: `CASE-FR-2026-00421`
- Intake Agent creates the room on case open
- All 8+ agents auto-recruited at room creation (visibility = all in room, but only @mentioned agents process each message)

### Structured message schema (what agents exchange)
Each message in the room follows a structured format — not free-text chat:
```json
{
  "type": "evidence | hypothesis | challenge | request | decision | escalation",
  "from_agent": "device_compromise_agent",
  "to_agents": ["@legal_evidence_agent", "@transaction_trace_agent"],
  "case_id": "CASE-FR-2026-00421",
  "confidence": 0.82,
  "content": {
    "claim": "AccessibilityService abuse detected in com.fake.sbi.SmsReceiver",
    "evidence_refs": ["obs-001", "obs-002", "frida-hook-log-114"],
    "reasoning_summary": "..."
  },
  "supports_or_contradicts": ["msg-42", "msg-43"]
}
```

### Collaboration primitives (what makes Band the governance layer, not chat)
- **@mention routing** — only mentioned agents process a message
- **Challenge** — `@Device_Compromise_Agent your report says accessibility abuse. Can you prove install time preceded the disputed transactions?`
- **Recruit peer** — Device Agent notices an APK finding → recruits Brand Impersonation Agent for visual verification
- **Structured evidence refs** — every claim links to Observation IDs, not vibes
- **Confidence + evidence** separation — judges see agents building cases with evidence
- **Decision Convenor gating** — final action packet only issued when all open challenges are resolved
- **Human officer in the loop** — fraud officer is a real Band room member, can @mention any agent

### The transcript IS the demo
The 3-minute submission video should show a real Band room transcript scrolling, not a polished UI. Band's room UI itself is the product. Example flow embedded in the room:

```
[Intake Agent] Case CASE-FR-2026-00421 opened. Customer reports ₹3.4L lost 
               after installing APK from WhatsApp. Extracted entities: 
               phone, 3 UPI IDs, 2 APK hashes, complaint time T+41min.
               @Transaction Trace Agent Reconstruct the fund movement.

[Transaction Trace Agent] 7 UPI transfers across 3 beneficiary accounts 
               in 11 minutes. Mule pattern confidence 0.89. 
               Recommending immediate freeze radius: 3 direct + 2 downstream.
               @Device Compromise Agent The APK hash is attached. Determine 
               whether device compromise plausibly caused the transactions.

[Device Compromise Agent] AccessibilityService permission present. 
               SMS receiver registered for OTP interception. 
               Overlay attack vector matches GoldPickaxe pattern (0.82).
               @Mule Graph Agent Do these beneficiary accounts overlap 
               with prior cases?

[Mule Graph Agent] 2 of 3 accounts appear in 4 prior mule-cluster cases 
               from last quarter. Cluster confidence 0.91.

[Liability Agent] Reporting time was T+41min. Customer did not share 
               credentials. Provisional credit recommended under policy 4.2.
               @Device Compromise Agent Can you prove install time preceded 
               the first transaction?

[Device Compromise Agent] Install time 09:14:33. First transfer 09:25:47. 
               11-minute gap. Timeline supports compromise.
               @Legal Evidence Agent Convert this into cyber-cell-ready 
               evidence without overclaiming attribution.

[Legal Evidence Agent] Drafted complaint packet. Cautious on attribution; 
               strong on timeline and IOC reuse.

[Decision Convenor Agent] Final action packet ready for human review:
  1. Freeze request for 3 direct beneficiary accounts
  2. Enhanced monitoring on 2 downstream accounts
  3. Provisional credit to customer
  4. APK IOC package: 2 hashes, 4 C2 domains, 1 cert fingerprint
  5. Cyber-cell complaint draft
  6. RBI fraud taxonomy mapping complete
```

This transcript shows every collaboration primitive: agent recruitment, @mention routing, challenge/response, evidence references, confidence tracking, decision gating.

---

## 5. PARALLAX integration — what changes vs what stays

### Stays untouched (the core engine)
- All v2 modules: hypothesis engine, fraud chain stage, pattern memory, temporal fingerprint, evidence validator, risk calibration, brand impersonation
- Local Ollama models (banking compliance — on-prem requirement)
- Neo4j TAIG graph
- RE tools: Frida, MobSF, Ghidra, androguard, YARA
- Python agent frameworks: LangGraph, Pydantic AI
- Postgres metadata store

### New components (only what's needed for the hackathon)
1. **`parallax/agents/band_adapter.py`** — Band SDK wrapper that registers each PARALLAX agent as a Band peer, implements the structured message schema, and handles @mention routing
2. **`parallax/agents/room_protocol.py`** — Defines the structured message types (evidence/hypothesis/challenge/request/decision/escalation) and the confidence/evidence reference format
3. **`parallax/agents/convenor.py`** — Decision Convenor agent that gates final action packet issuance until all open challenges resolved
4. **`parallax/agents/human_officer.py`** — Adapter exposing a human fraud officer as a Band room member
5. **Featherless integration** — Cloud-fallback inference path for agents when local GPU saturated
6. **AI/ML API integration** — Multi-model API access for specialized agent roles
7. **One synthetic demo case** — Pre-analyzed synthetic APK with full PARALLAX output loaded into the room for the demo video

### Why the engine is untouched
Band is the room, not the engine. The 8+ agents already exist in PARALLAX v2 docs. The adapter just connects them to Band's room protocol. International story: PARALLAX remains a self-contained on-prem bank product. Band is a deployment option for cases where multi-agent collaboration governance is needed (fraud ops, cyber-cell coordination, internal audit).

---

## 6. Partner tech integration — the real adoption plan

### AI/ML API ($100 sponsor credits + $100 existing balance + $1000 best-use bonus)
**Adoption plan:**
- Use AI/ML API as the **multi-model cloud API** for specialized agent roles where local Ollama is too slow or unavailable
- Specific agent-model routing:
  - **Triage Agent** → small fast model (Phi-3, Llama 3 8B) via AI/ML API
  - **Code Interpretation Agent** → DeepSeek-Coder-V2 via AI/ML API
  - **Reasoning/Synthesis Agent** → Claude or GPT-4o via AI/ML API
  - **Multimodal Visual Phishing Agent** → LLaVA/InternVL via AI/ML API
- Single API key → many models → cleaner than per-provider integration
- **Best-use case to claim the $1000 bonus:** "Best Use of AI/ML API to power model orchestration, reasoning, automation, extraction, or multimodal workflows" → model orchestration is exactly what we're doing. Each agent picks the right model from the AI/ML API marketplace based on its role. The Decision Convenor agent orchestrates which model is called for which task.

### Featherless AI (500 inference credits + $200 Claw Pro plan)
**Adoption plan:**
- Use Featherless as the **serverless fallback inference path** for open-source models when local Ollama is saturated
- Specific workloads:
  - Burst inference during high case load (PARALLAX bursty by nature — fraud spikes during tax season, festival sales, salary weeks)
  - Specialized models that aren't worth running locally 24/7 (e.g. specific code models only used for APK analysis)
  - Cost-effective multi-model experimentation without buying GPU
- **Production benefit:** when a bank's GPU is overloaded, Featherless picks up the slack without forcing the bank to buy more hardware. This is **durable production tech** for PARALLAX, not just hackathon usage.
- **Best-use case to claim the bonus:** "Best Use of Featherless AI to integrate open-source model inference into an agent, workflow, automation system, or real-world AI application" → exactly what we're doing. Featherless is the production-grade inference layer for PARALLAX's open-source model needs.

### Adoption honesty (important for judges)
- Document the local-first / cloud-fallback architecture honestly
- Show that AI/ML API and Featherless are **production infra**, not hackathon gimmicks
- Demonstrate clear migration path: bank runs PARALLAX fully on-prem, falls back to cloud only when needed
- This is the real international story: PARALLAX scales from single-bank on-prem to multi-bank SaaS without rewriting

---

## 7. Team of 6 — role allocation

| Role | Person | Responsibilities |
|---|---|---|
| **Lead architect** | (you) | PARALLAX-Band integration design, agent protocol, submission narrative |
| **Backend agent dev #1** | TBD | Band adapter + room protocol + Convenor agent |
| **Backend agent dev #2** | TBD | Featherless + AI/ML API integration, agent-model routing |
| **Backend agent dev #3** | TBD | PARALLAX core agent modules (Fraud Chain, Pattern Memory, Hypothesis Engine) wiring |
| **Frontend / demo** | TBD | Synthetic case scenario, Band room recording, demo video |
| **Documentation / submission** | TBD | Architecture diagrams, submission text, partner tech writeup |

Team of 6 → $60 Featherless credits + $50 AI/ML API per person sponsor total. (Verify per-participant math with kickoff announcement.)

---

## 8. Demo case scenario — the synthetic fraud case

**Case ID:** `CASE-FR-2026-00421`
**Customer complaint (synthetic):**
> "₹3.4L lost after installing 'SBI YONO KYC Update' APK from WhatsApp link. 7 UPI transfers to 3 accounts in 11 minutes. Phone now shows suspicious accessibility-service app. SIM replacement 2 days before fraud."

**Pre-analyzed outputs loaded for demo:**
- Synthetic APK hash: `sha256:abc123...` (benign, not real malware)
- Extracted entities: phone, 3 UPI IDs, 2 APK hashes, complaint time T+41min
- PARALLAX analysis output: class roles, method intents, Frida hook logs, brand impersonation screenshots, IOC package
- Mock transaction trace data: 7 transfers, 3 beneficiaries
- Mock mule graph data: 2 of 3 accounts in prior cases

**Why synthetic:** keeps submission clean, avoids real malware samples, fully reproducible.

**Demo flow (target: 3 minutes):**
1. Open Band room `CASE-FR-2026-00421` (5s)
2. Intake Agent posts case packet (10s)
3. Transaction Trace Agent reconstructs fund movement (20s)
4. Device Compromise Agent reports accessibility abuse + GoldPickaxe pattern match (20s)
5. Mule Graph Agent finds 2-account overlap with prior cases (15s)
6. Evidence Validator challenges: `@Device_Compromise_Agent your confidence is 0.82, but accessibility abuse can be benign. What else supports the OTP theft claim?` (15s)
7. Device Compromise Agent responds with SMS receiver + C2 evidence (15s)
8. Liability Agent posts liability recommendation (15s)
9. Legal Evidence Agent drafts cyber-cell complaint (15s)
10. Decision Convenor issues final action packet (15s)
11. Human officer in room: `@Decision_Convenor approved with one modification — hold the 2 downstream accounts, don't freeze yet.` (10s)
12. Architecture diagram: PARALLAX core + Band room + AI/ML API + Featherless (15s)

Total: ~3 min. Every primitive visible: agent recruitment, @mention routing, challenge/response, evidence refs, confidence tracking, decision gating, human-in-loop.

---

## 9. Win strategy

### Why we'd podium
1. **Track 3 fit is undeniable** — they listed bank fraud investigation, financial services approval, cybersecurity investigation as their explicit example domains
2. **8+ agents is 2.5x their minimum** — depth of collaboration obvious
3. **Band is the governance layer, not chat** — challenge/recruit/escalate visible throughout
4. **Domain is hard** — most submissions will be generic compliance bots. PARALLAX has real IOCs, real timeline analysis, real evidence chain, real RBI/CERT-In framing
5. **PARALLAX is real, not a wrapper** — 10 docs and growing code behind it
6. **Partner tech is genuinely adopted, not sticker** — Featherless as production fallback, AI/ML API as multi-model orchestrator

### Risks
- Demo is brutal — 3-min video must show real Band room, not slides
- Track 3 competition may be moderate to high — go for top 3, not just participation
- Synthetic case must be credible to judges unfamiliar with Indian banking — explain context clearly

### Bonus prize strategy
- **$1000 AI/ML API bonus** → claim via "model orchestration" story (Decision Convenor routes each agent to the right model from the AI/ML API marketplace)
- **$200 Featherless Claw Pro + 500 inference credits** → claim via "real-world AI application" story (PARALLAX in production at banks, with Featherless as the production fallback inference layer)

---

## 10. Build order (only after main PARALLAX is complete)

| Phase | Duration | Deliverable |
|---|---|---|
| Phase 1: Band adapter prototype | 3-4 days | `band_adapter.py` + `room_protocol.py` working with 2 agents in a test room |
| Phase 2: All 8+ agents wired | 5-6 days | Each PARALLAX agent connected to Band with structured message schema |
| Phase 3: Synthetic case scenario | 2-3 days | Pre-analyzed synthetic APK + mock data + demo flow script |
| Phase 4: Partner tech integration | 2-3 days | Featherless + AI/ML API routing implemented + documented |
| Phase 5: Demo recording + editing | 2-3 days | 3-min video showing live Band room transcript + architecture diagram |
| Phase 6: Submission packaging | 1-2 days | Submission text, partner tech writeup, architecture diagram, video upload |
| **Total** | **~3 weeks** | **Submission ready** |

---

## 11. Resume point for future sessions

When you return to plan this in depth, start by reading:
1. This file (submission framing + decisions)
2. `C:\Users\arjun\Desktop\PSBs\01_IDEATION.md` (PARALLAX core design)
3. `C:\Users\arjun\Desktop\PSBs\02_ARCHITECTURE.md` (5-layer system)
4. `C:\Users\arjun\Desktop\PSBs\06_TAIG_SCHEMA.md` (Neo4j graph for Mule Graph Agent)
5. `C:\Users\arjun\Desktop\PSBs\07_AGENT_PROMPTS.md` (existing LLM prompts to reuse)

Then dive into:
- Band SDK docs (https://docs.band.ai/) — agent API, rooms, @mention routing
- Featherless AI setup guide (revealed at kickoff stream)
- AI/ML API Discord for promo code
- PARALLAX v2 modules in `C:\Users\arjun\Desktop\parallax_repo\src\parallax\models\v2\`

---

## 12. Open questions to resolve at kickoff

1. Featherless setup guide + promo code (revealed at kickoff stream)
2. AI/ML API promo code (announced at kickoff)
3. Per-participant credit math (verify $50 AI/ML API × 6 = $300, but earlier said $100 team total)
4. Band SDK Python version + agent registration flow specifics
5. Whether Band supports structured JSON messages natively or needs string-encoded JSON
6. Whether multi-framework agent registration is one-process-per-framework or unified process
7. Demo recording format preferences (live demo with judge interaction? pre-recorded? screen capture only?)

---

## 13. Final verdict snapshot

| Dimension | Verdict |
|---|---|
| PARALLAX fit | ★★★★★ — Track 3 is our track, 8+ agents already designed |
| Tech integration | ★★★★★ — Band = room, Featherless = production infra, AI/ML API = model orchestration |
| Win chance | ★★★★☆ — Track 3 competition moderate; 8+ agents + real domain is strong |
| Build cost | ★★★★☆ — One new adapter, demo case, room transcript; ~3 weeks |
| International leverage | ★★★★★ — Reference architecture for regulated multi-agent fraud |
| Credits/support | ★★★★☆ — $100+ AI/ML API, $25/person Featherless, both permanent tech |
| Bonus prize potential | ★★★★☆ — $1000 AI/ML API bonus + $200 Featherless bonus both reachable |

**Confirmed: GO on Track 3, PARALLAX-CASE on Band.**
