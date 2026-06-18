# PARALLAX: Agentic Malware Analysis Platform
## Executive Whitepaper

### Abstract
Modern malware is increasingly polymorphic, adaptive, and designed to evade traditional sandbox environments. Traditional static analysis tools generate massive amounts of noise, leading to analyst fatigue. **Parallax** is a next-generation malware analysis platform that introduces an **Agentic Workflow**, **Two-Layer Risk Scoring**, and an **Infrastructure Degradation Matrix** to provide high-fidelity, resilient, and fully automated threat intelligence.

### 1. Introduction
Parallax bridges the gap between raw telemetry and actionable intelligence by combining deterministic static analysis (Soot, YARA) with non-deterministic dynamic analysis (Frida, Android Emulator) and orchestrating them through an intelligent LLM agent. By reasoning over execution traces and code artifacts, Parallax identifies the *intent* of an application rather than relying solely on signatures.

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
- **Final Confidence Score**: A post-dynamic score refined by the LLM, taking into account observed behaviors. If the LLM's confidence is low, the system widens the confidence interval, flagging the sample for manual analyst review.

### 5. Infrastructure Degradation Matrix
Security infrastructure often fails under load or sophisticated attacks. Parallax is designed to degrade gracefully rather than fail entirely:
- **LLM Fallback**: If the cloud provider (e.g., Anthropic) is unreachable or rate-limited, Parallax automatically falls back to a locally hosted model (Ollama).
- **Dynamic Analysis Failure**: If the Emulator Pool is exhausted or crashes, Parallax skips the dynamic stage and relies solely on static heuristics.
- **Database Resilience**: If Neo4j or Qdrant goes offline, the analysis continues without graph population or semantic search, ensuring the core triage pipeline remains uninterrupted.

### 6. Conclusion
Parallax represents a paradigm shift in automated malware analysis. By integrating deterministic tooling with resilient agentic reasoning, Parallax enables security operations centers to triage Android malware at unprecedented scale and accuracy.
