"""AI Reasoning Cortex orchestration.

Implements the planned DAG:

    INPUT -> [parallel: code_interpreter, behavior_analyst, visual]
          -> intel_correlator (needs code+behavior)
          -> debate -> risk -> synthesis -> CortexResult

Agents run concurrently; a failure in one is isolated (recorded in
``agent_errors``) so the cortex still produces a verdict from the rest. The
verdict and numeric score come from the deterministic risk module, never the
LLM.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from parallax.ai.agents.behavior_analyst import run_behavior_analyst
from parallax.ai.agents.code_interpreter import run_code_interpreter
from parallax.ai.agents.intel_correlator import run_intel_correlator
from parallax.ai.agents.synthesis import run_synthesis
from parallax.ai.agents.visual import run_visual_intelligence
from parallax.ai.debate import run_debate
from parallax.ai.risk import compute_risk
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    CortexResult,
    IntelCorrelatorOutput,
    VisualIntelOutput,
)

logger = logging.getLogger(__name__)

_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HOST_RE = re.compile(r"https?://([A-Za-z0-9.\-]+)")
_URL_RE = re.compile(r"https?://[A-Za-z0-9.\-:/_%?=&]+")


def _extract_iocs(
    observations: list[dict[str, Any]],
    behavior: BehaviorAnalystOutput | None,
    code: CodeInterpreterOutput | None,
) -> dict[str, list[str]]:
    urls: set[str] = set()
    domains: set[str] = set()
    ips: set[str] = set()

    def scan(text: str) -> None:
        for u in _URL_RE.findall(text):
            urls.add(u)
        for h in _HOST_RE.findall(text):
            domains.add(h)
        for ip in _IP_RE.findall(text):
            ips.add(ip)

    for obs in observations:
        blob = str(obs.get("args")) + " " + str(obs.get("event_type"))
        scan(blob)
    if behavior:
        for ioc in behavior.network_iocs:
            scan(ioc)
            if "." in ioc and "/" not in ioc and not _IP_RE.match(ioc):
                domains.add(ioc)
    if code:
        for ev in code.evidence:
            scan(ev)

    # Domains that are bare IPs belong in ips.
    domains = {d for d in domains if not _IP_RE.match(d)}
    return {
        "urls": sorted(urls),
        "domains": sorted(domains),
        "ips": sorted(ips),
    }


async def _safe(coro, name: str, errors: dict[str, str]):
    try:
        return await coro
    except Exception as exc:  # isolate per-agent failure
        logger.warning("Cortex agent %s failed: %s", name, exc)
        errors[name] = str(exc)
        return None


async def run_cortex(
    *,
    submission_id: str,
    sha256: str,
    artifact: dict,
    sources_dir: str | None,
    observations: list[dict[str, Any]],
    screenshot_keys: list[str],
    apkid: dict | None = None,
    related_samples: list[dict] | None = None,
    taint_flows: list[dict] | None = None,
) -> CortexResult:
    errors: dict[str, str] = {}
    features = artifact.get("static_features", {}) if artifact else {}
    permissions = features.get("permissions", [])
    yara_matches = artifact.get("yara_matches", []) if artifact else []
    taint_flows = taint_flows or []

    # Stage 1: independent agents in parallel.
    code, behavior, visual = await asyncio.gather(
        _safe(
            run_code_interpreter(artifact, sources_dir, taint_flows),
            "code_interpreter",
            errors,
        ),
        _safe(run_behavior_analyst(observations), "behavior_analyst", errors),
        _safe(run_visual_intelligence(screenshot_keys), "visual", errors),
    )
    code = code or CodeInterpreterOutput()
    behavior = behavior or BehaviorAnalystOutput()
    visual = visual or VisualIntelOutput()

    iocs = _extract_iocs(observations, behavior, code)

    # Stage 2: intel correlation depends on code + behavior.
    intel = await _safe(
        run_intel_correlator(code, behavior, iocs, related_samples, taint_flows),
        "intel_correlator",
        errors,
    )
    intel = intel or IntelCorrelatorOutput()

    # Hash + infrastructure family attribution from external threat intel
    # (MalwareBazaar/VT) and our own TAIG corpus. This is ground-truth evidence
    # the LLM cannot derive from code alone, so it overrides an empty LLM guess.
    from parallax.knowledge.ioc_matcher import match_iocs

    family_match = await _safe(
        match_iocs(sha256, iocs.get("domains", []), iocs.get("ips", [])),
        "ioc_matcher",
        errors,
    )
    if family_match and family_match.get("family"):
        if not intel.family_attribution:
            intel.family_attribution = family_match["family"]
        intel.family_confidence = max(intel.family_confidence, family_match.get("confidence", 0.0))

    # Stage 3: deterministic debate + risk.
    debate = run_debate(code, behavior, intel, visual)
    risk = compute_risk(
        permissions=permissions,
        code=code,
        behavior=behavior,
        intel=intel,
        visual=visual,
        debate=debate,
        apkid=apkid,
        yara_matches=yara_matches,
        taint_flows=taint_flows,
        known_family=family_match,
    )

    # Stage 4: synthesis narrative.
    synth = await _safe(
        run_synthesis(
            code=code,
            behavior=behavior,
            intel=intel,
            visual=visual,
            debate=debate,
            risk=risk,
            package_name=features.get("package_name", "unknown"),
        ),
        "synthesis",
        errors,
    )
    synth = synth or {
        "executive_summary": "",
        "technical_findings": [],
        "irt": [],
        "recommendations": [],
    }

    # Merge ATT&CK from code + intel + taint (taint mappings are curated
    # source/sink->technique facts, not LLM output — always trustworthy).
    taint_attck = {t["attck_technique"] for t in taint_flows if t.get("attck_technique")}
    attck = sorted(set(code.attck_techniques) | set(intel.attck_techniques) | taint_attck)

    return CortexResult(
        submission_id=submission_id,
        sha256=sha256,
        verdict=risk.verdict,
        risk=risk,
        executive_summary=synth["executive_summary"],
        technical_findings=synth["technical_findings"],
        attck_techniques=attck,
        kill_chain=behavior.kill_chain,
        iocs=iocs,
        irt=synth["irt"],
        recommendations=synth["recommendations"],
        code_interpreter=code,
        behavior_analyst=behavior,
        intel_correlator=intel,
        visual=visual,
        debate=debate,
        agent_errors=errors,
    )
