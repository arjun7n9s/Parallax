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

---

## Session 2026-06-14 (cont.) — Dynamic evidence CLOSED: real-malware observation in the DB

**Verification gate MET.** One frida observation from a real Cerberus sample landed in the
database, end-to-end through the dynamic stage:
```
verdict HIGH / 65.0   launch_strategy: accessibility_wake   frida_error: None
OBSERVATIONS IN DB: 1
  frida | parallax.instrumentation_loaded | t=1781461268752 | {package: com.hmxuxgdngpi.bkqrlzkuwzuj}
```

### How it was solved (icon-hiding malware launch)
Cerberus has **no LAUNCHER activity** (hidden icon) and no resolvable activities; its surface
is an AccessibilityService + NotificationListenerService. So `frida.spawn([pkg])` fails with
`unable to find a front-door activity`. New **`parallax/sandbox/launcher.py`** runs a fallback
chain: `spawn → am start → accessibility-wake → notification-wake → monkey`, returns the pid +
whether it was spawned. For the attach paths the runner **`attach(pid)` and does NOT resume**
(spawn is the only path that resumes). Verified live: enabling the accessibility service via
`settings put secure enabled_accessibility_services` started Cerberus (pid), frida attached,
`Java.perform` fired. `frida_runner` refactored to use it; `sandbox/runner` passes the AVD
shell; the dynamic worker records `launch_strategy` + `frida_error` on the submission.

### Two real bugs found and fixed along the way
1. **`pidof` exit-1 crashed the launch chain.** adb wrappers raise on `pidof`'s non-zero exit
   ("not running"); `_pid_of` now treats that as "no pid yet" and keeps polling. Regression test.
2. **`observations.captured_at_ms` was a 32-bit Integer.** Epoch-ms (`Date.now()` ~1.7e12)
   overflowed it → the observation insert threw → **the entire dynamic transaction rolled back,
   silently losing every observation** (same class as the JSONB bug). Widened to **BigInteger**
   (migration `0006_captured_at_bigint`). This would have bitten the moment *any* real hook
   fired with an epoch-ms timestamp — the instrumentation beacon surfaced it.

### Instrumentation beacon (correct product behavior)
The script prelude now emits one `parallax.instrumentation_loaded` observation as soon as frida
attaches, so a run is **always provably instrumented** — "instrumented but the app was dormant"
is now distinguishable from "instrumentation never ran" (a real sample with 0 observations and
no beacon = the latter, a bug).

**144 unit tests pass** (11 new: launcher chain, order, accessibility-wake, raising-`pidof`,
clean-fail), mypy + ruff + format clean.

### Remaining dynamic follow-ups (not blockers; tracked)
- **Deep behavioral hooks** beyond the beacon: Cerberus overrides `onAccessibilityEvent` in an
  obfuscated subclass, so hooking the base `AccessibilityService` class doesn't intercept it.
  Need subclass-targeted hooks (from static class roles) to capture real malicious calls.
- **mitmproxy `Master.run` coroutine** still unawaited → network capture absent. (Phase 1 Task 1.1b.)

---

## Session 2026-06-16 — Phase 1 reliability core (Claude/ plan)

Continued the Claude/ build plan. Shipped the foundational, fully-unit-tested
reliability pieces (no live-emulator dependency), each CI-green on `main`:

- **Task 1.5 — typed error hierarchy** (`core/errors.py`): `ParallaxError` tree
  (Transient/Permanent/Stage; Infra/LLM and Data/LLMBadOutput leaves) + `is_retryable`,
  so workers decide retry vs fail vs continue-degraded from the exception type.
- **Task 1.6 — circuit breaker** (`core/circuit_breaker.py`): CLOSED/OPEN/HALF_OPEN,
  injectable clock. Wired into the LLM provider: each backend (ollama, aiml gateway)
  runs under a per-backend breaker; failures normalize to `LLMError`, an open circuit
  fails fast with `CircuitOpenError`, and `complete_json` raises `LLMBadOutputError`
  on unparseable output.
- **Task 1.4 — stage idempotency** (`workers/idempotency.py`): dynamic and reasoning
  workers skip when the submission already advanced past their stage, so Celery
  at-least-once redelivery never re-instruments or re-runs the cortex. Submit-time
  sha256 dedup already collapses repeated submissions.

New tests: `test_reliability.py` (errors + breaker + LLM boundary), `test_idempotency.py`
(stage-guard truth table + redelivery skips). Also made the dynamic-worker unit tests
**hermetic**: an autouse fixture forces `DYNAMIC_LIVE_DEVICE` off and stubs the reasoning
`.delay()`, so they never touch a real emulator or Redis regardless of the ambient `.env`
(this was a real local hang once services + the live-run flag were present; CI was always
green because it has neither). Full unit suite green, mypy + ruff + format clean.

- **Task 1.3 (core) — worker resilience** (`workers/mixins.py`): a `RetryableTask` base
  (autoretry_for=(TransientError,), exponential backoff + jitter, max_retries=3, acks_late,
  dead-letter logging on exhaustion). All five pipeline workers inherit it; the four pipeline
  workers now re-raise `TransientError` so Celery retries infra/LLM/circuit-open failures,
  while permanent and unknown failures still mark the submission failed. Combined with the
  stage idempotency guard, acks_late re-delivery is safe.

This completes the failure-recovery loop: typed errors (1.5) -> circuit breaker (1.6) ->
retry-transient / fail-permanent (1.3) -> idempotent re-delivery (1.4). All CI-green on `main`.

Commits on `main` (authored as arjun7n9s): `feat(core)`, `feat(llm)`, `test(reliability)`,
`feat(workers)` idempotency, `feat(workers)` RetryableTask, `test(workers)`.

### Remaining Phase 1: 1.3 heartbeat + orphan-reaper (needs live Redis + beat), 1.7 degradation
### matrix breadth, 1.8 observability (pure code); 1.1b mitmproxy capture + 1.2 emulator pool
### (need the live emulator up to verify).

### Next after this session

1. Pull a real labeled banking trojan from MalwareBazaar into `samples/`
2. Full end-to-end run (submit → triage → static → dynamic → cortex → delivery) with cloud routing — the final unproven milestone
3. Then: frontend UI → calibration Layer B (per agreed scope; DSPy deferred)

---

## Session 2026-06-17 — Observability core (Task 1.8, the code half)

Built the parts of 1.8 that don't need live infra, in three clean checkpoints.

- **Prometheus metrics** (`core/metrics.py`): decision-driving series, not vanity counters —
  `parallax_llm_call_duration_seconds{role,provider}`, `parallax_llm_tokens_total{role,direction}`,
  `parallax_analysis_verdict_total{verdict}`, and `parallax_stage_failure_total{stage,error_class}`
  (the last keyed off the typed error hierarchy from 1.5). All recording goes through no-op-safe
  helpers so call sites never guard. Added an unauthenticated `/metrics` endpoint on the API —
  the bundled `prometheus.yml` already scrapes `:8000/metrics`, so the target now exists.
- **Wiring**: every LLM call now flows through one timed `_generate()` entry point in `llm.py`
  that records per-role latency and **real** token usage threaded out of each backend (Ollama
  `prompt_eval_count`/`eval_count`; OpenAI/Anthropic/gateway `usage` blocks). The reasoning worker
  records the final verdict; all four pipeline workers record stage failures by error class on
  their failure branch.
- **Structured logging** (`core/logging.py`): renders colored console for an interactive TTY and
  JSON everywhere else (`LOG_FORMAT=auto|json|console`), so the same build ships to Loki/ELK with
  no change. Added `bind_log_context`/`clear_log_context` (structlog contextvars + a
  `merge_contextvars` processor): each worker binds `submission_id` + `stage` at entry and clears
  on exit, so every log line for one analysis is correlated without threading ids through call
  signatures.

New tests: `test_metrics.py` (helpers move the right series via `REGISTRY.get_sample_value`;
`/metrics` served through `TestClient`) and `test_logging.py` (format selection + bound context
renders into the JSON event). Full unit suite green; mypy + ruff + format clean.

Commits on `productize-audit-fixes` (authored as arjun7n9s, no co-author trailer):
`feat(obs)` metrics core + endpoint, `feat(obs)` metric wiring, `feat(obs)` JSON logs + correlation.

### Remaining on 1.8 (needs live infra): OTel tracing across Celery, Grafana dashboards
### populating, and an Alertmanager rule firing. Tracked as 🟡 in the master tracker.

---

## Session 2026-06-17 (cont.) — Task 1.3 recovery half: heartbeat + orphan reaper

Closed the code half of worker self-healing (the `kill -9 → resume` story).

- **Heartbeat** (`workers/heartbeat.py`): a running stage refreshes `hb:{submission_id}`
  in Redis on a daemon thread (interval/TTL from settings); best-effort, so Redis being
  down degrades to a no-op and never breaks a stage. A `stage_context` decorator now unifies
  log-context binding **and** the heartbeat across all four pipeline workers, replacing the
  inline `bind_log_context`/`clear_log_context` added earlier — the worker bodies are cleaner
  and the teardown is guaranteed in one place.
- **Orphan reaper** (`workers/reaper.py`): a Celery-beat task (every 30s, configurable) that
  finds submissions still in a non-terminal status whose heartbeat expired **and** which
  haven't been touched within a grace window, then re-dispatches the worker for their current
  stage via a status→task `RESUME_DISPATCH` map. The stage idempotency guard makes restart
  safe, so resume never re-runs completed stages or duplicates LLM cost. If Redis is
  unreachable the whole run is skipped — a missed reap self-heals next tick, but a false reap
  would double-dispatch live work, so uncertainty always means "don't reap". Wired into the
  beat schedule + `include` list; new `parallax_orphan_reaped_total{stage}` metric.

Tests: `test_heartbeat.py` (helpers, refresher-thread refresh+clear, disabled no-op,
decorator binds/clears even on error) and `test_reaper.py` (resume map covers every
non-terminal status and excludes terminal; orphan selection truth table incl. live-heartbeat,
grace window, null/naive timestamps, and Redis-error propagation). Added an autouse conftest
fixture that disables the heartbeat in unit tests so none can touch real Redis. Full unit
suite green; mypy + ruff + bandit clean.

Commit on `main` (authored as arjun7n9s): `feat(workers)` heartbeat + orphan reaper.

### Remaining on 1.3: the live `kill -9 a worker mid-dynamic → re-queued and completes from
### the dynamic stage within ~60s` proof — needs live Redis + a running beat, deferred to a
### live session.

---

## Session 2026-06-18 — Phase 2 reconciliation (state audit, no new code)

Resumed from a stale summary and discovered `main` had already advanced ~14h with a full
Phase 2 build (and the 1.1b/1.1c dynamic fixes) layered on top of the reaper commit. Audited
every commit against its gate rather than rebuild. Each shipped code **plus** a dedicated test
file; the full unit suite is **247 passed**, mypy + ruff clean.

True state after audit:

- **2.4a confidence** (`cb8ddb3`) — ✅ `ai/confidence.py`: overall-confidence from coverage +
  agent self-confidence + dynamic-observed + attribution → band + `needs_human_review`; report
  surfaces it (test_confidence).
- **2.4b high-risk LLM debate** (`055b5c0`) — ✅ FOR/AGAINST/judge for high-risk claims, the
  deterministic evasion check as the fast-path trigger, cost-gated (test_debate_llm).
- **2.4c structured synthesis** (`55c7e57`) — ✅ `SynthesisOutput` (key_findings, evidence_table,
  risk_breakdown, attck, iocs, recommendations); report renders each section (test_synthesis,
  test_delivery).
- **2.6 pattern memory** (`34d5296`) — ✅ stable content-hash IDs (re-run → identical, dedupes),
  idiom + fraud-flow extractors, per-category tests (test_pattern_memory).
- **2.1 / 2.2 / 2.3 / 2.5** — 🟡 code+tests landed (`build_corpus.py`, `run_corpus.py`,
  `ai/calibration/` + `risk._calibrate`, `knowledge/graph_health.py`), but their gates need the
  live ≥200-sample corpus run: the accuracy table, a fitted isotonic model that beats identity,
  and cross-sample TAIG queries over loaded data. Deferred to a live-data session.

Note: a tree sync to HEAD during this session discarded an in-progress local re-implementation
of 2.4a (duplicate of `cb8ddb3`); nothing committed was lost. Tracker rows updated to match.

---

## Session 2026-06-18 (cont.) — Phase 3 backend: security controls + API hardening

Built the code-doable, no-live-DB parts of Phase 3.3 and 3.2 in tested checkpoints.

- **3.3 security controls** (`a7ea08f`): `LOCAL_ONLY` hard-disables all cloud LLM routing at
  the `provider_for` chokepoint (data residency for strict banks); `require_admin_key` gates
  `/admin` with a separate `X-Admin-Key` and **fails closed** if API_KEY is set but
  ADMIN_API_KEY isn't (a leaked analyst key can't escalate); a Redis fixed-window per-key
  rate limiter (`RATE_LIMIT_PER_HOUR`, 429, fails open, identity = hash of key not the secret)
  on submission endpoints; `redact_secrets()` scrubs configured key values from logs/errors
  (test_security_controls).
- **3.2c Idempotency-Key** (`72c0d6c`): `POST /analyze` honors the header — same key within
  24h returns the original submission, short-circuiting before upload/hashing. Redis nx + 24h
  TTL (first writer wins under a retry race), fails open with the sha256 unique index as
  backstop (test_idempotency_key).
- **3.2a per-submission webhooks** (`b9f2987`): optional `webhook_url` at submit (migration
  0007); delivery POSTs the signed result to it via a new `dispatch_to_url()` that reuses the
  HMAC signing + bounded-backoff retry path (refactored into `_build_request` +
  `_post_with_retries`) (test_webhooks).

Full unit suite green throughout; mypy + ruff + bandit clean.

### Remaining Phase 3 (the larger / gated pieces):
### - 3.3 tenancy (`tenant_id` + per-tenant query scoping) + AuditLog wiring — need a live DB.
### - 3.2b batch submit + 3.2d OpenAPI examples / generated SDKs.
### - 3.1 React frontend — a separate large stack; its E2E gate needs the full running system.
