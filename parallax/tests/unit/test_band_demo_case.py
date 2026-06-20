"""Tests for the deterministic Band demo case runner."""

from __future__ import annotations

import json

import pytest

from parallax.agents.band.demo_case import run_demo
from parallax.agents.band.transcript_export import default_pdf_converter_path


@pytest.mark.asyncio
async def test_run_demo_exports_transcript_artifacts(tmp_path):
    out = await run_demo("demo-submission-001", output_dir=str(tmp_path))

    transcript = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
    action_packet = json.loads((out / "action_packet.json").read_text(encoding="utf-8"))
    markdown = (out / "transcript.md").read_text(encoding="utf-8")

    assert transcript["case_id"] == "CASE-FR-2026-00421"
    assert transcript["status"] == "converged"
    assert action_packet["status"] == "final"
    assert action_packet["unresolved_challenge_ids"] == []
    assert "PARALLAX x Band Case Transcript" in markdown
    # PDF export is best-effort: only assert it when a converter is available
    # (CI runners have no PDF toolchain, so only the markdown transcript exists).
    if default_pdf_converter_path().exists():
        assert (out / "transcript.pdf").exists()
