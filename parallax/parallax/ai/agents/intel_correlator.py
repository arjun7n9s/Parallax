"""Intel Correlator agent — ATT&CK mapping + family/campaign attribution."""

from __future__ import annotations

import json
import logging

from parallax.ai.llm import llm
from parallax.ai.prompts.cortex import INTEL_CORRELATOR_SYSTEM
from parallax.ai.rag.attck import retrieve_techniques
from parallax.ai.schemas import (
    BehaviorAnalystOutput,
    CodeInterpreterOutput,
    IntelCorrelatorOutput,
)

logger = logging.getLogger(__name__)


def _build_query(code: CodeInterpreterOutput, behavior: BehaviorAnalystOutput) -> str:
    parts: list[str] = []
    if code:
        parts.append(code.intent_classification)
        parts.extend(code.evidence[:10])
        parts.extend(code.attack_flow[:10])
    if behavior:
        parts.append(behavior.overall_narrative)
        parts.extend(behavior.observed_behaviors[:10])
    return " ".join(p for p in parts if p)


async def run_intel_correlator(
    code: CodeInterpreterOutput,
    behavior: BehaviorAnalystOutput,
    iocs: dict[str, list[str]],
    related_samples: list[dict] | None = None,
) -> IntelCorrelatorOutput:
    """Correlate behaviors to ATT&CK techniques and known families.

    ``related_samples`` are prior analyses retrieved from the TAIG/Qdrant store
    (Phase 5). When empty, the agent relies on ATT&CK retrieval alone.
    """
    query = _build_query(code, behavior)
    candidates = await retrieve_techniques(query, top_k=10)

    prompt_parts = [
        "RETRIEVED ATT&CK MOBILE TECHNIQUE CANDIDATES (pick only from these):",
        json.dumps(candidates, indent=2),
        "",
        "EXTRACTED IOCs:",
        json.dumps(iocs),
        "",
        "CODE INTENT: " + (code.intent_classification if code else "unknown"),
        "BEHAVIOR NARRATIVE: " + (behavior.overall_narrative if behavior else ""),
    ]
    if related_samples:
        prompt_parts += [
            "",
            "RELATED PRIOR ANALYSES (from knowledge base):",
            json.dumps(related_samples[:5], indent=2),
        ]
    prompt_parts.append(
        "\nMap to ATT&CK techniques and attribute a family/campaign only if "
        "the retrieved evidence supports it."
    )
    prompt = "\n".join(prompt_parts)

    raw = await llm.complete_json("intel_correlator", prompt, INTEL_CORRELATOR_SYSTEM)
    out = IntelCorrelatorOutput.model_validate(raw)

    # Guard against hallucinated technique IDs: keep only retrieved candidates.
    valid_ids = {c["technique_id"] for c in candidates}
    if valid_ids:
        out.attck_techniques = [t for t in out.attck_techniques if t in valid_ids]
    if related_samples:
        out.related_submissions = [
            s.get("sha256", "") for s in related_samples if s.get("sha256")
        ]
    return out
