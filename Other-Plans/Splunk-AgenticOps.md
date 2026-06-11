# Splunk Agentic Ops Hackathon — PARALLAX-SIEM Submission Plan

> **Status:** Conditional go-decision (after Band of Agents, after UiPath). Security track. Building only after main PARALLAX is complete — this file is the resume point for future planning sessions.
>
> **The condition:** Splunk judges will demand Splunk as a first-class part of the architecture, not a data sink. If we can't credibly show that, downgrade to skip.

---

## 1. Hackathon decoded — what they actually want

### Stated criteria (verbatim priorities)
- **Build innovative AI-powered solutions that enhance how teams monitor systems, secure environments, or build on the Splunk platform**
- **Use one or more of Splunk's latest AI capabilities** — Python SDK AI, Splunk MCP Server, AI Assistant, AI Toolkit, Splunk Hosted Models
- $20K cash + .conf26 passes
- 3 tracks: Observability, Security, Platform & Developer Experience

### The implicit bar (what actually wins)
- Splunk judges are Splunk admins, security engineers, and SOC operators
- They reward: real Splunk-platform depth, working Splunk apps, integrations that feed Splunk meaningfully, use of Splunk-specific features (SPL, dashboards, alerts, MCP server, AI Toolkit)
- They punish: surface-level integrations where Splunk is just storage, not a real architectural component
- Bonus: solutions that **leverage Splunk's specific AI capabilities** (MCP server is the headline new one)

### Tracks
| Track | Domain | Fit for PARALLAX |
|---|---|---|
| Observability | Engineering system behavior, anomaly detection, automated operational response | Misfit — PARALLAX is fraud/malware, not system observability |
| **Security** | **Threat detection, incident investigation, security workflow automation** | **Direct match — fraud + threat detection** |
| Platform & DevEx | Developer experience, workflow automation, app development | Partial — could frame as "developer experience for fraud analysts" but stretchy |

**Security track chosen.**

---

## 2. The submission: PARALLAX-SIEM on Splunk

### One-line pitch
PARALLAX-SIEM: PARALLAX ingests APKs, produces fraud detections and IOCs, and emits them as Splunk events. Splunk's MCP server lets PARALLAX agents query the bank's full operational telemetry (network logs, EDR alerts, transaction logs, prior SIEM data) for cross-system correlation. AI agents built via Python SDK for Splunk apps do the investigation in-band, with Foundation-Sec-1.1-8B handling security-specific reasoning. Result: a fraud case timeline enriched with evidence from across the bank's entire security estate.

### Why this passes the "PARALLAX is the center" bar
PARALLAX is the AI brain for APK analysis. Splunk is the operational data backbone. The relationship is honest: PARALLAX produces detections → Splunk indexes and correlates → agents query Splunk via MCP for cross-system context → PARALLAX analysis is enriched with full bank telemetry.

**Three real production gaps PARALLAX fills via Splunk:**

1. **SIEM integration** — banks already run Splunk as their SIEM. PARALLAX emitting events to Splunk = no new dashboards for fraud analysts to learn, fits existing SOC workflow
2. **Cross-system correlation** — fraud cases need: PARALLAX APK analysis + bank transaction logs + telecom logs + EDR alerts + network logs. Splunk is the natural place to correlate all of it
3. **Hosted cybersecurity LLM** — Foundation-Sec-1.1-8B is a security-specialized LLM hosted by Splunk. PARALLAX could use it as one of its specialized models for security reasoning. Free, no GPU cost, no model hosting overhead

### What's in the submission
- **PARALLAX AI agents** (the engine) — unchanged
- **PARALLAX → Splunk event emitter** — structured Splunk events with PARALLAX's detection data
- **Splunk MCP server** — PARALLAX agents query Splunk via MCP for cross-system evidence
- **Python SDK for Splunk app** — agentic workflows inside Splunk that orchestrate PARALLAX queries and Splunk searches
- **Foundation-Sec-1.1-8B hosted model** — security-specialized reasoning
- **Splunk dashboards** — fraud case timeline enriched with cross-system evidence
- **AI Assistant for SPL** — natural language query interface for fraud analysts

---

## 3. The Splunk architectural integration

### Layer 1: PARALLAX → Splunk event emission
- PARALLAX emits structured events to Splunk via HTTP Event Collector (HEC) or Splunk SDK
- Event types:
  - `parallax:apk:analyzed` — APK submission + analysis complete with class roles, method intents, IOCs
  - `parallax:fraud:case:opened` — new fraud case created
  - `parallax:fraud:hypothesis` — hypothesis from Hypothesis Engine with confidence + evidence
  - `parallax:fraud:ioc:matched` — IOC match against known pattern memory
  - `parallax:fraud:case:closed` — case closed with action packet
  - `parallax:fraud:action:dispatched` — freeze / blocklist / cyber-cell complaint
- All events indexed in Splunk, searchable via SPL, dashboarded, alerted

### Layer 2: Splunk MCP server for cross-system correlation
- MCP server exposes Splunk data to PARALLAX agents
- PARALLAX agents use MCP to ask:
  - "Have you seen this C2 domain in any of the bank's network logs in the last 90 days?"
  - "How many transactions from this account have crossed the fraud threshold?"
  - "Are there EDR alerts on the customer's device?"
  - "Show all prior cases with this APK's certificate fingerprint"
- Result: PARALLAX's fraud case is enriched with cross-system evidence that lives in Splunk

### Layer 3: Python SDK agentic app inside Splunk
- Build a Splunk app using Python SDK AI that:
  - Monitors for `parallax:fraud:case:opened` events
  - Triggers PARALLAX agents to run analysis (via PARALLAX API)
  - Stores PARALLAX results back in Splunk index
  - Builds correlation searches combining PARALLAX events with bank's other logs
  - Generates Splunk alerts when fraud patterns match across systems
  - Updates Splunk dashboards with live case status

### Layer 4: Foundation-Sec-1.1-8B hosted model
- Splunk-hosted cybersecurity LLM
- PARALLAX uses it for:
  - Security-specific reasoning in Decision Convenor agent
  - IOC interpretation
  - Threat actor attribution
  - MITRE ATT&CK technique mapping
- Free, hosted, no GPU cost — production deployment advantage for banks

### Layer 5: AI Assistant for SPL
- Natural language → SPL queries
- Embed in PARALLAX-CASE for fraud analysts
- "Show me all cases with SBI YONO brand impersonation in the last 30 days" → SPL query
- Removes SPL learning curve for fraud analysts

---

## 4. The agent map — PARALLAX + Splunk

| PARALLAX agent | Splunk integration | What it does |
|---|---|---|
| Intake Agent | Splunk lookup of customer KYC + transaction history via MCP | Enriches case with customer context |
| Triage Agent | Splunk risk scoring index lookup | Cross-references historical fraud patterns |
| Static Analysis Agent | Emits `parallax:apk:analyzed` event with class roles + IOCs | PARALLAX output becomes Splunk-indexed intelligence |
| Dynamic Analysis Agent | Emits `parallax:fraud:hypothesis` events with confidence + evidence | Hypotheses are searchable + alertable in Splunk |
| Visual Phishing Agent | Emits `parallax:fraud:ioc:matched` with brand impersonation evidence | Brand impersonation patterns trigger Splunk alerts |
| Mule Graph Agent | MCP query to Splunk for account history across all bank systems | Cross-system mule detection |
| Pattern Memory Agent | Splunk lookup against IOC database + threat intel feeds | Cross-references with known fraud patterns |
| Hypothesis Engine | All hypotheses emitted as events, queryable via SPL | Auditable hypothesis chain |
| Evidence Validator | Splunk audit log integration | Evidence chain is auditable in Splunk |
| Decision Convenor Agent | Foundation-Sec reasoning + Splunk risk index | Synthesizes all evidence with security-specialized LLM |
| Brand Impersonation Engine | Splunk dashboard for brand impersonation trends | Real-time brand impersonation intelligence |
| Risk Calibration Agent | Splunk lookup of historical labels for calibration | Calibrated risk scoring using bank's own data |

---

## 5. Why Splunk judges will reward this

1. **Real Splunk-platform depth** — not a wrapper. PARALLAX events flow into Splunk, Splunk MCP server powers PARALLAX correlation, Python SDK app orchestrates the workflow, Foundation-Sec is integrated as a model, AI Assistant is embedded. Five different Splunk capabilities used authentically.

2. **Cross-system correlation story** — Splunk's strength. PARALLAX analysis is enriched with network logs, EDR alerts, transaction logs, prior SIEM data. This is exactly the SOC workflow Splunk is built for.

3. **Foundation-Sec-1.1-8B** — Splunk's own hosted cybersecurity LLM. Using it for security reasoning in PARALLAX shows the team understands Splunk's specific AI capabilities.

4. **MCP server** — Splunk's headline new capability. Building a real integration around it signals the team is on the cutting edge.

5. **SIEM + fraud** is a high-value use case. Banks with Splunk SIEMs are exactly the customers for PARALLAX. The product fit is real.

6. **Cross-system evidence chain** — judges will see: PARALLAX detects → Splunk correlates with network logs → MCP surfaces prior sightings → Python SDK app builds timeline → AI Assistant lets analyst query → Foundation-Sec reasons about the full picture. That's a complete story.

---

## 6. What stays untouched vs what's new

### Stays untouched (PARALLAX core)
- All v2 modules
- Local Ollama models
- Neo4j TAIG
- RE tools
- Python agent frameworks

### New components
1. **`parallax/integrations/splunk/`** — adapter package
   - `event_emitter.py` — emits PARALLAX events to Splunk HEC
   - `mcp_client.py` — Splunk MCP server client for cross-system queries
   - `foundation_sec.py` — Foundation-Sec-1.1-8B model adapter
   - `audit_sync.py` — syncs PARALLAX audit log with Splunk audit
2. **Splunk app: PARALLAX-SIEM** — Python SDK app
   - Monitors PARALLAX events
   - Runs correlation searches
   - Generates dashboards
   - Triggers alerts
   - Embeds AI Assistant for SPL
3. **Splunk dashboards** — fraud case timeline, IOC trends, brand impersonation map, mule cluster visualization
4. **Splunk correlation searches** — pre-built searches combining PARALLAX events with bank telemetry
5. **One synthetic demo case** — pre-analyzed synthetic APK + mock bank SIEM data
6. **Demo video** showing PARALLAX + Splunk integrated workflow

### Why the engine is untouched
Splunk is the operational data backbone and correlation layer. PARALLAX remains self-contained. Splunk becomes one of multiple deployment options.

---

## 7. Team of 6 — role allocation

| Role | Person | Responsibilities |
|---|---|---|
| **Lead architect** | (you) | PARALLAX-Splunk integration design, MCP protocol usage, submission narrative |
| **Backend agent dev #1** | TBD | PARALLAX event emitter + MCP client + Foundation-Sec integration |
| **Backend agent dev #2** | TBD | Python SDK Splunk app development |
| **Splunk platform engineer** | TBD | Splunk deployment, dashboards, correlation searches, AI Assistant setup |
| **Data engineer** | TBD | Mock bank SIEM data + sample telemetry for demo |
| **Frontend / demo** | TBD | Synthetic case scenario, demo video, architecture diagram, submission packaging |

---

## 8. Synthetic demo case scenario

**Case ID:** `CASE-SPLUNK-2026-00099`
**Customer complaint (synthetic):**
> "₹5.2L transferred in 8 minutes. Phone now shows accessibility service app I never installed. Please help."

**Pre-analyzed mock data:**
- Synthetic customer profile + transaction history (mocked bank data in Splunk index)
- Synthetic network logs (mocked bank's Splunk ingestion)
- Synthetic APK hash (benign, pre-analyzed by PARALLAX)
- Mock EDR alerts (one anomaly on customer's device)
- Mock prior fraud cases in Splunk with overlapping mule account

**Demo flow (target: 3-5 minutes):**
1. PARALLAX analyzes uploaded APK (offline) — class roles, IOCs detected (15s)
2. PARALLAX emits `parallax:apk:analyzed` event to Splunk via HEC (5s)
3. Splunk app detects event, creates fraud case in Splunk (5s)
4. PARALLAX Mule Graph Agent queries Splunk MCP for "all accounts with transactions in last 8 min from this customer" (15s)
5. Splunk returns: 7 transactions, 3 beneficiaries. 2 beneficiaries appear in 4 prior cases (5s)
6. PARALLAX Hypothesis Engine emits hypotheses as Splunk events (10s)
7. Splunk correlation search fires: "PARALLAX hypothesis + network log anomaly + EDR alert" → auto-creates alert (10s)
8. Foundation-Sec-1.1-8B reasons over the full case: timeline + IOCs + cross-system evidence (15s)
9. Splunk dashboard shows case timeline with all evidence (10s)
10. Fraud analyst uses AI Assistant for SPL: "show all cases with this APK's certificate fingerprint" (10s)
11. Decision Convenor Agent issues final action packet (10s)
12. Architecture diagram: PARALLAX + Splunk + MCP + Foundation-Sec + AI Assistant (15s)

Total: ~3 minutes. Every Splunk capability visible: event ingestion, MCP server, Python SDK app, Foundation-Sec, AI Assistant, dashboards, correlation searches, alerts.

---

## 9. Win strategy

### Why we'd podium
1. **Real Splunk-platform depth** — five different Splunk AI capabilities used authentically
2. **Cross-system correlation** — Splunk's strength, executed well
3. **Foundation-Sec hosted model** — uses Splunk's specific AI capability, signals platform understanding
4. **MCP server integration** — cutting-edge, signals forward thinking
5. **Direct security use case fit** — banks run Splunk, banks need fraud detection, this is a real product story
6. **SIEM + fraud** is a real buyer pain point

### Risks (the conditional)
- Splunk judges will scrutinize whether Splunk is genuinely integrated or a data sink. If the submission is "PARALLAX analyzes APKs, sends JSON to Splunk, end," we lose
- Splunk's MCP server is new — API stability and feature completeness TBD
- Python SDK AI has a learning curve
- Foundation-Sec model may have usage limits

### What triggers downgrade to skip
- If MCP server is too unstable or immature for production-grade demo
- If team can't credibly learn Splunk Python SDK in 2-3 weeks
- If Foundation-Sec hosted model has blocking limitations

---

## 10. Build order (only after main PARALLAX is complete)

| Phase | Duration | Deliverable |
|---|---|---|
| Phase 1: Splunk platform ramp | 3-4 days | Team trained on Splunk AI capabilities, Python SDK, MCP server |
| Phase 2: Event emitter + MCP client | 4-5 days | PARALLAX → Splunk HEC, PARALLAX → MCP queries working |
| Phase 3: Python SDK Splunk app | 5-6 days | Splunk app with monitoring, correlation searches, dashboards, alerts |
| Phase 4: Foundation-Sec integration | 2-3 days | Security-specialized reasoning integrated into Decision Convenor |
| Phase 5: AI Assistant + dashboards | 2-3 days | AI Assistant for SPL embedded, dashboards polished |
| Phase 6: Synthetic case + demo | 3-4 days | Synthetic case scenario, end-to-end run-through, demo video |
| Phase 7: Submission packaging | 1-2 days | Submission text, architecture diagram, video upload |
| **Total** | **~3-4 weeks** | **Submission ready** |

---

## 11. Resume point for future sessions

When you return to plan this in depth, start by reading:
1. This file (submission framing + decisions)
2. `C:\Users\arjun\Desktop\PSBs\01_IDEATION.md` (PARALLAX core design)
3. `C:\Users\arjun\Desktop\PSBs\02_ARCHITECTURE.md` (5-layer system)
4. `C:\Users\arjun\Desktop\Band-of-agents\Band-of-agents.md` (Band of Agents plan for cross-reference)
5. `C:\Users\arjun\Desktop\Band-of-agents\UiPath-AgentHack.md` (UiPath plan for cross-reference)
6. Splunk AI documentation (https://help.splunk.com/en/splunk-ai)
7. Splunk MCP server docs (https://help.splunk.com/en/splunk-ai/mcp-server-for-splunk-platform)
8. PARALLAX v2 modules in `C:\Users\arjun\Desktop\parallax_repo\src\parallax\models\v2\`

---

## 12. Open questions to resolve at hackathon kickoff

1. **Splunk MCP server API stability and feature completeness** — is it production-grade for a hackathon demo, or experimental?
2. **Foundation-Sec-1.1-8B usage limits** — verify credit/token limits accommodate full demo flow
3. **Python SDK AI maturity** — is it stable enough to build a full app on, or still rough?
4. **Splunk Cloud free trial limits for hackathon** — confirm full deployment is possible for 6-month developer license period
5. **Splunk Marketplace submission process** — verify we can publish PARALLAX-SIEM as a Splunkbase app
6. **AI Assistant for SPL availability** — confirm it's generally available and not gated
7. **MCP server authentication options** — token-based vs OAuth (OAuth is in controlled availability per docs)

---

## 13. Final verdict snapshot

| Dimension | Verdict |
|---|---|
| PARALLAX fit | ★★★★☆ — Security track is direct, SIEM integration is real |
| Tech integration | ★★★★★ — Splunk fills 3 production gaps (SIEM, cross-system, hosted security LLM) |
| Win chance | ★★★☆☆ — Splunk judges demand platform depth; must execute well |
| Build cost | ★★★☆☆ — Splunk learning curve ~1-2 weeks; total ~3-4 weeks |
| International leverage | ★★★★★ — Splunk is global SIEM standard; banks worldwide use it |
| Credits/support | ★★★★☆ — 6-month developer license + hosted models = real runway |
| Bonus prize potential | ★★★☆☆ — Bonus points for AI capabilities used; reachable |

**Conditional GO on Security track, PARALLAX-SIEM on Splunk.**

**Trigger for downgrade to skip:**
- MCP server too unstable for demo
- Python SDK AI too immature
- Foundation-Sec has blocking limits
- Team can't credibly ramp on Splunk in 2-3 weeks

**Build order across all GOs:**
1. Band of Agents (first — 3 weeks, simplest architecture change)
2. UiPath AgentHack (second — 5 weeks, biggest learning curve)
3. Splunk Agentic Ops (third, conditional — ~3-4 weeks if pursued)
