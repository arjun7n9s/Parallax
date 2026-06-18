# Pricing and Packaging

This page is a planning model for buyer conversations. It avoids public accuracy, calibration, and cost-per-sample claims until the validation corpus and cost report are complete.

## Packaging

### Community Lab

For local demos, student teams, and internal security research.

- Single-node Docker Compose deployment
- Local Ollama-first reasoning
- One analyst tenant
- Manual backup and restore drill
- Community support only

### SOC Team

For a bank security team running routine Android APK triage.

- Multi-tenant API keys and audit logs
- Web console for submission, history, reports, and graph hunting
- Completion webhooks and batch submission
- Grafana, Prometheus, and Alertmanager bundle
- Helm deployment path for Kubernetes
- Email support and upgrade guidance

### Enterprise Bank

For regulated deployment, central platform teams, or multiple subsidiaries.

- Dedicated deployment architecture review
- Private model/provider routing policy
- Custom retention, quarantine, and audit controls
- DR runbook review and restore drills
- Security assessment support
- Priority support and roadmap review

## Cost Model

Track cost from measured telemetry, not estimates in slideware. PARALLAX exposes:

- `parallax_llm_cost_usd_total` for estimated cloud LLM spend by role and provider.
- `parallax_llm_tokens_total` for input/output token volume.
- `parallax_analysis_stage_seconds` for stage latency.
- `parallax_analysis_failures_total` for failed stages by error class.

The default Prometheus alert fires when daily estimated LLM spend exceeds the configured budget. Update the threshold in `prometheus_rules.yml` before production rollout.

## Pricing Formula

Use this formula after a validation or pilot run:

```text
monthly_price =
  platform_base_fee
  + expected_monthly_samples * measured_cost_per_sample * margin_multiplier
  + support_tier_fee
```

Where:

- `measured_cost_per_sample` comes from `increase(parallax_llm_cost_usd_total[30d]) / completed_samples`.
- `margin_multiplier` should cover cloud LLM spend variance, dynamic-analysis infrastructure, support, and failed/retried work.
- `support_tier_fee` depends on response-time commitments, audit support, and deployment complexity.

## Launch Guardrails

Do not publish firm per-sample pricing until:

- The corpus run has at least 200 usable samples.
- Cost metrics cover the same workload shape buyers will run.
- Local-only and cloud-routed modes are priced separately.
- Dynamic-analysis infrastructure cost is included, not just LLM spend.
- The package clearly states whether managed infrastructure, model tokens, and support are included.
