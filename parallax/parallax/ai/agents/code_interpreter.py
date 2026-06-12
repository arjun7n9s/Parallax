"""Code Interpreter agent — static intent classification from decompiled code."""

from __future__ import annotations

import json
import logging

from parallax.ai.llm import llm
from parallax.ai.prompts.cortex import CODE_INTERPRETER_SYSTEM
from parallax.ai.re_workbench.code_selector import select_relevant_code
from parallax.ai.schemas import CodeInterpreterOutput

logger = logging.getLogger(__name__)


def _build_prompt(
    artifact: dict,
    code: str,
    selected: list[str],
    urls: list[str],
    taint_flows: list[dict] | None = None,
) -> str:
    features = artifact.get("static_features", {})
    yara = [m.get("rule") for m in artifact.get("yara_matches", [])]
    parts = [
        "STATIC FACTS",
        f"package: {features.get('package_name')}",
        f"permissions: {json.dumps(features.get('permissions', []))}",
        f"services: {json.dumps(features.get('services', []))}",
        f"receivers: {json.dumps(features.get('receivers', []))}",
        f"activities_count: {len(features.get('activities', []))}",
        f"yara_matches: {json.dumps(yara)}",
        f"hardcoded_urls_in_code: {json.dumps(urls[:25])}",
    ]
    if taint_flows:
        parts += [
            "",
            "STATIC TAINT FLOWS (FlowDroid: proven source->sink data paths — "
            "what the app COULD do even if not observed at runtime):",
            json.dumps(taint_flows[:20], indent=1),
        ]
    parts += [
        "",
        f"DECOMPILED CODE (top {len(selected)} security-relevant files):",
        code if code else "(no security-relevant code matched the selector)",
        "",
        "Classify the app's intent grounded in the facts and code above.",
    ]
    return "\n".join(parts)


async def run_code_interpreter(
    artifact: dict,
    sources_dir: str | None,
    taint_flows: list[dict] | None = None,
) -> CodeInterpreterOutput:
    """Analyze decompiled code + static facts and classify intent.

    ``artifact`` is the REArtifactModel dict; ``sources_dir`` is the local jadx
    output directory (or its ``sources`` subdir); ``taint_flows`` are FlowDroid
    source->sink records (Phase 2.5) giving static causal evidence.
    """
    code: str = ""
    selected: list[str] = []
    urls: list[str] = []
    if sources_dir:
        code, selected, urls = select_relevant_code(sources_dir)

    prompt = _build_prompt(artifact, code, selected, urls, taint_flows)
    raw = await llm.complete_json("code_interpreter", prompt, CODE_INTERPRETER_SYSTEM)
    out = CodeInterpreterOutput.model_validate(raw)
    # Always surface the hardcoded URLs we found, even if the model missed them.
    if urls and not any("url" in e.lower() or "http" in e.lower() for e in out.evidence):
        out.evidence.append(f"hardcoded URLs in code: {', '.join(urls[:5])}")
    return out
