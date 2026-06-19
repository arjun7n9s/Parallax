"""Tests for PARALLAX x Band transcript exports."""

from __future__ import annotations

import textwrap

from parallax.agents.band.agents import (
    add_challenge,
    build_action_packet,
    resolve_challenge,
    run_room_round,
)
from parallax.agents.band.band_adapter import BandAdapter, BandConfig
from parallax.agents.band.room_protocol import CaseRoom, EvidenceBundleRef
from parallax.agents.band.transcript_export import export_markdown, export_pdf


def _room() -> CaseRoom:
    return CaseRoom(
        case_id="CASE-FR-2026-00421",
        submission_id="sub-1",
        band_room_id="room-1",
        evidence_bundle=EvidenceBundleRef(
            url="https://example.test/bundle.json",
            bucket="parallax-case-bundles",
            object_name="submissions/sub-1/bundle.json",
            sha256="d" * 64,
            byte_size=512,
        ),
    )


def _completed_room() -> CaseRoom:
    adapter = BandAdapter(BandConfig(mode="mock"))
    room = _room()
    first_round = run_room_round(room, adapter=adapter)
    challenge_message = add_challenge(
        room,
        target_claim_id=first_round[1].attached_claims[0].claim_id,
        reason="Dynamic corroboration required.",
        adapter=adapter,
    )
    resolve_challenge(
        room,
        challenge_message.attached_challenges[0].challenge_id,
        accepted=True,
        resolution_text="Dynamic SMS timeline corroborates static permissions.",
        adapter=adapter,
    )
    run_room_round(room, adapter=adapter)
    build_action_packet(room)
    return room


def test_export_markdown_has_judge_facing_sections():
    markdown = export_markdown(_completed_room())

    assert "## Case Header" in markdown
    assert "## Agent Roster And Final Claims" in markdown
    assert "## Challenges And Resolutions" in markdown
    assert "## Verbatim Transcript" in markdown
    assert "## Final Action Packet" in markdown
    assert "Submission SHA-256" in markdown
    assert "Dynamic SMS timeline corroborates static permissions." in markdown
    assert "Grant provisional credit" in markdown


def test_export_pdf_uses_supplied_converter(tmp_path):
    markdown_path = tmp_path / "transcript.md"
    pdf_path = tmp_path / "transcript.pdf"
    converter_path = tmp_path / "md_to_pdf.py"
    markdown_path.write_text(
        "# Demo\n\n| A | B |\n| --- | --- |\n| one | two |\n", encoding="utf-8"
    )
    converter_path.write_text(
        textwrap.dedent(
            """
            def parse_md_table(lines, idx):
                return ([["A", "B"], ["one", "two"]], idx + 3)

            class HackathonPDF:
                def __init__(self):
                    self.events = []
                def set_title(self, text): self.events.append(("title", text))
                def set_author(self, text): self.events.append(("author", text))
                def h1(self, text): self.events.append(("h1", text))
                def h2(self, text): self.events.append(("h2", text))
                def h3(self, text): self.events.append(("h3", text))
                def h4(self, text): self.events.append(("h4", text))
                def rule(self): self.events.append(("rule", ""))
                def add_table(self, rows): self.events.append(("table", rows))
                def numbered(self, text, n, level=0): self.events.append(("numbered", text))
                def bullet(self, text, level=0): self.events.append(("bullet", text))
                def para(self, text): self.events.append(("para", text))
                def ln(self, amount): self.events.append(("ln", amount))
                def code_block(self, code): self.events.append(("code", code))
                def output(self, path):
                    from pathlib import Path
                    Path(path).write_bytes(b"%PDF-test")
            """
        ),
        encoding="utf-8",
    )

    result = export_pdf(markdown_path, pdf_path, converter_path=converter_path)

    assert result == pdf_path
    assert pdf_path.read_bytes() == b"%PDF-test"
