"""PARALLAX Band agent registry. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from parallax.core.config import settings

AgentRole = Literal[
    "intake",
    "device_compromise",
    "transaction_trace",
    "mule_graph",
    "evidence_validator",
    "liability",
    "legal_evidence",
    "decision_convenor",
]


@dataclass(frozen=True)
class AgentDescriptor:
    role: AgentRole
    display_name: str
    handle: str
    env_id_key: str
    env_api_key: str
    description: str

    @property
    def configured_id(self) -> str:
        return str(getattr(settings, self.env_id_key, "") or "")

    @property
    def configured_api_key(self) -> str:
        return str(getattr(settings, self.env_api_key, "") or "")

    @property
    def participant_ref(self) -> str:
        return self.configured_id or self.handle


AGENT_ROSTER: tuple[AgentDescriptor, ...] = (
    AgentDescriptor(
        role="intake",
        display_name="PARALLAX Intake Agent",
        handle="@arjun7n9s/parallax-intake-agent",
        env_id_key="BAND_AGENT_INTAKE_ID",
        env_api_key="BAND_AGENT_INTAKE_API_KEY",
        description="Opens rooms, snapshots evidence bundles, extracts case entities, and recruits peers.",
    ),
    AgentDescriptor(
        role="device_compromise",
        display_name="PARALLAX Device Compromise Agent",
        handle="@arjun7n9s/parallax-device-compromi",
        env_id_key="BAND_AGENT_DEVICE_COMPROMISE_ID",
        env_api_key="BAND_AGENT_DEVICE_COMPROMISE_API_KEY",
        description="Reviews APK permissions, static findings, dynamic observations, and timeline signals.",
    ),
    AgentDescriptor(
        role="transaction_trace",
        display_name="PARALLAX Transaction Trace Agent",
        handle="@arjun7n9s/parallax-transaction-tra",
        env_id_key="BAND_AGENT_TRANSACTION_TRACE_ID",
        env_api_key="BAND_AGENT_TRANSACTION_TRACE_API_KEY",
        description="Reconstructs disputed transfer flows and mule-account patterns.",
    ),
    AgentDescriptor(
        role="mule_graph",
        display_name="PARALLAX Mule Graph Agent",
        handle="@arjun7n9s/parallax-mule-graph-agen",
        env_id_key="BAND_AGENT_MULE_GRAPH_ID",
        env_api_key="BAND_AGENT_MULE_GRAPH_API_KEY",
        description="Queries TAIG and fraud graph evidence for linked mule and campaign overlap.",
    ),
    AgentDescriptor(
        role="evidence_validator",
        display_name="PARALLAX Evidence Validator Agent",
        handle="@arjun7n9s/parallax-evidence-valida",
        env_id_key="BAND_AGENT_EVIDENCE_VALIDATOR_ID",
        env_api_key="BAND_AGENT_EVIDENCE_VALIDATOR_API_KEY",
        description="Challenges weak claims and forces confidence adjustments.",
    ),
    AgentDescriptor(
        role="liability",
        display_name="PARALLAX Liability Agent",
        handle="@arjun7n9s/parallax-liability-agent",
        env_id_key="BAND_AGENT_LIABILITY_ID",
        env_api_key="BAND_AGENT_LIABILITY_API_KEY",
        description="Applies synthetic bank policy rules to provisional-credit decisions.",
    ),
    AgentDescriptor(
        role="legal_evidence",
        display_name="PARALLAX Legal Evidence Agent",
        handle="@arjun7n9s/parallax-legal-evidence",
        env_id_key="BAND_AGENT_LEGAL_EVIDENCE_ID",
        env_api_key="BAND_AGENT_LEGAL_EVIDENCE_API_KEY",
        description="Builds cyber-cell-ready and audit-safe evidence packets.",
    ),
    AgentDescriptor(
        role="decision_convenor",
        display_name="PARALLAX Decision Convenor Agent",
        handle="@arjun7n9s/parallax-decision-conven",
        env_id_key="BAND_AGENT_DECISION_CONVENOR_ID",
        env_api_key="BAND_AGENT_DECISION_CONVENOR_API_KEY",
        description="Tracks open challenges and issues final or provisional action packets.",
    ),
)


def participant_refs() -> list[str]:
    return [agent.participant_ref for agent in AGENT_ROSTER]


def agent_by_role(role: AgentRole) -> AgentDescriptor:
    for agent in AGENT_ROSTER:
        if agent.role == role:
            return agent
    raise KeyError(role)
