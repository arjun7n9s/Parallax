"""Band SDK remote-agent orchestrator. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from parallax.agents.band.agents import AGENT_ROSTER, AgentDescriptor
from parallax.core.config import settings

logger = logging.getLogger(__name__)


class BandSDKUnavailable(RuntimeError):
    """Raised when band-sdk/langgraph dependencies are not installed."""


@dataclass(frozen=True)
class RemoteAgentSpec:
    descriptor: AgentDescriptor
    system_prompt: str

    @property
    def agent_id(self) -> str:
        return self.descriptor.configured_id

    @property
    def api_key(self) -> str:
        return self.descriptor.configured_api_key

    @property
    def ready(self) -> bool:
        return bool(self.agent_id and self.api_key)


SYSTEM_PROMPTS: dict[str, str] = {
    "intake": (
        "You are PARALLAX Intake Agent. Open fraud-analysis rooms, explain the immutable "
        "evidence bundle, recruit peer agents, and keep the case bounded."
    ),
    "device_compromise": (
        "You are PARALLAX Device Compromise Agent. Assess Android APK and runtime evidence "
        "for account takeover, OTP interception, accessibility abuse, and overlay abuse."
    ),
    "transaction_trace": (
        "You are PARALLAX Transaction Trace Agent. Analyze synthetic/demo bank-ledger traces "
        "and separate mule-splitting patterns from normal payments."
    ),
    "mule_graph": (
        "You are PARALLAX Mule Graph Agent. Reason over TAIG-style graph links, shared IOCs, "
        "and beneficiary/campaign overlap."
    ),
    "evidence_validator": (
        "You are PARALLAX Evidence Validator Agent. Challenge weak claims, demand source "
        "paths, and prevent final convergence while material disputes are unresolved."
    ),
    "liability": (
        "You are PARALLAX Liability Agent. Apply bank policy context, customer-report timing, "
        "and credential-sharing signals to provisional-credit recommendations."
    ),
    "legal_evidence": (
        "You are PARALLAX Legal Evidence Agent. Produce cyber-cell-ready evidence packet "
        "requirements with bundle hashes, IOCs, timelines, and transcript references."
    ),
    "decision_convenor": (
        "You are PARALLAX Decision Convenor Agent. Synthesize the room into provisional or "
        "final bank-officer action packets without overruling open challenges."
    ),
}


def remote_agent_specs(roles: Iterable[str] | None = None) -> list[RemoteAgentSpec]:
    selected = set(roles or [agent.role for agent in AGENT_ROSTER])
    return [
        RemoteAgentSpec(agent, SYSTEM_PROMPTS[agent.role])
        for agent in AGENT_ROSTER
        if agent.role in selected
    ]


def missing_credentials(specs: Iterable[RemoteAgentSpec]) -> list[str]:
    return [spec.descriptor.role for spec in specs if not spec.ready]


# Per-role model routing on the AI/ML API gateway (OpenAI-compatible). Economy
# models for high-frequency structured roles; a premium model for the reasoning,
# challenge, synthesis, and narrative roles where output quality is decisive.
# IDs match PARALLAX's own roster (parallax.ai.llm.ROSTER) for consistency.
_AIML_ECONOMY = "gpt-4o-mini"
_AIML_PREMIUM = "anthropic/claude-sonnet-4.6"
_AGENT_MODELS: dict[str, str] = {
    "intake": _AIML_ECONOMY,
    "transaction_trace": _AIML_ECONOMY,
    "mule_graph": _AIML_ECONOMY,
    "device_compromise": _AIML_PREMIUM,
    "evidence_validator": _AIML_PREMIUM,
    "liability": _AIML_PREMIUM,
    "legal_evidence": _AIML_PREMIUM,
    "decision_convenor": _AIML_PREMIUM,
}


def _llm_kwargs(role: str) -> dict[str, Any]:
    """ChatOpenAI kwargs for a Band agent. Routes through the AI/ML API gateway
    when ``AIML_API`` is set (the sponsor path PARALLAX already uses), else a
    direct OpenAI key. Raises a clear error if neither is configured rather than
    letting agents connect to Band and then 401 on their first message."""
    model = _AGENT_MODELS.get(role, _AIML_ECONOMY)
    if settings.AIML_API:
        return {
            "model": model,
            "base_url": settings.AIML_BASE_URL,
            "api_key": settings.AIML_API,
            "temperature": 0.2,
        }
    if settings.OPENAI_API_KEY:
        return {"model": model, "api_key": settings.OPENAI_API_KEY, "temperature": 0.2}
    raise ValueError(
        "No LLM provider configured for Band agents: set AIML_API (AI/ML API gateway) "
        "or OPENAI_API_KEY before connecting remote agents."
    )


def create_band_agent(spec: RemoteAgentSpec) -> Any:
    """Create one Band remote agent with the official SDK adapter path."""
    if not spec.ready:
        raise ValueError(f"Missing Band credentials for {spec.descriptor.role}")
    try:
        from band import Agent
        from band.adapters import LangGraphAdapter
        from langchain_openai import ChatOpenAI
        from langgraph.checkpoint.memory import InMemorySaver
    except ImportError as exc:
        raise BandSDKUnavailable(
            'Install Band remote-agent dependencies with: pip install "band-sdk[langgraph]" '
            "langchain-openai"
        ) from exc

    adapter = LangGraphAdapter(
        llm=ChatOpenAI(**_llm_kwargs(spec.descriptor.role)),
        checkpointer=InMemorySaver(),
        custom_section=spec.system_prompt,
        inject_system_prompt=True,
    )
    return Agent.create(
        adapter=adapter,
        agent_id=spec.agent_id,
        api_key=spec.api_key,
        ws_url=settings.BAND_WS_URL,
        rest_url=settings.BAND_REST_URL,
    )


async def run_remote_agents(roles: Iterable[str] | None = None) -> None:
    """Connect configured PARALLAX agents to Band over the SDK/WebSocket runtime."""
    specs = remote_agent_specs(roles)
    missing = missing_credentials(specs)
    if missing:
        raise ValueError(f"Missing Band credentials for roles: {', '.join(missing)}")

    agents = [create_band_agent(spec) for spec in specs]
    logger.info("Starting %d Band remote agent(s)", len(agents))
    await asyncio.gather(*(agent.run() for agent in agents))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PARALLAX Band remote agents.")
    parser.add_argument(
        "--role",
        action="append",
        choices=[agent.role for agent in AGENT_ROSTER],
        help="Run only this role. Repeat to run multiple roles. Default: all configured roles.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_remote_agents(args.role))


if __name__ == "__main__":
    main()
