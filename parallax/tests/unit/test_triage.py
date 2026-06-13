from unittest.mock import AsyncMock, patch

import pytest

from parallax.ai.agents.triage import run_llm_triage


@pytest.mark.asyncio
@patch("parallax.ai.agents.triage.llm.complete_json", new_callable=AsyncMock)
async def test_run_triage_success(mock_generate_json):
    """Test successful triage run."""
    mock_generate_json.return_value = {
        "pre_score": 85.0,
        "priority": "high",
        "initial_hypotheses": [
            {
                "claim": "The app requests suspicious permissions.",
                "category": "static",
                "expose_in_irt": True,
                "irt_label": "Suspicious permissions detected.",
                "evidence_citations": ["permission_internet", "permission_read_sms"],
                "initial_confidence": 0.8,
            }
        ],
    }

    metadata = {"package_name": "com.test.app", "app_name": "Test App"}

    result = await run_llm_triage(metadata)

    assert result["pre_score"] == 85.0
    assert result["priority"] == "high"
    assert len(result["initial_hypotheses"]) == 1

    # Verify that the generate_json was called
    mock_generate_json.assert_called_once()
