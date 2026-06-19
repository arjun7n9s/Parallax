"""PARALLAX Band agent registry and deterministic stubs. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Protocol

from parallax.agents.band.band_adapter import BandAdapter
from parallax.agents.band.room_protocol import (
    ActionPacket,
    AgentMessage,
    CaseRoom,
    Challenge,
    EvidenceClaim,
    EvidenceRef,
)
from parallax.core.config import settings

logger = logging.getLogger(__name__)

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


class CaseAgent(Protocol):
    """Deterministic case-room agent used for demo-safe transcript generation."""

    descriptor: AgentDescriptor

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        """Return claims for the current room state."""


class BaseStubAgent:
    role: AgentRole

    @property
    def descriptor(self) -> AgentDescriptor:
        return agent_by_role(self.role)

    @property
    def agent_id(self) -> str:
        return self.descriptor.participant_ref

    def _claim(
        self,
        text: str,
        evidence_id: str,
        evidence_type: str,
        path: str,
        confidence: float,
        *,
        summary: str = "",
        supports_or_contradicts: list[str] | None = None,
    ) -> EvidenceClaim:
        return EvidenceClaim(
            claim_text=text,
            evidence_refs=[
                EvidenceRef(
                    evidence_id=evidence_id,
                    evidence_type=evidence_type,
                    path=path,
                    summary=summary,
                )
            ],
            confidence=confidence,
            agent_id=self.agent_id,
            supports_or_contradicts=supports_or_contradicts or [],
        )

    async def respond_live(self, room: CaseRoom) -> list[EvidenceClaim]:
        """Return LLM-backed claims when a subclass supports live reasoning."""
        return self.respond(room)


class IntakeAgent(BaseStubAgent):
    role: AgentRole = "intake"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        return [
            self._claim(
                (
                    f"Opened case {room.case_id} for submission {room.submission_id}; "
                    "all agents are reviewing the same immutable evidence snapshot."
                ),
                "bundle.snapshot",
                "bundle",
                "$",
                1.0,
                summary=f"Bundle SHA-256 {room.evidence_bundle.sha256}",
            )
        ]


class DeviceCompromiseAgent(BaseStubAgent):
    role: AgentRole = "device_compromise"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        return [
            self._claim(
                (
                    "APK requests accessibility-service binding plus overlay permission, "
                    "a strong device-compromise signal for mobile banking fraud."
                ),
                "submission.permissions",
                "static",
                "$.submission.permissions",
                0.91,
                summary="Accessibility and overlay permission pair.",
            ),
            self._claim(
                (
                    "Dynamic hooks captured SMS and notification-access behavior within "
                    "seconds of install, consistent with OTP interception."
                ),
                "observations.dynamic.sms",
                "dynamic",
                "$.observations[?type=='sms']",
                0.87,
                summary="SMS and notification collection.",
            ),
        ]

    async def respond_live(self, room: CaseRoom) -> list[EvidenceClaim]:
        prompt = _room_prompt(
            room,
            focus=(
                "Assess whether the Android device is compromised. Use the evidence bundle "
                "metadata and prior room claims only; do not invent package names, phone "
                "numbers, hashes, or URLs not present in context."
            ),
        )
        text = await llm_claim(
            prompt,
            system=(
                "You are PARALLAX Device Compromise Agent. Write one concise, evidence-first "
                "claim about APK/device compromise. Include uncertainty when evidence is sparse."
            ),
            role="behavior_analyst",
            fallback=self.respond(room)[0].claim_text,
        )
        return [
            self._claim(
                text,
                "bundle.device_compromise",
                "bundle",
                "$.submission",
                _confidence_from_text(text, default=0.84),
                summary="LLM-reviewed device compromise claim.",
            )
        ]


class TransactionTraceAgent(BaseStubAgent):
    role: AgentRole = "transaction_trace"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        return [
            self._claim(
                (
                    "Synthetic bank ledger shows five transfers totaling INR 3.4L "
                    "across three beneficiaries inside an 11-minute window."
                ),
                "synthetic.transactions",
                "bank-ledger",
                "$.transactions",
                0.82,
                summary="Demo-only transaction trace.",
            ),
            self._claim(
                (
                    "Transfer cadence and repeated beneficiary reuse match a mule-splitting "
                    "pattern rather than ordinary bill-payment behavior."
                ),
                "synthetic.transactions.cadence",
                "bank-ledger",
                "$.transactions[*].minute",
                0.78,
                summary="Rapid fan-out and reuse.",
            ),
        ]


class MuleGraphAgent(BaseStubAgent):
    role: AgentRole = "mule_graph"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        return [
            self._claim(
                (
                    "TAIG-style graph health check links two beneficiaries to prior Android "
                    "banking fraud clusters through shared UPI handles and device fingerprints."
                ),
                "taig.graph.neighborhood",
                "graph",
                "$.taig.neighborhood",
                0.84,
                summary="Shared campaign indicators.",
            )
        ]


class EvidenceValidatorAgent(BaseStubAgent):
    role: AgentRole = "evidence_validator"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        open_challenges = room.open_challenges
        if open_challenges:
            return [
                self._claim(
                    (
                        f"{len(open_challenges)} challenge remains open; final action should "
                        "stay provisional until the disputed confidence is resolved."
                    ),
                    "room.open_challenges",
                    "protocol",
                    "$.messages[*].attached_challenges",
                    0.96,
                    summary="Open challenge gate.",
                )
            ]
        return [
            self._claim(
                (
                    "Evidence bundle has a stable SHA-256 and every high-confidence claim "
                    "now cites at least one concrete source path."
                ),
                "bundle.integrity",
                "bundle",
                "$.sha256",
                0.93,
                summary="Integrity and citation check.",
            )
        ]

    async def respond_live(self, room: CaseRoom) -> list[EvidenceClaim]:
        fallback = self.respond(room)[0].claim_text
        prompt = _room_prompt(
            room,
            focus=(
                "Challenge overconfident or weakly cited claims. If open challenges exist, "
                "state whether they still block final convergence. If no challenge is needed, "
                "say why the evidence is sufficient."
            ),
        )
        text = await llm_claim(
            prompt,
            system=(
                "You are PARALLAX Evidence Validator Agent. Be skeptical, citation-driven, "
                "and concise. Prefer one actionable validation or challenge claim."
            ),
            role="evidence_validator",
            fallback=fallback,
        )
        return [
            self._claim(
                text,
                "room.validation",
                "protocol",
                "$.messages",
                _confidence_from_text(text, default=0.9),
                summary="LLM validation pass over room claims.",
            )
        ]


class LiabilityAgent(BaseStubAgent):
    role: AgentRole = "liability"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        return [
            self._claim(
                (
                    "Synthetic policy rules favor provisional credit: report arrived within "
                    "41 minutes and there is no customer credential-sharing admission."
                ),
                "synthetic.policy",
                "policy",
                "$.policy_context",
                0.8,
                summary="Demo-only policy context.",
            )
        ]


class LegalEvidenceAgent(BaseStubAgent):
    role: AgentRole = "legal_evidence"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        return [
            self._claim(
                (
                    "Legal packet should include bundle hash, APK identity, IOC list, "
                    "SMS-observation timeline, and Band transcript as chain-of-reasoning appendix."
                ),
                "legal.packet.requirements",
                "legal",
                "$.exports",
                0.86,
                summary="Cyber-cell evidence checklist.",
            )
        ]


class DecisionConvenorAgent(BaseStubAgent):
    role: AgentRole = "decision_convenor"

    def respond(self, room: CaseRoom) -> list[EvidenceClaim]:
        if room.open_challenges:
            confidence = 0.74
            text = (
                "Decision is provisional because at least one challenge is unresolved; "
                "human officer can approve temporary freeze and evidence preservation only."
            )
        else:
            confidence = 0.9
            text = (
                "All material challenges are resolved; recommend provisional credit, "
                "mule-account freeze request, and cyber-cell evidence export."
            )
        return [
            self._claim(
                text,
                "room.consensus",
                "decision",
                "$.messages",
                confidence,
                summary="Bounded adversarial convergence.",
            )
        ]

    async def respond_live(self, room: CaseRoom) -> list[EvidenceClaim]:
        fallback = self.respond(room)[0].claim_text
        prompt = _room_prompt(
            room,
            focus=(
                "Synthesize the room into a final or provisional action recommendation. "
                "Refuse final convergence if material challenges remain open."
            ),
        )
        text = await llm_claim(
            prompt,
            system=(
                "You are PARALLAX Decision Convenor Agent. Produce one bank-officer-facing "
                "decision claim grounded in the transcript. Do not overrule open challenges."
            ),
            role="synthesis",
            fallback=fallback,
        )
        return [
            self._claim(
                text,
                "room.decision",
                "decision",
                "$.messages",
                _confidence_from_text(text, default=0.86),
                summary="LLM synthesis of room state.",
            )
        ]


AGENTS: tuple[CaseAgent, ...] = (
    IntakeAgent(),
    DeviceCompromiseAgent(),
    TransactionTraceAgent(),
    MuleGraphAgent(),
    EvidenceValidatorAgent(),
    LiabilityAgent(),
    LegalEvidenceAgent(),
    DecisionConvenorAgent(),
)


def _format_claims(claims: list[EvidenceClaim]) -> str:
    return "\n".join(
        f"- [{claim.confidence:.2f}] {claim.claim_text} "
        f"({', '.join(ref.evidence_id for ref in claim.evidence_refs)})"
        for claim in claims
    )


def run_room_round(
    room: CaseRoom,
    *,
    adapter: BandAdapter | None = None,
    agents: tuple[CaseAgent, ...] = AGENTS,
) -> list[AgentMessage]:
    """Post one deterministic claim message from each agent."""
    adapter = adapter or BandAdapter()
    messages: list[AgentMessage] = []
    for agent in agents:
        claims = agent.respond(room)
        descriptor = agent.descriptor
        body = f"**{descriptor.display_name}**\n\n{_format_claims(claims)}"
        message = AgentMessage(
            message_type="evidence" if descriptor.role != "decision_convenor" else "decision",
            sender_id=descriptor.participant_ref,
            sender_type="agent",
            body=body,
            attached_claims=claims,
            bundle_sha256=room.evidence_bundle.sha256,
        )
        posted = adapter.post_message(
            room.band_room_id,
            sender_id=descriptor.participant_ref,
            body=body,
            mentions=[],
            metadata=message.model_dump(mode="json"),
        )
        message.message_id = str(posted.get("id", message.message_id))
        room.messages.append(message)
        messages.append(message)
        logger.debug("Posted deterministic Band message from %s", descriptor.role)
    return messages


async def llm_claim(
    prompt: str,
    system: str,
    *,
    role: str = "debate",
    fallback: str,
    temperature: float = 0.2,
) -> str:
    """Call the PARALLAX LLM gateway for one Band claim with deterministic fallback."""
    try:
        from parallax.ai.llm import llm

        text = await llm.complete_text(role, prompt, system=system, temperature=temperature)
    except Exception as exc:  # noqa: BLE001 - demo room must degrade gracefully
        logger.warning("Band LLM claim failed for role %s; using fallback: %s", role, exc)
        return fallback
    text = _clean_llm_text(text)
    return text or fallback


async def run_room_round_live(
    room: CaseRoom,
    *,
    adapter: BandAdapter | None = None,
    agents: tuple[CaseAgent, ...] = AGENTS,
) -> list[AgentMessage]:
    """Post one round, using LLM-backed responses for live-enabled agents."""
    adapter = adapter or BandAdapter()
    messages: list[AgentMessage] = []
    for agent in agents:
        respond_live = getattr(agent, "respond_live", None)
        claims = await respond_live(room) if respond_live else agent.respond(room)
        descriptor = agent.descriptor
        body = f"**{descriptor.display_name}**\n\n{_format_claims(claims)}"
        message = AgentMessage(
            message_type="evidence" if descriptor.role != "decision_convenor" else "decision",
            sender_id=descriptor.participant_ref,
            sender_type="agent",
            body=body,
            attached_claims=claims,
            bundle_sha256=room.evidence_bundle.sha256,
        )
        posted = adapter.post_message(
            room.band_room_id,
            sender_id=descriptor.participant_ref,
            body=body,
            mentions=[],
            metadata=message.model_dump(mode="json"),
        )
        message.message_id = str(posted.get("id", message.message_id))
        room.messages.append(message)
        messages.append(message)
    return messages


def _clean_llm_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith(("text", "markdown")):
            text = text.split("\n", 1)[-1].strip()
    lines = [line.strip(" -") for line in text.splitlines() if line.strip()]
    return " ".join(lines)[:900]


def _confidence_from_text(text: str, *, default: float) -> float:
    lowered = text.lower()
    if any(word in lowered for word in ("provisional", "uncertain", "sparse", "insufficient")):
        return min(default, 0.74)
    if any(word in lowered for word in ("confirmed", "strong", "corroborated", "resolved")):
        return max(default, 0.88)
    return default


def _room_prompt(room: CaseRoom, *, focus: str) -> str:
    messages = [
        {
            "type": message.message_type,
            "sender": message.sender_id,
            "body": message.body[:900],
            "claims": [
                {
                    "claim_id": claim.claim_id,
                    "confidence": claim.confidence,
                    "text": claim.claim_text,
                    "evidence_refs": [ref.model_dump(mode="json") for ref in claim.evidence_refs],
                }
                for claim in message.attached_claims[:4]
            ],
            "challenges": [
                challenge.model_dump(mode="json") for challenge in message.attached_challenges[:4]
            ],
        }
        for message in room.messages[-12:]
    ]
    import json

    return "\n".join(
        [
            focus,
            "",
            "CASE:",
            json.dumps(
                {
                    "case_id": room.case_id,
                    "submission_id": room.submission_id,
                    "band_room_id": room.band_room_id,
                    "bundle": room.evidence_bundle.model_dump(mode="json"),
                    "open_challenge_ids": [c.challenge_id for c in room.open_challenges],
                },
                indent=2,
            ),
            "",
            "RECENT TRANSCRIPT:",
            json.dumps(messages, indent=2),
            "",
            "Return exactly one short claim sentence. No markdown table.",
        ]
    )


def add_challenge(
    room: CaseRoom,
    *,
    target_claim_id: str,
    reason: str,
    severity: str = "major",
    adapter: BandAdapter | None = None,
) -> AgentMessage:
    """Post the validator's challenge against a prior claim."""
    adapter = adapter or BandAdapter()
    validator = agent_by_role("evidence_validator")
    target_agent = agent_by_role("device_compromise").participant_ref
    challenge = Challenge(
        target_claim_id=target_claim_id,
        challenger_id=validator.participant_ref,
        reason=reason,
        severity=severity,  # type: ignore[arg-type]
    )
    body = f"Challenge {challenge.challenge_id}: {reason}"
    message = AgentMessage(
        message_type="challenge",
        sender_id=validator.participant_ref,
        sender_type="agent",
        body=body,
        mentions=[target_agent],
        attached_challenges=[challenge],
        bundle_sha256=room.evidence_bundle.sha256,
    )
    posted = adapter.post_message(
        room.band_room_id,
        sender_id=validator.participant_ref,
        body=body,
        mentions=[target_agent],
        metadata=message.model_dump(mode="json"),
    )
    message.message_id = str(posted.get("id", message.message_id))
    room.messages.append(message)
    return message


def resolve_challenge(
    room: CaseRoom,
    challenge_id: str,
    *,
    accepted: bool,
    resolution_text: str,
    adapter: BandAdapter | None = None,
) -> AgentMessage:
    """Resolve a challenge and post the resolution to the room."""
    adapter = adapter or BandAdapter()
    resolver = agent_by_role("device_compromise")
    target: Challenge | None = None
    for challenge in room.open_challenges:
        if challenge.challenge_id == challenge_id:
            target = challenge
            break
    if target is None:
        raise ValueError(f"Open challenge not found: {challenge_id}")

    target.status = "accepted" if accepted else "rejected"
    target.resolution_text = resolution_text
    target.resolved_by = resolver.participant_ref
    from parallax.agents.band.room_protocol import utc_now

    target.resolved_at = utc_now()
    body = f"Resolved {challenge_id}: {resolution_text}"
    message = AgentMessage(
        message_type="challenge",
        sender_id=resolver.participant_ref,
        sender_type="agent",
        body=body,
        mentions=[target.challenger_id],
        attached_challenges=[target],
        bundle_sha256=room.evidence_bundle.sha256,
    )
    posted = adapter.post_message(
        room.band_room_id,
        sender_id=resolver.participant_ref,
        body=body,
        mentions=[target.challenger_id],
        metadata=message.model_dump(mode="json"),
    )
    message.message_id = str(posted.get("id", message.message_id))
    room.messages.append(message)
    return message


def build_action_packet(room: CaseRoom) -> ActionPacket:
    """Create a deterministic human-officer action packet from room state."""
    unresolved = [challenge.challenge_id for challenge in room.open_challenges]
    status = "provisional" if unresolved else "final"
    packet = ActionPacket(
        status=status,
        summary=(
            "PARALLAX x Band agents find a likely APK-led account takeover with "
            "mule-account fan-out and preserved evidence bundle integrity."
        ),
        recommended_actions=[
            "Grant provisional credit subject to bank policy review.",
            "Request freeze on linked mule beneficiaries.",
            "Export cyber-cell packet with APK, IOCs, bundle hash, and transcript.",
        ],
        unresolved_challenge_ids=unresolved,
    )
    room.final_action_packet = packet
    room.status = "provisional" if unresolved else "converged"
    return packet
