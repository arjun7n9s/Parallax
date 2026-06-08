from unittest.mock import AsyncMock, MagicMock

import pytest

from parallax.ai.hypothesis.engine import HypothesisEngine


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
