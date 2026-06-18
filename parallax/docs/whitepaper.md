# PARALLAX: Agentic Malware Analysis Platform
## Draft Executive Whitepaper

### Abstract
Modern Android malware is increasingly adaptive and designed to evade traditional sandbox environments. Traditional static analysis tools can generate significant noise, leading to analyst fatigue. **PARALLAX** combines deterministic APK analysis, dynamic instrumentation, and agent-assisted reasoning to produce evidence-first reports for banking fraud and malware triage.

This paper is a product and architecture summary. Accuracy, calibration, and case-study claims remain pending until the corpus validation workflow is run on a representative sample set.

### 1. Introduction
PARALLAX bridges the gap between raw telemetry and actionable intelligence by combining deterministic static analysis (Jadx, YARA, FlowDroid where configured) with dynamic analysis (Frida, mitmproxy, Android emulator) and structured LLM-assisted reasoning. The goal is to surface the likely intent of an application while keeping the underlying evidence auditable.

### 2. Core Architecture
The Parallax pipeline is built on a resilient, microservice-based architecture:
- **API Layer**: A high-performance FastAPI service handling submissions and SSE (Server-Sent Events) for real-time status streaming.
- **Worker Pool**: Celery distributed task queues execute heavy static analysis and instrumented dynamic runs.
- **Emulator Pool**: A scalable, KVM-accelerated pool of Android emulators managed programmatically.
- **Data Layer**: PostgreSQL for metadata, MinIO for artifact storage, Neo4j for Threat Activity Intent Graphs (TAIG), and Qdrant for semantic vector search.

### 3. The Agentic Workflow
Parallax replaces static rule engines with an autonomous agentic reasoning loop:
1. **Hypothesis Generation**: The LLM reviews static strings and dynamic API hooks to formulate hypotheses (e.g., "The app exfiltrates SMS messages to a C2 server").
2. **Targeted Instrumentation**: Based on hypotheses, the system dynamically generates Frida scripts to hook specific Android APIs (e.g., `SmsManager.sendTextMessage`).
3. **Synthesis**: The agent aggregates findings into a structured Cortex report and a MITRE ATT&CK mapped Fraud Chain.

### 4. Two-Layer Risk Scoring
To reduce false positives and ensure analysts focus on critical threats, Parallax uses a two-tier scoring system:
- **Triage Score**: A fast, deterministic score computed immediately after static analysis using YARA rules, permissions mapping, and heuristic matching.
- **Final Risk Score**: A post-dynamic score refined from observed behaviors, agent confidence, debate output, and available evidence. Calibration of this layer against a large corpus is still pending.

### 5. Infrastructure Degradation Matrix
Security infrastructure often fails under load or sophisticated attacks. Parallax is designed to degrade gracefully rather than fail entirely:
- **LLM Fallback**: If the cloud provider (e.g., Anthropic) is unreachable or rate-limited, Parallax automatically falls back to a locally hosted model (Ollama).
- **Dynamic Analysis Failure**: If the Emulator Pool is exhausted or crashes, Parallax skips the dynamic stage and relies solely on static heuristics.
- **Database Resilience**: If Neo4j or Qdrant goes offline, the analysis continues without graph population or semantic search, ensuring the core triage pipeline remains uninterrupted.

### 6. Conclusion
PARALLAX is designed to help security operations centers triage Android malware and banking fraud apps faster while preserving evidence for analyst review. The next validation milestone is a reproducible corpus run with calibrated risk scoring and documented case studies.
