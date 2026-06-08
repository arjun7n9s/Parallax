import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from parallax.ai.hypothesis.engine import HypothesisEngine
from parallax.core.models import Hypothesis


@pytest.mark.asyncio
async def test_seed_initial_hypotheses():
    """Test seeding initial hypotheses into the database."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    engine = HypothesisEngine(db=mock_db)

    triage_data = {
        "initial_hypotheses": [
            {
                "claim": "Test claim",
                "category": "static",
                "initial_confidence": 0.75,
                "expose_in_irt": True,
                "irt_label": "Suspicious behavior found.",
            }
        ]
    }

    records = await engine.seed_initial_hypotheses(
        submission_id=uuid.uuid4(), sha256="fake_sha256_hash", triage_data=triage_data
    )

    assert len(records) == 1
    assert records[0].claim == "Test claim"
    assert records[0].category == "static"
    assert records[0].initial_confidence == 0.75

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    assert mock_db.refresh.call_count == len(records)


@pytest.mark.asyncio
async def test_process_static_results_yara_match():
    """Test that a YARA match successfully upgrades a PENDING hypothesis to CONFIRMED."""
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    sub_id = uuid.uuid4()

    # Setup an existing pending hypothesis
    h = Hypothesis(
        hypothesis_id="HYP-1234",
        submission_id=sub_id,
        claim="App is a banking trojan",
        status="PENDING",
    )

    # Mock db.execute to return the hypothesis
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [h]
    mock_db.execute.return_value = mock_result

    engine = HypothesisEngine(db=mock_db)

    artifact = {
        "yara_matches": [
            {"rule": "Android_BankingTrojan_Generic", "meta": {"category": "Banking Trojan"}}
        ],
        "static_features": {"permissions": []},
    }

    await engine.process_static_results(sub_id, artifact)

    assert h.status == "CONFIRMED"
    assert h.final_confidence == 0.95
    assert "Confirmed by YARA rule: Android_BankingTrojan_Generic" in h.status_reason
    mock_db.commit.assert_called_once()
