"""Structured I/O contracts for the AI Reasoning Cortex.

Every cortex agent returns one of these Pydantic models. They are deliberately
permissive (``extra="ignore"`` + safe defaults) because the upstream producer
is an LLM: a missing or extra field must never crash the pipeline. Downstream
consumers (debate layer, synthesis, graph population, report generator) depend
on these shapes, so they are the single source of truth for the cortex.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
Verdict = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAN", "UNCERTAIN"]

_INTENTS = Literal[
    "banking_trojan",
    "spyware",
    "adware",
    "dropper",
    "ransomware",
    "sms_fraud",
    "clean",
    "uncertain",
]


class ClassRole(BaseModel):
    model_config = ConfigDict(extra="ignore")
    class_name: str = ""
    role: str = ""
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class MethodIntent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    method: str = ""
    intent: str = ""
    sources: list[str] = Field(default_factory=list)
    sinks: list[str] = Field(default_factory=list)


class CodeInterpreterOutput(BaseModel):
    """Static code understanding — the RE Workbench's semantic verdict."""

    model_config = ConfigDict(extra="ignore")
    intent_classification: _INTENTS = "uncertain"
    risk_level: RiskLevel = "LOW"
    confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)
    attck_techniques: list[str] = Field(default_factory=list)
    class_roles: list[ClassRole] = Field(default_factory=list)
    method_intents: list[MethodIntent] = Field(default_factory=list)
    attack_flow: list[str] = Field(default_factory=list)
    reasoning: str = ""


class BehaviorPhase(BaseModel):
    model_config = ConfigDict(extra="ignore")
    phase: str = "reconnaissance"
    actions: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    risk: RiskLevel = "LOW"


class BehaviorAnalystOutput(BaseModel):
    """Runtime behavior understanding from the dynamic observation timeline."""

    model_config = ConfigDict(extra="ignore")
    kill_chain: list[BehaviorPhase] = Field(default_factory=list)
    overall_narrative: str = ""
    risk_level: RiskLevel = "LOW"
    confidence: float = 0.0
    network_iocs: list[str] = Field(default_factory=list)
    observed_behaviors: list[str] = Field(default_factory=list)


class CampaignLink(BaseModel):
    model_config = ConfigDict(extra="ignore")
    campaign: str = ""
    similarity: float = 0.0


class IntelCorrelatorOutput(BaseModel):
    """ATT&CK mapping + attribution + cross-sample correlation."""

    model_config = ConfigDict(extra="ignore")
    attck_techniques: list[str] = Field(default_factory=list)
    family_attribution: str = ""
    family_confidence: float = 0.0
    threat_actor: str = ""
    actor_confidence: float = 0.0
    campaign_links: list[CampaignLink] = Field(default_factory=list)
    related_submissions: list[str] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0


class ScreenshotFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    screenshot_key: str = ""
    description: str = ""
    brand_detected: str = ""
    is_phishing: bool = False
    brand_similarity_score: float = 0.0
    overlay_detected: bool = False


class VisualIntelOutput(BaseModel):
    """Aggregate visual verdict over captured screenshots."""

    model_config = ConfigDict(extra="ignore")
    findings: list[ScreenshotFinding] = Field(default_factory=list)
    brand_impersonation: str = ""
    brand_impersonation_score: float = 0.0
    phishing_detected: bool = False
    overlay_attack_detected: bool = False
    confidence: float = 0.0


class Contradiction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    between: list[str] = Field(default_factory=list)
    description: str = ""
    severity: float = 0.0
    resolution: str = ""


class DebateResult(BaseModel):
    """Output of the debate layer — contradictions surfaced and resolved."""

    model_config = ConfigDict(extra="ignore")
    contradictions: list[Contradiction] = Field(default_factory=list)
    evasion_suspected: bool = False
    confidence_modifier: float = 0.0  # added to the final confidence
    notes: str = ""


class RiskComponents(BaseModel):
    """Layer A evidence-score components (each 0.0-1.0)."""

    model_config = ConfigDict(extra="ignore")
    permission_abuse: float = 0.0
    behavioral_indicators: float = 0.0
    code_intent_risk: float = 0.0
    network_exfiltration: float = 0.0
    code_obfuscation: float = 0.0
    brand_impersonation: float = 0.0
    campaign_association: float = 0.0
    attribution_confidence: float = 0.0


class RiskScore(BaseModel):
    """Two-layer risk score. Layer A is live; Layer B (calibration) is wired
    but uses an identity calibration until labeled corpora are available."""

    model_config = ConfigDict(extra="ignore")
    evidence_score: float = 0.0  # 0-100, deterministic weighted sum
    components: RiskComponents = Field(default_factory=RiskComponents)
    weights: dict[str, float] = Field(default_factory=dict)
    calibrated_score: float = 0.0  # 0-100
    confidence_interval: float = 0.0  # +/- points
    verdict: Verdict = "LOW"


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    action: str = ""
    approval_mode: Literal["SUGGEST", "APPROVED", "AUTO_LOW_RISK", "HELD"] = "SUGGEST"
    rationale: str = ""


class IRTEntry(BaseModel):
    """One line of the clean external Investigation Reasoning Trace."""

    model_config = ConfigDict(extra="ignore")
    status: Literal["CONFIRMED", "UNRESOLVED", "REJECTED"] = "CONFIRMED"
    claim: str = ""
    explanation: str = ""
    evidence: list[str] = Field(default_factory=list)


class CortexResult(BaseModel):
    """The complete output of the reasoning cortex for one submission."""

    model_config = ConfigDict(extra="ignore")
    submission_id: str = ""
    sha256: str = ""
    verdict: Verdict = "UNCERTAIN"
    risk: RiskScore = Field(default_factory=RiskScore)

    executive_summary: str = ""
    technical_findings: list[str] = Field(default_factory=list)
    attck_techniques: list[str] = Field(default_factory=list)
    kill_chain: list[BehaviorPhase] = Field(default_factory=list)
    iocs: dict[str, list[str]] = Field(default_factory=dict)
    irt: list[IRTEntry] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)

    # Per-agent outputs retained for audit and graph population.
    code_interpreter: CodeInterpreterOutput | None = None
    behavior_analyst: BehaviorAnalystOutput | None = None
    intel_correlator: IntelCorrelatorOutput | None = None
    visual: VisualIntelOutput | None = None
    debate: DebateResult | None = None

    agent_errors: dict[str, str] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
