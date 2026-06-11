# UiPath AgentHack — PARALLAX-CASE Submission Plan

> **Status:** Confirmed go-decision (after Band of Agents). Track 1 (UiPath Maestro Case). Building only after main PARALLAX is complete — this file is the resume point for future planning sessions.

---

## 1. Hackathon decoded — what they actually want

### Stated criteria (verbatim priorities)
- **Build a real, working solution on the UiPath Platform** — "not a concept, nor a slide deck, but a working solution that handles complexity, survives interruptions, keeps humans in the loop, and solves something that matters"
- 7 weeks of hacking time
- $50K cash across three tracks
- **Bonus points** for using **UiPath for Coding Agents** (Claude Code, Codex, Cursor, Gemini CLI) to build the solution — "use coding agents to build coding agents" is the meta-move
- **UiPath must be the execution and orchestration layer** — they explicitly encourage mixing in external framework agents (LangChain, CrewAI, AutoGen), but UiPath orchestrates everything
- Must run on **UiPath Automation Cloud** (not just locally)
- Track 1, 2, or 3 — only one per project

### The implicit bar (what actually wins)
- "Coding agents have redefined how we build" — they're positioning UiPath as the *governance and operation* layer for the new world of AI coding agents
- Rejecting Track 1 example list (insurance claims, patient care, HR onboarding) as generic — winners will pick a domain with real depth
- Bonus on UiPath for Coding Agents rewards meta-build: use Claude Code / Codex / Cursor to build parts of the solution itself
- Strong submissions show: working prototype + end-to-end flow + real-world complexity handling + clear documentation another developer could extend

### Tracks
| Track | Domain | Fit for PARALLAX |
|---|---|---|
| **Track 1** | **UiPath Maestro Case — dynamic, exception-heavy business processes, case management, agent handoffs, human-in-loop** | **Direct match — fraud case management** |
| Track 2 | UiPath Maestro BPMN — predictable sequence processes | Misfit — fraud is exception-heavy, not predictable |
| Track 3 | UiPath Test Cloud — agentic software testing | Misfit — wrong domain |

**Track 1 chosen.**

---

## 2. The submission: PARALLAX-CASE on UiPath Maestro

### One-line pitch
PARALLAX-CASE on UiPath Maestro: a bank APK-fraud case management system where PARALLAX's AI agents do the analysis, UiPath Maestro orchestrates the case lifecycle, UiPath RPA pulls data from legacy banking systems without APIs, and a human fraud officer approves the final action packet at a real human-in-loop checkpoint.

### Why this passes the "PARALLAX is the center" bar
PARALLAX's analysis engine stays the AI brain. UiPath becomes the **case orchestration + enterprise integration layer.** UiPath fills three real production gaps PARALLAX has today:
1. **RPA for legacy banking systems** — banks have core banking systems, ERPs, payment gateways, fraud case management tools without modern APIs. UiPath RPA does screen scraping + data entry + workflow automation on these systems
2. **Production case management** — UiPath Maestro Case is a production-grade case lifecycle engine with state machines, SLA tracking, escalation rules, human-in-loop UI, audit logs. PARALLAX's case management is currently custom-built
3. **Enterprise distribution** — UiPath Marketplace lets you publish agents. PARALLAX as a UiPath-published agent = instant access to UiPath's enterprise customer base (every major bank uses UiPath)

### What's in the submission
- **PARALLAX AI agents** (the engine) — unchanged
- **UiPath Maestro Case** — orchestrates the fraud case lifecycle (intake → triage → static analysis → dynamic analysis → reasoning → human approval → action packet)
- **UiPath RPA** — pulls customer KYC, transaction history, account flags from bank's legacy systems (mocked for demo)
- **UiPath Agent Builder** — UiPath-native agents for case intake form, officer approval UI, action packet dispatch
- **External framework agents (PARALLAX's Python)** — integrated via UiPath's external agent support
- **UiPath for Coding Agents** — use Claude Code or Codex to build parts of the case workflow itself (bonus points)

---

## 3. Case lifecycle on UiPath Maestro

### Stages (the Maestro case flow)
1. **Intake** — UiPath Agent (or web form) receives fraud complaint. RPA pulls customer KYC + recent transaction history from bank core (mocked). PARALLAX Intake Agent normalizes + extracts entities. Case created in Maestro with full evidence packet.
2. **Triage** — PARALLAX Triage Agent scores urgency. Maestro routes to one of three tracks based on severity: fast-track (low value), standard, or high-priority with immediate freeze.
3. **Static Analysis** — PARALLAX Static Analysis Agent runs. UiPath RPA uploads APK to PARALLAX engine API. PARALLAX returns class roles, method intents, IOC list. Maestro stores structured evidence.
4. **Dynamic Analysis** (conditional) — PARALLAX Dynamic Agent + Frida Hook Planner runs if APK warrants deeper analysis. RPA launches Android emulator instance via PARALLAX infrastructure. Maestro tracks runtime.
5. **Hypothesis & Correlation** — PARALLAX Hypothesis Engine + Mule Graph Agent run. Maestro waits for both, validates evidence chain, escalates to human if any agent reports confidence < threshold.
6. **Human Approval** — Fraud officer receives case in UiPath Action Center. Reviews evidence, approves / rejects / requests more. This is the explicit human-in-loop checkpoint.
7. **Action Packet Dispatch** — Maestro orchestrates: freeze request → bank's core system (RPA), reimbursement recommendation → core banking, IOC package → SIEM (Splunk if integrated), cyber-cell complaint draft → legal team
8. **Case Closure & Audit** — Maestro closes case, writes audit log, archives evidence chain

### The "exception-heavy" pitch
Fraud cases are **fundamentally exception-heavy.** Static and dynamic analysis may disagree, new evidence may arrive mid-case, customer may call with new info, mule account may have a hold. Maestro's case management is built for exactly this. Show the submission handling:
- Mid-case new evidence (UI re-injects)
- Agent disagreement escalation to human
- Conditional stage skip (low-value cases skip dynamic analysis)
- Parallel investigation tracks (transaction + device + telecom run in parallel, Maestro joins)

---

## 4. The agent map — PARALLAX on UiPath

| Stage | UiPath layer | PARALLAX component | Framework |
|---|---|---|---|
| Intake | UiPath Agent Builder (form) + RPA (KYC pull) | PARALLAX Intake Agent | Pydantic AI |
| Triage | UiPath Agent Builder | PARALLAX Triage Agent | Pydantic AI |
| Static Analysis | UiPath API Workflow calls PARALLAX | PARALLAX Static Analysis + Hypothesis Engine | LangGraph + Pydantic AI |
| Dynamic Analysis | UiPath API Workflow + RPA (emulator control) | PARALLAX Dynamic Agent + Frida Hook Planner | LangGraph |
| Visual Phishing | UiPath API Workflow | PARALLAX Brand Impersonation Engine (CLIP + LLaVA/InternVL) | Custom |
| Mule Graph | UiPath API Workflow | PARALLAX Mule Graph Agent + Pattern Memory + TAIG | LangGraph |
| Evidence Validation | UiPath Agent Builder | PARALLAX Evidence Validator | Pydantic AI |
| Human Approval | UiPath Action Center | Human fraud officer (real person in the loop) | N/A |
| Action Packet | UiPath RPA + API Workflows | PARALLAX Recommendation Engine | LangGraph |
| Audit | UiPath built-in audit log | PARALLAX Audit Logger | Custom |

### Cross-framework demonstration
UiPath explicitly encourages mixing frameworks. PARALLAX uses:
- **Pydantic AI** (structured extraction, validation)
- **LangGraph** (multi-step reasoning, stateful workflows)
- **Custom** (multimodal visual analysis)
- **RPA** (legacy system integration)
- **Agent Builder** (low-code UiPath-native agents)

This is a real cross-framework story for judges, not a sticker.

---

## 5. UiPath for Coding Agents — the bonus move

UiPath gives bonus points for using **UiPath for Coding Agents (Claude Code, Codex, Cursor, Gemini CLI) to build any part of the solution.**

### How we'd use it
- Use **Claude Code or Codex to scaffold the Maestro case workflow JSON** (the case definition file) — show the LLM generating valid UiPath Maestro case config from natural language spec
- Use **Claude Code or Codex to generate the PARALLAX-UiPath adapter code** — show the LLM writing the integration code following UiPath patterns
- Use **Codex or Cursor to generate the RPA workflows** for legacy system integration (mocked bank core, fake SIEM, etc.)
- Show in the demo video: "I asked Claude Code to build a UiPath Maestro case for this fraud workflow, here's what it generated, I reviewed and refined it"

### Why this matters for the bonus
UiPath is positioning itself as the platform where AI builds AI. Showing actual coding-agent usage to build the solution is the meta-move that signals "I get it." Even 20-30% of the codebase generated by coding agents is enough to claim the bonus.

---

## 6. What stays untouched vs what's new

### Stays untouched (PARALLAX core)
- All v2 modules: hypothesis engine, fraud chain stage, pattern memory, temporal fingerprint, evidence validator, risk calibration, brand impersonation
- Local Ollama models
- Neo4j TAIG
- RE tools: Frida, MobSF, Ghidra, androguard, YARA
- Python agent frameworks

### New components
1. **`parallax/integrations/uipath/`** — adapter package
   - `case_definition.py` — exports PARALLAX's case flow as a UiPath Maestro case definition
   - `agent_adapters.py` — wraps each PARALLAX agent as a UiPath-callable service
   - `rpa_workflows/` — UiPath RPA projects for legacy system integration (mocked)
   - `action_center.py` — human-in-loop integration with UiPath Action Center
   - `audit_sync.py` — syncs PARALLAX audit log with UiPath audit log
2. **One synthetic demo case** — pre-analyzed synthetic APK + mock bank core data
3. **UiPath Automation Cloud deployment** — fully working deployment, not local mock
4. **Demo video** showing end-to-end case flow on UiPath cloud

### Why the engine is untouched
UiPath is the orchestration and integration layer, not the analysis engine. PARALLAX remains self-contained. UiPath becomes one of multiple deployment options (alongside direct API, Band, Splunk).

---

## 7. Team of 6 — role allocation

| Role | Person | Responsibilities |
|---|---|---|
| **Lead architect** | (you) | PARALLAX-UiPath integration design, case flow architecture, submission narrative |
| **Backend agent dev #1** | TBD | Maestro case definition + agent adapters |
| **Backend agent dev #2** | TBD | PARALLAX API service + UiPath API Workflow integration |
| **RPA engineer** | TBD | UiPath RPA workflows for legacy system integration (mocked bank core) |
| **UiPath platform engineer** | TBD | Automation Cloud deployment, Action Center setup, UiPath for Coding Agents usage |
| **Frontend / demo** | TBD | Synthetic case scenario, demo video, architecture diagram, submission packaging |

---

## 8. Synthetic demo case scenario

**Case ID:** `CASE-UI-2026-00077`
**Customer complaint (synthetic):**
> "₹2.1L transferred to unknown account after installing 'HDFC KYC Update' APK from SMS link. Bank says I authorized it. I did not."

**Pre-analyzed mock data:**
- Synthetic customer profile in mocked bank core (UiPath RPA can query)
- Synthetic transaction trail (3 transfers, ₹2.1L total)
- Synthetic APK hash (benign, pre-analyzed by PARALLAX)
- Mock SIEM data for IOC correlation (could integrate with Splunk if that hackathon also pursued)
- Mock mule account database

**Demo flow (target: 3-5 minutes):**
1. Customer complaint enters UiPath Action Center form (10s)
2. Maestro opens new case, RPA pulls customer KYC + transaction history from bank core (15s)
3. PARALLAX Triage Agent scores urgency → high-priority track (10s)
4. PARALLAX Static Analysis runs via UiPath API Workflow → returns class roles, IOCs (20s)
5. PARALLAX Dynamic Analysis runs in parallel with Visual Phishing (15s)
6. PARALLAX Mule Graph finds beneficiary overlap with prior cases (10s)
7. Evidence Validator challenges Device Agent's confidence (10s)
8. Device Agent responds with timeline + SMS receiver evidence (10s)
9. Maestro routes to Action Center for human officer approval (10s)
10. Officer approves with modification (hold, don't freeze yet) (10s)
11. Maestro orchestrates: RPA dispatches freeze to bank core, IOC package to SIEM, complaint draft to legal (15s)
12. Audit log entries synced to UiPath audit (5s)
13. Architecture diagram: PARALLAX + UiPath Maestro + RPA + Action Center + bank core (15s)

Total: ~3 minutes. Every Maestro capability visible: case state machine, conditional stages, parallel tracks, human-in-loop, RPA integration, audit.

---

## 9. Win strategy

### Why we'd podium
1. **Track 1 fit is undeniable** — exception-heavy, case management, agent handoffs, human-in-loop is PARALLAX-CASE exactly
2. **8+ PARALLAX agents orchestrated by Maestro** — depth of integration obvious
3. **Cross-framework story** — Pydantic AI + LangGraph + Custom + RPA + Agent Builder. UiPath explicitly encourages this
4. **RPA fills a real PARALLAX gap** — legacy banking system integration. Most AI fraud products don't do this. PARALLAX on UiPath does
5. **UiPath Marketplace distribution** — judges reward real distribution potential. PARALLAX on UiPath Marketplace = real international leverage
6. **UiPath for Coding Agents bonus** — meta-build, shows the team gets the future

### Risks
- UiPath learning curve is real — Maestro, Agent Builder, RPA, Action Center are new platforms
- Demo must show real UiPath Automation Cloud deployment, not local
- Track 1 competition may be moderate to high

### Bonus prize strategy
- **UiPath for Coding Agents bonus** — use Claude Code or Codex to generate real code, show it in the demo video

---

## 10. Build order (only after main PARALLAX is complete)

| Phase | Duration | Deliverable |
|---|---|---|
| Phase 1: UiPath platform ramp | 3-4 days | Team trained on Maestro, Agent Builder, RPA, Action Center, Automation Cloud |
| Phase 2: Maestro case definition | 3-4 days | PARALLAX case flow exported as valid UiPath Maestro case JSON |
| Phase 3: Agent adapters | 4-5 days | Each PARALLAX agent callable from UiPath API Workflow |
| Phase 4: RPA workflows | 3-4 days | Mocked bank core + SIEM + legal system integration via UiPath RPA |
| Phase 5: Action Center integration | 2-3 days | Human officer approval flow with PARALLAX evidence display |
| Phase 6: UiPath for Coding Agents usage | 2-3 days | At least one part of the solution built with Claude Code/Codex/Cursor, documented in demo |
| Phase 7: Synthetic case + demo | 3-4 days | Synthetic case scenario, end-to-end run-through, demo video |
| Phase 8: Deployment + submission | 2-3 days | Automation Cloud deployment, submission packaging, architecture diagram |
| **Total** | **~5 weeks** (fits in 7-week hackathon window) | **Submission ready** |

---

## 11. Resume point for future sessions

When you return to plan this in depth, start by reading:
1. This file (submission framing + decisions)
2. `C:\Users\arjun\Desktop\PSBs\01_IDEATION.md` (PARALLAX core design)
3. `C:\Users\arjun\Desktop\PSBs\02_ARCHITECTURE.md` (5-layer system)
4. `C:\Users\arjun\Desktop\Band-of-agents\Band-of-agents.md` (Band of Agents plan for cross-reference)
5. UiPath Maestro documentation (https://docs.uipath.com/)
6. UiPath for Coding Agents docs (TBD when published)
7. PARALLAX v2 modules in `C:\Users\arjun\Desktop\parallax_repo\src\parallax\models\v2\`

---

## 12. Open questions to resolve at kickoff

1. UiPath for Coding Agents docs and access — verify Claude Code / Codex / Cursor / Gemini CLI support in current UiPath version
2. UiPath Automation Cloud free tier limits for hackathon — confirm 7-week sustained deployment is possible
3. UiPath Agent Builder's external agent integration story — verify PARALLAX Python agents can be invoked from UiPath
4. UiPath Action Center integration with custom evidence display — can we render PARALLAX's 10-stage Fraud Attack Chain inside Action Center, or do we need a custom UI?
5. UiPath Marketplace submission process and timing — verify we can publish PARALLAX as a UiPath Marketplace agent
6. Per-team member licensing for Automation Cloud during hackathon

---

## 13. Final verdict snapshot

| Dimension | Verdict |
|---|---|
| PARALLAX fit | ★★★★★ — Track 1 is our track, exception-heavy case mgmt is PARALLAX-CASE |
| Tech integration | ★★★★★ — Maestro = case orchestration, RPA = legacy integration, Marketplace = distribution |
| Win chance | ★★★★☆ — Track 1 competition moderate; PARALLAX + RPA + cross-framework is strong |
| Build cost | ★★★☆☆ — UiPath learning curve is real; ~5 weeks for productive submission |
| International leverage | ★★★★★ — UiPath at every major bank; Marketplace = instant distribution |
| Credits/support | ★★★★☆ — UiPath Labs with agentic + AI units is real compute |
| Bonus prize potential | ★★★★☆ — UiPath for Coding Agents bonus reachable with meta-build approach |

**Confirmed: GO on Track 1, PARALLAX-CASE on UiPath Maestro.**

**Build order across all GOs:**
1. Band of Agents (first — 3 weeks, simplest architecture change)
2. UiPath AgentHack (second — 5 weeks, biggest learning curve)
3. Splunk Agentic Ops (third, conditional — ~3-4 weeks if pursued)
