# PARALLAX — Session Progress Log

> Running log of build work. Newest session at the top.
> Prior context: `BUILD_HANDOFF.md` (2026-06-12 checkpoint) and `Plan/04b_INTEGRATED_BUILD_ORDER.md` (operative plan).

---

## Session 2026-06-13 — Cloud LLM gateway (aimlapi) + model strategy

### Context at session start

All 6 phases of the operative plan are built, committed, and CI-green (81 unit tests, mypy, ruff). The one unproven thing: a **full end-to-end cortex run** — local 7B models on this CPU-only host time out on real decompiled-code prompts. The fix is cloud routing, for which the user provided:

- `AIML_API` — an [aimlapi.com](https://docs.aimlapi.com/) unified gateway key (OpenAI-compatible, 400+ models, one key)
- `MALWAREBAZAAR_API_KEY` — abuse.ch Auth-Key for pulling real labeled malware samples

### 1. Model strategy (cost-efficiency by design)

**Principle:** match each agent role's model to its actual difficulty and call volume. Opus-class models are unjustified everywhere in this pipeline — the two highest-value roles get Sonnet-class, everything else gets economy models, and embeddings never leave the box.

Per-APK call profile and assignments:

| Role | Calls/APK | Cloud model (aimlapi ID) | Local fallback | Rationale |
|---|---|---|---|---|
| triage | 1 small | `gpt-4o-mini` | `phi3:mini` | Tiny manifest prompt, strict JSON; speed matters |
| hypothesis | few, small | `gpt-4o-mini` | `phi3:mini` | Scratchpad updates, simple structure |
| hook_planner | 1–3 medium | `gpt-4o-mini` | `phi3:mini` | Output is grammar-validated + retried anyway; cheap model + validator beats expensive model |
| intel_correlator | 1 medium | `gpt-4o-mini` | `mistral:7b` | RAG retrieval does the heavy lifting; LLM just maps |
| debate | 1 small | `gpt-4o-mini` | `mistral:7b` | Contradiction logic is deterministic; LLM only narrates |
| behavior_analyst | 1 med-large | `google/gemini-2.5-flash` | `mistral:7b` | Long observation timelines → huge cheap context |
| evidence_validator | 1 medium | `google/gemini-2.5-flash` | `mistral:7b` | Careful filtering/rewriting, not deep reasoning |
| visual | 5–20 vision | `google/gemini-2.5-flash` | `llava:7b` | Highest call volume + needs vision → cheapest good vision model |
| dynamic_explorer | ≤20 vision | `google/gemini-2.5-flash` | `llava:7b` | Fast UI-driving loop, same reasoning |
| **code_interpreter / re_workbench** | 1 LARGE | **`anthropic/claude-sonnet-4.6`** | `qwen2.5-coder:7b` | **Crown jewel #1:** reads decompiled malware code; detection quality lives here |
| **synthesis** | 1 large | **`anthropic/claude-sonnet-4.6`** | `mistral:7b` | **Crown jewel #2:** the bank-facing verdict + report; the product's face |
| embedding | many | — (always local) | `nomic-embed-text` | Vector-space stability for TAIG — cloud routing must never shift embeddings |

**Estimated cost: ~$0.15–0.20 per APK** (Sonnet ~$0.14 across its 2 calls, flash ~$0.03, mini ~$0.01). An all-Opus pipeline would be ~15× more for marginal gain — the only roles where model quality is decision-critical get the premium tier.

### 2. Gateway wiring (`parallax/ai/llm.py` + config)

aimlapi facts (from https://docs.aimlapi.com/):
- Base URL `https://api.aimlapi.com/v1`, standard OpenAI SDK works as the client
- Bearer auth with the single key; model IDs like `gpt-4o-mini`, `anthropic/claude-sonnet-4.6`, `google/gemini-2.5-flash`
- Chat completions endpoint for all text models; vision via OpenAI `image_url` data-URI format

Changes:
- `core/config.py`: `AIML_API` (key), `AIML_BASE_URL` (default `https://api.aimlapi.com/v1`); `CLOUD_PROVIDER` now `aiml | anthropic | openai`
- `ai/llm.py`:
  - `ModelSpec` gains `cloud_model` (per-role gateway model ID); `cloud_capable` derived from it
  - New `aiml` provider path using `AsyncOpenAI(base_url=AIML_BASE_URL)` — lazily constructed
  - JSON mode on the gateway: **no** `response_format` param (not all 400+ models support it); instead instruct "single valid JSON object only" + tolerant `_extract_json` (already battle-tested)
  - Vision: base64 PNGs as `image_url` data URIs
  - `max_tokens=4096` explicit (gateway defaults can be low)
- `.env`: `LLM_MODE=auto`, `CLOUD_PROVIDER=aiml` — auto mode degrades to local Ollama seamlessly if the key is absent/exhausted, so the same config works everywhere
- `.env.example` updated to match (kept in parity)

### 3. Verification — ALL PASSED (2026-06-13)

- [x] **Routing unit tests** — new `tests/unit/test_llm_routing.py` (17 tests): roster tier contract (exactly the 3 premium role-slots, no Opus anywhere, embeddings never cloud), provider selection with key present/absent, local-mode override, native-anthropic path intact, gateway call shape (per-role model ID, `max_tokens=4096`, no `response_format`, JSON-by-instruction, data-URI images)
- [x] **Full unit suite green** (98 tests), mypy clean, ruff clean
- [x] **Live economy tier**: `triage` → gateway → `gpt-4o-mini` → valid JSON back
- [x] **Live premium tier**: `synthesis` → gateway → `anthropic/claude-sonnet-4.6` → valid JSON back
- [x] **Live vision**: `visual` → gateway → `google/gemini-2.5-flash` correctly described a generated test image
- [x] **Live MalwareBazaar**: authenticated `get_taginfo` query for SharkBot returned 3 samples (`query_status=ok`)

New ops tooling: **`parallax/scripts/smoke_cloud.py`** — one-command smoke-check of all gateway tiers + MalwareBazaar auth (never prints secrets). Run it any time keys/billing change.

### Files touched this session

| File | Change |
|---|---|
| `parallax/parallax/core/config.py` | `AIML_API` + `AIML_BASE_URL`; `CLOUD_PROVIDER` default `aiml`; native `ANTHROPIC_MODEL` default downgraded Opus→Sonnet (consistent with cost strategy) |
| `parallax/parallax/ai/llm.py` | `ModelSpec.cloud_model` (per-role gateway IDs), tiered ROSTER, `aiml` provider path via OpenAI SDK, client cleanup in `close()` |
| `parallax/.env` | `LLM_MODE=auto`, `CLOUD_PROVIDER=aiml` (keys were added by the user) |
| `parallax/.env.example` | Parity: documented `AIML_API`, `AIML_BASE_URL`, provider options |
| `parallax/tests/unit/test_llm_routing.py` | NEW — 17 routing/contract tests |
| `parallax/scripts/smoke_cloud.py` | NEW — live connectivity smoke-check |
| `progress.md` | NEW — this log |

---

## Session 2026-06-13 (cont.) — First live malware run + integration-bug fixes

Ran a **real Cerberus banking trojan** (MalwareBazaar `a52d2105…796a`, family=Cerberus/Alien) through the full pipeline via two new reusable scripts: `scripts/fetch_sample.py` (MalwareBazaar pull) and `scripts/run_pipeline.py` (in-process triage→static→reasoning→delivery driver). Dynamic stage skipped (no emulator → 0 observations).

**The run exposed real integration bugs that mocked unit tests never caught:**

1. **JSONB in-place mutation not persisted** (the big one). `static_worker` and `delivery_worker` did `meta = submission.metadata_json or {}; meta[k]=v; submission.metadata_json = meta` — reassigning the *same* dict reference, which SQLAlchemy does not flag dirty. Result: the RE-workbench artifact (package, permissions, decompiled-code pointer) was **silently dropped**, so the cortex analyzed empty input and returned CLEAN/7.6 on a real trojan. Fixed with `flag_modified(submission, "metadata_json")` in static, delivery, and reasoning workers.
2. **Triage/hook-planner bypassed the gateway** — `triage.py` still called `ollama_client` directly (Ollama down → triage failed). Migrated triage to `llm.complete_json("triage", …)` (→ gpt-4o-mini). Updated `test_triage.py`. (hook-planner + droidbot still on `ollama_client` — see gaps.)
3. **YARA rules path wrong** — runner looked in `parallax/rules/yara`; rules live at repo-root `rules/yara`. Added `YARA_RULES_DIR` config + robust `_resolve_rules_dir()` (repo-root or package).
4. **jadx path** — `JADX_BIN` must be absolute (jadx is at repo-root `tools/`, not `parallax/tools/`). Persisted absolute path in `.env`.

**Literal result after fixes (exit 0):**
- code_interpreter (cloud Sonnet): **intent=banking_trojan, risk=HIGH, conf=0.72** ✅ correctly identified
- aggregate verdict: **LOW, score 29.5/100** ❌ — under-scored (see gap A)
- ATT&CK (8): T1417, T1426, T1429, T1437, T1582, T1624.001, T1636.003, T1636.004
- risk components: code_intent_risk 0.75, permission_abuse 1.00, behavioral 0.20, network/brand/campaign/attribution 0.00
- family_attribution: None ❌ (gap B); IOC rows: 0; artifacts: 5 (report.pdf ~3pp, html, STIX, YARA rule, fraud_rules)

**Open gaps surfaced by the run:**
- **(A) Static-only runs structurally under-score.** 60% of evidence weight (behavioral .20 + network .15 + brand .15 + campaign .10) needs the dynamic/graph stages. With no emulator, even a confirmed banking_trojan caps ~30 → verdict LOW. Needs either a dynamic run or a risk-model adjustment so strong code-intent + known-family evidence can carry a verdict alone.
- **(B) Hash→family attribution not wired into reasoning.** `knowledge/ioc_matcher.py` (MalwareBazaar/VT) exists but the reasoning worker never calls it; wiring it would attribute "Cerberus" from the hash and populate attribution_confidence.
- **(C)** hook-planner generator + droidbot_gpt still call `ollama_client` directly (dynamic-only path) — migrate to gateway for consistency.
- **(D)** apkid's bundled `rules.yarc` is incompatible with installed yara-python (packer detection disabled); ssdeep binary absent. Both non-critical, degrade gracefully.

---

## Session 2026-06-13 (cont. 2) — Family attribution, scoring floor, gateway migration, emulator

### Corrected verdict on the real Cerberus sample (exit 0)
```
verdict            : HIGH      final_score : 65.0  (evidence 65.0, calibrated 65.0, ±5.0)
family_attribution : 'Cerberus' (confidence 0.9, source MalwareBazaar)
note               : Known-malware family 'Cerberus' confirmed by malwarebazaar (conf 0.9): floored 38.5 -> 65.0
components          : code_intent_risk 1.0, permission_abuse 1.0, attribution_confidence 0.9, behavioral 0.2, rest 0.0
attck_techniques(9) : T1417, T1426, T1429, T1437, T1606, T1616, T1624.001, T1636.003, T1636.004
artifacts(5)        : report.pdf (~4pp), report.html, bundle.stix.json, rule.yar, fraud_rules.json
```
The code-interpreter (cloud Sonnet) independently classified it `banking_trojan / HIGH / 0.72`. Verdict, family, and score are now all correct and auditable.

### Changes
1. **Family attribution wired into the cortex.** `orchestration.run_cortex` now calls `knowledge.ioc_matcher.match_iocs(sha256, domains, ips)` (MalwareBazaar/VT/internal-corpus), merges the result into `intel.family_attribution` / `family_confidence`. Error-isolated like every other agent.
2. **Known-family verdict floor (the scoring fix).** `risk.compute_risk` gained `known_family`. A confirmed known-malware family from external threat intel (confidence ≥ 0.8) sets a verdict floor of 65 (HIGH) — because external ground-truth that the hash IS a known malicious family must not be lowered just because the dynamic stage didn't run (60% of weight is dynamic). Recorded as an auditable `RiskScore.notes` entry. New tests in `test_productization.py`.
3. **Completed gateway migration.** `triage` (prior), plus `hook_planner` generator and `droidbot_gpt` now route through `ai.llm` roles instead of the legacy `ollama_client`. `api/main.py` shutdown closes `llm`. **Deleted the orphaned `ai/ollama_client.py`.** Updated `test_generator.py`, `test_dynamic_worker.py`, `test_droidbot.py`. **126 unit tests pass**, ruff + mypy (43 files) clean.

### Live emulator — BLOCKED by environment (task left open)
Booted the docker `android-emulator` container; it crash-loops because **`/dev/kvm` is absent** in this Docker/WSL2 setup (`docker run --device /dev/kvm` fails; no nested virtualization). The x86_64 Android emulator cannot start without KVM. This is a host limitation, not a code issue. **To enable the live dynamic run:** (a) enable nested virtualization + expose /dev/kvm to WSL2/Docker, or (b) attach a physical rooted Android device over adb, or (c) run dynamic analysis on a Linux host/VM with KVM. Then set `DYNAMIC_LIVE_DEVICE=true`. Until then the pipeline runs static→cortex→delivery and (for known samples) attributes family via threat intel.

### Known non-critical env limitations (documented, not fixed — would destabilize the stack)
- **apkid**: ships only a precompiled `rules.yarc` incompatible with installed yara-python 4.5.4; no raw `.yar` sources in the package to recompile. Fixing means downgrading yara-python, which would break the working YARA banking-rule engine. Degrades gracefully (obfuscation signal, 0.05 weight). Fix path: install apkid's raw rules from its repo and recompile, or pin a yara build matching the .yarc.
- **ssdeep**: no Windows binary; fuzzy-hash prefilter degrades gracefully.

---

## Session 2026-06-13 (cont. 3) — LIVE dynamic run on the emulator

**KVM unblocked** (user loaded `kvm`/`kvm_intel` in the docker-desktop WSL2 VM; modules don't auto-load across Docker restarts). Added **`scripts/start-emulator.sh`** — preflight `modprobe` via `wsl.exe -d docker-desktop`, `docker compose up android-emulator`, wait for `sys.boot_completed`. Emulator booted in ~35s, adb `localhost:5555 device`, frida-server running (pid in-container), ports 5555/27042 exposed.

Enabled `DYNAMIC_LIVE_DEVICE=true` + `ADB_BIN` in `.env`; extended `run_pipeline.py` to run the real dynamic worker (`_async_run_dynamic_pipeline`) and neutralize the downstream `.delay()` chaining.

**Dependency/path bugs fixed to get the dynamic stage to run (all real, none mock-caught):**
- **bcrypt 4.1+ broke passlib** → mitmproxy `proxyauth` import crashed (`module 'bcrypt' has no attribute '__about__'` → `ValueError: password cannot be longer than 72 bytes`). Pinned `bcrypt==4.0.1` in `requirements.txt`.
- **HookPlannerParser default path was one level too deep** (`parallax/parallax/parallax/analysis/...`). Fixed to `parents[2]` (package root). 25 API entries load.
- **Synthesis JSON truncated at 4096 tokens** (`Expecting ',' delimiter` → deterministic fallback). Bumped gateway `max_tokens` to 8192; test updated.

**Live dynamic result on Cerberus (exit 0, full pipeline incl. emulator):**
```
verdict HIGH / 65.0   family 'Cerberus' (0.9)   floor note: 41.5 -> 65.0
components: code_intent 1.0, perm_abuse 1.0, attribution 0.9, brand_impersonation 0.2 (NEW: dynamic), behavioral 0.2
attck(10): T1417, T1417.001, T1429, T1430, T1437, T1582, T1624.001, T1636.002/003/004
dynamic stage ran ~3.5 min; 9 screenshots captured + analysed by Visual agent
artifacts(5): report.pdf(~4pp), html, STIX, YARA, fraud_rules
```

**What the live dynamic stage did / didn't capture (honest):**
- ✅ Emulator boot, APK install, DroidBot UI exploration (~3.5 min), **9 screenshots** → Visual agent produced real signal (`brand_impersonation 0.2`, up from 0.0 static-only).
- ❌ **0 frida observations**: hooks didn't yield events. Likely Cerberus dormancy under random UI exploration (no SMS/accessibility/C2 triggers — textbook context-aware banking malware), and/or hook targeting/attach needs investigation. NEEDS DEBUG.
- ❌ **mitmproxy traffic capture failed**: `RuntimeWarning: coroutine 'Master.run' was never awaited` — the DumpMaster isn't driven correctly in its thread; also cross-container proxy routing (emulator-in-container → mitmproxy-on-host) is unverified. NEEDS FIX. (`network_exfiltration 0.0`.)

**Net:** full pipeline including the live emulator now runs end-to-end on real malware and yields a correct, auditable HIGH/Cerberus verdict with visual dynamic signal. Two dynamic-capture paths (frida events, mitm traffic) need a follow-up debugging pass to enrich behavioral/network evidence. 126 unit tests pass, ruff + mypy clean.

---

## Session 2026-06-14 — Dynamic-capture root cause (the "0 frida observations")

Treated dynamic capture as the #1 blocker. Fixed the *plumbing* before theorizing
about dormancy, and converted each bug into a regression test.

**Root cause was FOUR stacked bugs, not dormancy:**
1. **Wrong frida connection API.** `frida.get_device("localhost:27042")` raises
   `InvalidArgumentError` — it searches existing devices, it does not open a TCP
   connection. The reliable path is the adb-tunnelled device (`localhost:5555`).
   Fixed `frida_runner` to connect via the adb serial (config `FRIDA_DEVICE_ID`),
   plumbed from the AVD manager.
2. **Swallowed errors.** `SandboxRunner` used `asyncio.gather(return_exceptions=True)`
   and never inspected the result, so any frida failure vanished and read as
   "0 observations / dormant." Now surfaced on `sandbox.frida_error` + logged loudly.
3. **frida 17 dropped the bundled Java bridge.** Every `Java.perform` hook failed
   with `ReferenceError: 'Java' is not defined`. Pinned **frida==16.7.19** (client)
   and pushed a matching 16.x frida-server to the emulator. **Verified live: a
   `Java.perform` hook on com.android.settings produced 2 real observations.**
4. **Cerberus hides its launcher icon** (no `LAUNCHER` activity), so frida's
   spawn-by-launch fails with `unable to find a front-door activity`. Its
   components are an AccessibilityService + NotificationListenerService; its
   manifest MAIN activity name (`OzGUhRlf`) doesn't resolve via `am start`
   (obfuscated/aliased). **Open: launching icon-hiding, obfuscated malware needs
   an `am start`/attach (or component-trigger) strategy — task #16 continues.**

**Status:** frida plumbing PROVEN working (real observations on a real app);
3 of 4 bugs fixed with regression tests. The 4th (launching icon-hiding malware)
is a distinct dynamic-analysis problem, not a plumbing bug. The mitmproxy
`Master.run` coroutine warning (network capture) also remains.

**Regression tests added (the "would-have-caught-the-bug" set):**
`tests/unit/test_dynamic_capture.py` — frida default device is the adb serial not
`:27042`; `run_sync` calls `get_device` with the serial; sandbox records (not
swallows) a frida failure on `frida_error`; device_id flows from the AVD manager.
`test_static_worker.py` — asserts `flag_modified(submission, "metadata_json")` is
called (guards the JSONB-persistence fix; the old in-memory assertion passed while
the bug was live). **133 unit tests pass, mypy + ruff + format clean.**

Note: the emulator's container ships frida-server 17.x; a 16.x server must be
provisioned (pushed manually this session). `start-emulator.sh` should be extended
to push/start the 16.x server, or `install.py` updated to do so.

### Next after this session

1. Pull a real labeled banking trojan from MalwareBazaar into `samples/`
2. Full end-to-end run (submit → triage → static → dynamic → cortex → delivery) with cloud routing — the final unproven milestone
3. Then: frontend UI → calibration Layer B (per agreed scope; DSPy deferred)
