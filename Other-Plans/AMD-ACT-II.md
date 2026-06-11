# AMD Developer Hackathon: ACT II — PARALLAX on AMD Submission Plan

> **Status:** Confirmed go-decision (after main PARALLAX is complete). Track 1: AI Agents & Agentic Workflows. This file is the resume point for future planning sessions.
>
> **Core value proposition:** Validate AMD Instinct MI300X + ROCm as a permanent production deployment target for PARALLAX at banks with AMD-friendly infrastructure.

---

## 1. Hackathon decoded — what they actually want

### Stated criteria (verbatim priorities)
- **Build an application, agent, or developer tool that feels real, works end-to-end, and shows what AMD's compute stack can unlock**
- $100 in AMD Developer Cloud credits per member
- Access to AMD Instinct MI300X GPUs (192GB HBM3 — high memory bandwidth, data-center class)
- ROCm open-source GPU platform
- DeepLearning.AI Pro membership (1 month)
- AMD AI Academy access
- Expert access via community channels and office hours
- "No hardware, no complex setup — just access to powerful compute"

### The implicit bar (what actually wins)
- AMD judges are GPU-focused engineers and AI developers
- They reward: **production-grade workloads that actually push GPU utilization**, ROCm-native code (not just CUDA ported), real AMD-stack integration
- They punish: lightweight demos that don't actually need MI300X, code that runs on any GPU, surface-level AMD branding
- Bonus: **benchmarks comparing AMD performance to alternatives** (NVIDIA baseline), open-source contributions to ROCm, AMD-specific optimizations

### Tracks
| Track | Domain | Fit for PARALLAX |
|---|---|---|
| **Track 1** | **AI Agents & Agentic Workflows** — LangChain, CrewAI, AutoGen + open-source models (Llama, DeepSeek, Mistral, Qwen) | **Direct match — PARALLAX is a multi-agent system with these exact frameworks** |
| Track 2 | Fine-Tuning on AMD GPUs — ROCm, PyTorch, Hugging Face Optimum-AMD, vLLM | Real but heavier — fraud-specialized fine-tuned model as permanent PARALLAX capability |
| Track 3 | Vision & Multimodal AI — LLaVA, Qwen-VL on ROCm | Strong fit for PARALLAX's Brand Impersonation Engine |

**Track 1 chosen (AI Agents & Agentic Workflows).** Track 3 is a strong alternative if Brand Impersonation Engine is the strategic focus.

---

## 2. The submission: PARALLAX-AMD

### One-line pitch
PARALLAX-AMD: PARALLAX's multi-agent fraud investigation system running end-to-end on AMD Instinct MI300X + ROCm. Eight specialist agents (Triage, Static, Dynamic, Hypothesis, Mule Graph, Visual Phishing, Evidence Validator, Decision Convenor) collaborate to analyze APKs and produce Fraud Attack Chains, all inference and graph traversal on AMD hardware. Submission includes performance benchmarks comparing MI300X vs NVIDIA baselines for PARALLAX's specific workload.

### Why this passes the "PARALLAX is the center" bar
PARALLAX is the multi-agent system. AMD is the GPU stack. The relationship is honest: PARALLAX's existing agent architecture runs on AMD instead of NVIDIA. The submission's center is PARALLAX. AMD is the deployment substrate that proves the system works on AMD hardware.

**Three real production gaps PARALLAX fills via AMD:**

1. **Production deployment target** — banks with AMD-friendly infrastructure (Linux servers, ROCm-aware stacks) can deploy PARALLAX without buying NVIDIA. AMD MI300X with 192GB HBM3 is genuinely competitive with NVIDIA H100 for LLM inference workloads
2. **Validated ROCm support** — currently Ollama + AMD has rough edges. A hackathon submission that runs PARALLAX cleanly on MI300X + ROCm is a real production reference architecture
3. **Performance benchmark credibility** — banks evaluating GPU infrastructure need real-world performance data. PARALLAX-AMD's submission includes apples-to-apples MI300X vs H100/H200 benchmarks for the actual fraud-analysis workload

---

## 3. The PARALLAX workload on AMD

### What runs on MI300X
1. **LLM inference for all 8 agents** — Ollama running open-source models (DeepSeek-Coder-V2, Qwen2.5, Llama 3.3, Mistral, Phi-3) on ROCm
2. **Multimodal vision inference for Visual Phishing Agent** — LLaVA-OneVision or Qwen2.5-VL on ROCm
3. **Neo4j graph traversal** — TAIG queries for mule cluster detection (graph algorithms benefit from MI300X's high memory bandwidth)
4. **Embedding generation for Pattern Memory** — sentence-transformers on ROCm for code/string/IOC embeddings
5. **Frida analysis orchestration** — PARALLAX's RE workbench runs on the same AMD host, with MI300X accelerating any LLM-assisted hook planning

### What does NOT run on MI300X
- Static RE tools (Frida, MobSF, Ghidra, androguard) — CPU-bound, not GPU-accelerated
- YARA scanning — CPU-bound
- Emulator orchestration (Android emulator) — CPU/RAM bound

### The benchmark story
PARALLAX is genuinely a workload that benefits from GPU acceleration. The submission includes:
- **Throughput**: APKs analyzed per hour on MI300X vs CPU-only baseline
- **Latency**: P50/P95/P99 inference latency per agent
- **Cost efficiency**: tokens/second per dollar on MI300X vs H100
- **Memory utilization**: 192GB HBM3 enables running multiple large models concurrently (no need to swap models in/out)
- **Multi-agent concurrency**: MI300X runs all 8 agent models in parallel without OOM, vs CPU/NVIDIA setups that require sequential inference

This is a real benchmark story, not a synthetic one.

---

## 4. The agent map — PARALLAX on AMD

| Agent | Model on AMD | AMD-specific consideration |
|---|---|---|
| Triage Agent | Phi-3-mini / Llama 3.1 8B | Small model, fast inference, low memory |
| Static Analysis Agent | DeepSeek-Coder-V2 / Qwen2.5-Coder-32B | Code-specialized, large model, benefits from HBM3 |
| Dynamic Analysis Agent | DeepSeek-Coder-V2 / Qwen2.5-Coder-32B | Same as static — runs in parallel |
| Hypothesis Engine | Qwen2.5-72B / DeepSeek-V3 | Reasoning-heavy, benefits from MI300X's large memory |
| Mule Graph Agent | DeepSeek-V3 / Qwen2.5-72B | Reasoning + graph data integration |
| Visual Phishing Agent | LLaVA-OneVision / Qwen2.5-VL-72B | Multimodal vision, large model |
| Evidence Validator | Qwen2.5-72B / Claude (if available) | Careful reasoning, challenge mode |
| Decision Convenor | Qwen2.5-72B / DeepSeek-V3 | Synthesis, final action packet |
| Brand Impersonation Engine | CLIP + LLaVA-OneVision | Embedding + multimodal vision |

**All models open-source (no API costs, full control).** MI300X's 192GB HBM3 enables running 3-4 large models concurrently without OOM.

---

## 5. ROCm stack — the technical depth story

### Stack components
- **Ollama with ROCm backend** — primary inference server
- **PyTorch ROCm** — for custom model code (Hypothesis Engine, embedding generation)
- **vLLM with ROCm** — for high-throughput serving of specific agents
- **Hugging Face Optimum-AMD** — for inference optimization
- **ROCm SMI** — for GPU monitoring and benchmarking
- **Transformers + ROCm** — for any agent that uses transformers directly

### What the submission proves
- PARALLAX runs cleanly on ROCm (not just CUDA)
- Ollama serves all PARALLAX models on MI300X
- Multi-agent concurrency works on a single MI300X (memory headroom for 3-4 large models)
- Performance is competitive with NVIDIA for PARALLAX's workload
- ROCm tooling (profiling, monitoring) integrates with PARALLAX's observability stack

### Potential ROCm gotchas (the honest ones)
- Some open-source models have known ROCm issues (specific attention kernels, certain quantization formats)
- vLLM ROCm support is less mature than CUDA
- Ollama's AMD support has improved but isn't bug-free
- Mitigation: include fallback model choices in the demo, document any ROCm workarounds in the submission

---

## 6. The benchmark deliverable

This is the real differentiator. Most AMD hackathon submissions are demos. PARALLAX-AMD includes a **real performance comparison** that's useful for the team's own deployment planning AND for international bank customers evaluating GPU infrastructure.

### Benchmark suite
1. **Single-agent inference latency** — measure P50/P95/P99 for each of the 8 agents
2. **Multi-agent concurrent throughput** — measure how many fraud cases can be processed per hour with all agents running in parallel
3. **End-to-end APK analysis time** — measure time from APK submission to final Fraud Attack Chain
4. **Memory utilization** — measure peak VRAM, average VRAM, OOM events
5. **Cost efficiency** — tokens/second/dollar for MI300X vs published H100/H200 numbers
6. **Model concurrency** — measure how many large models can be resident in 192GB HBM3 simultaneously
7. **ROCm vs CUDA comparison** — apples-to-apples for at least one model

### Benchmark tooling
- **vLLM benchmark scripts** — standardized throughput measurement
- **Ollama benchmark mode** — built-in performance metrics
- **ROCm SMI** — GPU utilization, memory bandwidth
- **Custom PARALLAX benchmark harness** — measures end-to-end fraud case processing
- **MLPerf-style result tables** — published in submission

---

## 7. What stays untouched vs what's new

### Stays untouched (PARALLAX core)
- All v2 modules
- All agent frameworks (LangGraph, Pydantic AI, CrewAI, AutoGen)
- All RE tools
- Neo4j TAIG
- Postgres metadata
- Ollama configurations (just point at AMD GPU instead of NVIDIA)

### New components
1. **`parallax/integrations/amd/`** — adapter package
   - `rocm_config.py` — ROCm environment configuration
   - `amd_model_configs.py` — model configs tuned for MI300X
   - `benchmark_harness.py` — performance benchmark suite
   - `mi300x_deployment.yaml` — Kubernetes/Docker deployment for AMD
2. **AMD Developer Cloud deployment** — running PARALLAX on MI300X
3. **Benchmark report** — MI300X vs NVIDIA comparison
4. **One synthetic demo case** — pre-analyzed synthetic APK
5. **Demo video** showing end-to-end PARALLAX on MI300X

### Why the engine is untouched
AMD is the GPU substrate. PARALLAX remains self-contained. The integration is purely at the deployment layer.

---

## 8. Team of 6 — role allocation

| Role | Person | Responsibilities |
|---|---|---|
| **Lead architect** | (you) | PARALLAX-AMD integration design, submission narrative, performance story |
| **Backend agent dev #1** | TBD | Ollama + ROCm setup, model deployment, agent wiring on AMD |
| **Backend agent dev #2** | TBD | vLLM + ROCm high-throughput serving, multi-agent concurrency |
| **ML engineer** | TBD | Benchmark harness, performance measurement, ROCm optimization |
| **DevOps / deployment** | TBD | AMD Developer Cloud deployment, monitoring, observability |
| **Documentation / demo** | TBD | Synthetic case scenario, demo video, benchmark report, architecture diagram |

---

## 9. Synthetic demo case scenario

**Case ID:** `CASE-AMD-2026-00121`
**Customer complaint (synthetic):**
> "₹1.8L transferred to unknown UPI ID. Phone had a fake 'PhonePe KYC' app. Please help."

**Pre-analyzed mock data:**
- Synthetic APK hash (benign, pre-analyzed by PARALLAX)
- Synthetic transaction trail
- Mock mule account database
- Mock brand impersonation screenshots

**Demo flow (target: 3-5 minutes):**
1. APK uploaded to PARALLAX running on MI300X (10s)
2. Live benchmark dashboard shows MI300X utilization (5s)
3. Triage Agent runs (Phi-3 on AMD) — fast triage (10s)
4. Static + Dynamic + Visual Phishing agents run in parallel (DeepSeek-Coder-V2, LLaVA-OneVision on AMD) (30s)
5. Hypothesis Engine emits 3 hypotheses (DeepSeek-V3 on AMD) (15s)
6. Mule Graph Agent queries Neo4j (graph traversal accelerated by MI300X memory bandwidth) (15s)
7. Decision Convenor synthesizes final action packet (Qwen2.5-72B on AMD) (15s)
8. Benchmark results: P50/P95 latency, throughput, GPU utilization (10s)
9. Cost efficiency comparison: MI300X vs H100 baseline (10s)
10. Architecture diagram: PARALLAX on AMD stack (Ollama, vLLM, Neo4j, MI300X, ROCm) (15s)

Total: ~3 minutes. Every AMD capability visible: MI300X inference, ROCm stack, multi-agent concurrency, benchmark story.

---

## 10. Win strategy

### Why we'd podium
1. **Real ROCm validation** — not a sticker. PARALLAX is a real workload that runs cleanly on MI300X
2. **Performance benchmark credibility** — apples-to-apples MI300X vs H100 for the actual fraud-analysis workload is real value for AMD's marketing
3. **Multi-agent concurrency story** — MI300X's 192GB HBM3 enables a workload NVIDIA setups can't match (running 3-4 large models concurrently)
4. **Open-source model showcase** — PARALLAX uses Llama, DeepSeek, Qwen, Mistral — all open-source, all running on ROCm
5. **Production deployment narrative** — banks evaluating GPU infrastructure get a real reference architecture
6. **Direct track fit** — Track 1 is "build sophisticated AI agentic systems," and PARALLAX is exactly that

### Risks
- ROCm has real gotchas (kernel issues, model compatibility) — need fallback model choices
- AMD Developer Cloud may have limited instance availability during hackathon
- Benchmark credibility requires careful methodology — judges will scrutinize
- Track 1 likely has more competition than Track 2 or 3 (beginner-friendly track)

### What triggers downgrade to skip
- ROCm is too unstable for production-grade demo (workarounds are hacks)
- Multi-agent concurrency doesn't work on MI300X (memory issues)
- Team can't credibly do performance benchmarks in 2-3 weeks
- AMD Developer Cloud is too unstable for reliable deployment

---

## 11. Build order (only after main PARALLAX is complete)

| Phase | Duration | Deliverable |
|---|---|---|
| Phase 1: AMD stack ramp | 3-4 days | Team trained on Ollama-ROCm, vLLM-ROCm, Hugging Face Optimum-AMD |
| Phase 2: PARALLAX on MI300X | 5-6 days | All 8 agents running on AMD Developer Cloud, multi-agent concurrency working |
| Phase 3: Benchmark harness | 4-5 days | Custom benchmark suite measuring PARALLAX workload on MI300X |
| Phase 4: Performance comparison | 3-4 days | MI300X vs H100 baseline, results table, cost analysis |
| Phase 5: Synthetic case + demo | 3-4 days | Synthetic case scenario, end-to-end run-through, demo video |
| Phase 6: Submission packaging | 2-3 days | Submission text, architecture diagram, benchmark report, video upload |
| **Total** | **~4-5 weeks** | **Submission ready** |

---

## 12. Resume point for future sessions

When you return to plan this in depth, start by reading:
1. This file (submission framing + decisions)
2. `C:\Users\arjun\Desktop\PSBs\01_IDEATION.md` (PARALLAX core design)
3. `C:\Users\arjun\Desktop\PSBs\02_ARCHITECTURE.md` (5-layer system)
4. `C:\Users\arjun\Desktop\Band-of-agents\Band-of-agents.md` (Band of Agents plan for cross-reference)
5. `C:\Users\arjun\Desktop\Band-of-agents\UiPath-AgentHack.md` (UiPath plan for cross-reference)
6. `C:\Users\arjun\Desktop\Band-of-agents\Splunk-AgenticOps.md` (Splunk plan for cross-reference)
7. AMD ROCm documentation (https://rocm.docs.amd.com/)
8. AMD Developer Cloud getting started guide
9. PARALLAX v2 modules in `C:\Users\arjun\Desktop\parallax_repo\src\parallax\models\v2\`

---

## 13. Open questions to resolve at hackathon kickoff

1. **AMD Developer Cloud instance availability** — confirm MI300X instances are available throughout hackathon period
2. **ROCm maturity for Ollama/vLLM** — verify the specific model versions PARALLAX needs work cleanly on ROCm
3. **Hugging Face Optimum-AMD feature parity** — confirm the optimizations we want to use are available
4. **Per-member credit math** — verify $100 per member × 6 team = $600 total is allocated correctly
5. **AMD AI Academy content relevance** — check if there are ROCm-specific tutorials that accelerate ramp
6. **AMD Expert Access** — can we get office hours with AMD engineers to validate our benchmark methodology?
7. **Submission format** — confirm video, architecture diagram, and code repo requirements
8. **Public release of benchmark results** — does AMD want exclusive use of our benchmark data, or can we publish openly?

---

## 14. Final verdict snapshot

| Dimension | Verdict |
|---|---|
| PARALLAX fit | ★★★★★ — Track 1 is multi-agent systems, PARALLAX is multi-agent system |
| Tech integration | ★★★★★ — AMD as production GPU substrate is durable production tech |
| Win chance | ★★★★☆ — Track 1 has more competition but real AMD value |
| Build cost | ★★★☆☆ — ROCm ramp + benchmark work is real effort, ~4-5 weeks |
| International leverage | ★★★★★ — Banks with AMD infrastructure get a real deployment option |
| Credits/support | ★★★★☆ — $100/member + MI300X access + expert hours are real |
| Bonus prize potential | ★★★☆☆ — AMD-specific bonus (best ROCm use, etc.) reachable |

**Confirmed: GO on Track 1 (AI Agents & Agentic Workflows), PARALLAX on AMD Instinct MI300X + ROCm.**

**Build order across all GOs** (user decides what to pursue based on availability):
1. **Band of Agents** — agent collaboration governance (simplest architecture change, ~3 weeks)
2. **AMD ACT II** — production GPU validation (~4-5 weeks)
3. **UiPath AgentHack** — case management + distribution (~5 weeks)
4. **Splunk Agentic Ops** — SIEM integration + cross-system evidence (conditional, ~3-4 weeks)

The four GOs highlight **different production layers** of PARALLAX:
- Band = agent collaboration governance
- AMD = GPU infrastructure validation
- UiPath = case management + enterprise distribution
- Splunk = SIEM integration + cross-system evidence

No two compete for the same code paths. Team can split work efficiently across all four.
