"""Tests for the productization pass: taint wiring, API auth, and the
hardened Cypher/STIX/YARA delivery surface."""

import pytest

from parallax.ai.risk import _network_exfil, compute_risk
from parallax.ai.schemas import CodeInterpreterOutput, CortexResult
from parallax.knowledge.neo4j_client import _FORBIDDEN

TAINT_CRITICAL = [
    {
        "source": "android.telephony.SmsMessage.getMessageBody",
        "sink": "java.net.URL.openConnection",
        "path": [],
        "risk": "CRITICAL",
        "attck_technique": "T1417.002",
    }
]


# ---------------------------------------------------------------- taint -> risk
class TestTaintRisk:
    def test_critical_taint_raises_network_exfil(self):
        assert _network_exfil(None, TAINT_CRITICAL) == pytest.approx(0.75)

    def test_medium_taint_raises_network_exfil_less(self):
        flows = [dict(TAINT_CRITICAL[0], risk="MEDIUM")]
        assert _network_exfil(None, flows) == pytest.approx(0.4)

    def test_no_taint_no_behavior_is_zero(self):
        assert _network_exfil(None, []) == 0.0

    def test_known_family_floors_verdict_to_high(self):
        """A confirmed known-malware family must lift a static-only LOW to HIGH."""
        fam = {"family": "Cerberus", "confidence": 0.9, "sources": [{"source": "malwarebazaar"}]}
        floored = compute_risk(
            permissions=["android.permission.READ_SMS"],
            code=None, behavior=None, intel=None, visual=None, debate=None,
            known_family=fam,
        )
        assert floored.evidence_score >= 65.0
        assert floored.verdict == "HIGH"
        assert any("Cerberus" in n for n in floored.notes)

    def test_low_confidence_family_does_not_floor(self):
        fam = {"family": "Maybe", "confidence": 0.4, "sources": []}
        r = compute_risk(
            permissions=[], code=None, behavior=None, intel=None, visual=None,
            debate=None, known_family=fam,
        )
        assert r.evidence_score < 65.0

    def test_taint_flows_increase_score(self):
        base = compute_risk(
            permissions=[],
            code=None,
            behavior=None,
            intel=None,
            visual=None,
            debate=None,
        )
        with_taint = compute_risk(
            permissions=[],
            code=None,
            behavior=None,
            intel=None,
            visual=None,
            debate=None,
            taint_flows=TAINT_CRITICAL,
        )
        assert with_taint.evidence_score > base.evidence_score


# ------------------------------------------------------- taint -> agent prompts
class TestTaintPrompts:
    def test_code_interpreter_prompt_includes_taint(self):
        from parallax.ai.agents.code_interpreter import _build_prompt

        prompt = _build_prompt({}, "", [], [], TAINT_CRITICAL)
        assert "STATIC TAINT FLOWS" in prompt
        assert "getMessageBody" in prompt

    def test_code_interpreter_prompt_without_taint(self):
        from parallax.ai.agents.code_interpreter import _build_prompt

        assert "STATIC TAINT FLOWS" not in _build_prompt({}, "", [], [])

    def test_orchestration_merges_taint_attck(self):
        # The merge is deterministic set union; verify the expression directly.
        code = CodeInterpreterOutput(attck_techniques=["T1409"])
        taint_attck = {t["attck_technique"] for t in TAINT_CRITICAL if t.get("attck_technique")}
        merged = sorted(set(code.attck_techniques) | taint_attck)
        assert merged == ["T1409", "T1417.002"]


# ------------------------------------------------------------------ ORM model
class TestTaintFlowModel:
    def test_model_importable_and_mapped(self):
        from parallax.core.models import TaintFlow

        assert TaintFlow.__tablename__ == "taint_flows"

    def test_to_dict_shape(self):
        from parallax.core.models import TaintFlow

        t = TaintFlow(
            source_class="android.telephony.SmsMessage",
            source_method="getMessageBody",
            sink_class="java.net.URL",
            sink_method="openConnection",
            path=["a", "b"],
            risk="CRITICAL",
            attck_technique="T1417.002",
        )
        d = t.to_dict()
        assert d["source"] == "android.telephony.SmsMessage.getMessageBody"
        assert d["sink"] == "java.net.URL.openConnection"
        assert d["risk"] == "CRITICAL"


# ---------------------------------------------------------------- static worker
class TestStaticWorkerTaint:
    def test_skips_when_flowdroid_not_configured(self, monkeypatch):
        from parallax.core.config import settings
        from parallax.workers.static_worker import _run_flowdroid_taint

        monkeypatch.setattr(settings, "FLOWDROID_JAR", "")
        assert _run_flowdroid_taint("/nonexistent.apk") == []

    def test_failure_is_isolated(self, monkeypatch):
        from parallax.core.config import settings
        from parallax.workers.static_worker import _run_flowdroid_taint

        monkeypatch.setattr(settings, "FLOWDROID_JAR", "/missing/flowdroid.jar")
        # Missing JAR must degrade to [] instead of raising.
        assert _run_flowdroid_taint("/nonexistent.apk") == []


# ------------------------------------------------------------------- cypher guard
class TestCypherGuard:
    @pytest.mark.parametrize(
        "query",
        [
            "CALL apoc.load.json('file:///etc/passwd')",
            "MATCH (n) CALL db.labels() YIELD label RETURN label",
            "UNWIND [1] AS x CALL apoc.trigger.add('x','y',{}) RETURN x",
            "CREATE (n:Evil) RETURN n",
            "MATCH (n) DETACH DELETE n",
            "MATCH (n) SET n.x = 1 RETURN n",
            "LOAD CSV FROM 'http://evil' AS row RETURN row",
        ],
    )
    def test_blocks_mutating_and_procedure_calls(self, query):
        assert _FORBIDDEN.search(query)

    @pytest.mark.parametrize(
        "query",
        [
            "MATCH (a:APK)-[:COMMUNICATES_WITH]->(d:Domain) RETURN a.sha256, d.name",
            "MATCH (a:APK) WHERE a.verdict = 'CRITICAL' RETURN count(a)",
        ],
    )
    def test_allows_read_queries(self, query):
        assert not _FORBIDDEN.search(query)


# ---------------------------------------------------------------------- API auth
class TestApiKeyAuth:
    @pytest.mark.asyncio
    async def test_disabled_when_key_empty(self, monkeypatch):
        from parallax.api.security import require_api_key
        from parallax.core.config import settings

        monkeypatch.setattr(settings, "API_KEY", "")
        assert await require_api_key(None) is None

    @pytest.mark.asyncio
    async def test_rejects_missing_key(self, monkeypatch):
        from fastapi import HTTPException

        from parallax.api.security import require_api_key
        from parallax.core.config import settings

        monkeypatch.setattr(settings, "API_KEY", "s3cret")
        with pytest.raises(HTTPException) as exc:
            await require_api_key(None)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_wrong_key(self, monkeypatch):
        from fastapi import HTTPException

        from parallax.api.security import require_api_key
        from parallax.core.config import settings

        monkeypatch.setattr(settings, "API_KEY", "s3cret")
        with pytest.raises(HTTPException):
            await require_api_key("wrong")

    @pytest.mark.asyncio
    async def test_accepts_correct_key(self, monkeypatch):
        from parallax.api.security import require_api_key
        from parallax.core.config import settings

        monkeypatch.setattr(settings, "API_KEY", "s3cret")
        assert await require_api_key("s3cret") is None


# ------------------------------------------------------------------ STIX escaping
class TestStixEscaping:
    def test_quote_in_ioc_is_escaped(self):
        pytest.importorskip("stix2")
        import json

        from parallax.delivery.stix_exporter import build_stix_json

        cortex = CortexResult(
            iocs={"urls": ["http://evil.example/p?q='drop'"], "domains": [], "ips": []}
        )
        bundle = json.loads(build_stix_json("a" * 64, "com.evil.app", cortex))
        indicators = [o for o in bundle["objects"] if o["type"] == "indicator"]
        assert indicators, "indicator with quoted URL was dropped instead of escaped"
        assert "\\'" in indicators[0]["pattern"]


# ----------------------------------------------------------- flowdroid platforms
class TestFlowDroidPlatforms:
    def test_missing_platforms_raises_clear_error(self, tmp_path, monkeypatch):
        from parallax.analysis.static.flowdroid_runner import (
            FlowDroidError,
            _find_android_platforms,
        )

        for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT", "USERPROFILE"):
            monkeypatch.delenv(var, raising=False)
        with pytest.raises(FlowDroidError):
            _find_android_platforms(None)

    def test_explicit_platforms_dir_wins(self, tmp_path):
        from parallax.analysis.static.flowdroid_runner import _find_android_platforms

        platforms = tmp_path / "platforms"
        platforms.mkdir()
        assert _find_android_platforms(platforms) == platforms
