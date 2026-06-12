"""Behavior Analyst agent — kill-chain narrative from runtime observations."""

from __future__ import annotations

import json
import logging
from typing import Any

from parallax.ai.llm import llm
from parallax.ai.prompts.cortex import BEHAVIOR_ANALYST_SYSTEM
from parallax.ai.schemas import BehaviorAnalystOutput

logger = logging.getLogger(__name__)

_MAX_EVENTS = 200


def _summarize_observation(obs: dict[str, Any]) -> str:
    t = obs.get("captured_at_ms", 0)
    src = obs.get("source", "?")
    ev = obs.get("event_type", "?")
    args = obs.get("args")
    arg_str = ""
    if args:
        compact = json.dumps(args)[:200]
        arg_str = f" args={compact}"
    return f"[t+{t}ms][{src}] {ev}{arg_str}"


def _build_prompt(observations: list[dict[str, Any]]) -> str:
    timeline = sorted(observations, key=lambda o: o.get("captured_at_ms", 0))[:_MAX_EVENTS]
    if not timeline:
        return (
            "RUNTIME OBSERVATIONS: none captured (the app produced no hooked "
            "behavior or network traffic during the sandbox run).\n\n"
            "Report no observed malicious behavior with LOW risk."
        )
    lines = [_summarize_observation(o) for o in timeline]
    note = ""
    if len(observations) > _MAX_EVENTS:
        note = f"\n(showing first {_MAX_EVENTS} of {len(observations)} events)"
    return (
        "RUNTIME OBSERVATION TIMELINE (sandbox run)"
        + note
        + "\n"
        + "\n".join(lines)
        + "\n\nNarrate what the app did as a kill chain, grounded in these events."
    )


async def run_behavior_analyst(
    observations: list[dict[str, Any]],
) -> BehaviorAnalystOutput:
    prompt = _build_prompt(observations)
    raw = await llm.complete_json("behavior_analyst", prompt, BEHAVIOR_ANALYST_SYSTEM)
    return BehaviorAnalystOutput.model_validate(raw)
