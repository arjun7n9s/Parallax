"""Band room transcript and PDF exporter. Part of PARALLAX x Band integration. See Claude/band_plan.md."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from types import ModuleType

from parallax.agents.band.agents import AGENT_ROSTER
from parallax.agents.band.room_protocol import AgentMessage, CaseRoom, Challenge


def export_markdown(case_room: CaseRoom) -> str:
    """Render a judge-facing audit transcript for demo artifacts."""
    lines = [
        f"# PARALLAX x Band Case Transcript - {case_room.case_id}",
        "",
        "## Case Header",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Case ID | `{_escape_table(case_room.case_id)}` |",
        f"| Submission ID | `{_escape_table(case_room.submission_id)}` |",
        f"| Submission SHA-256 | `{case_room.evidence_bundle.sha256}` |",
        f"| Snapshot timestamp | `{case_room.evidence_bundle.created_at.isoformat()}` |",
        f"| Evidence stale as of | `{case_room.evidence_bundle.stale_as_of.isoformat()}` |",
        f"| Bundle URL | `{_escape_table(case_room.evidence_bundle.url)}` |",
        f"| Band room | `{_escape_table(case_room.band_room_id)}` |",
        "",
        "## Agent Roster And Final Claims",
        "",
        "| Agent | Handle / ID | Final claim | Confidence |",
        "| --- | --- | --- | --- |",
    ]

    for agent in AGENT_ROSTER:
        final_claim = next(
            (
                claim
                for message in reversed(case_room.messages)
                if message.sender_id == agent.participant_ref
                for claim in reversed(message.attached_claims)
            ),
            None,
        )
        claim_text = _short(final_claim.claim_text if final_claim else "No final claim posted.")
        confidence = f"{final_claim.confidence:.2f}" if final_claim else "-"
        lines.append(
            "| "
            f"{_escape_table(agent.display_name)} | "
            f"`{_escape_table(agent.participant_ref)}` | "
            f"{_escape_table(claim_text)} | "
            f"{confidence} |"
        )

    lines.extend(
        [
            "",
            "## Challenges And Resolutions",
            "",
            "| Challenge ID | Target claim | Challenger | Severity | Status | Resolution |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    challenges = _challenge_rows(case_room.messages)
    if challenges:
        for challenge, _message in challenges:
            lines.append(
                "| "
                f"`{challenge.challenge_id}` | "
                f"`{_escape_table(challenge.target_claim_id)}` | "
                f"`{_escape_table(challenge.challenger_id)}` | "
                f"{challenge.severity} | "
                f"{challenge.status} | "
                f"{_escape_table(_short(challenge.resolution_text or challenge.reason))} |"
            )
    else:
        lines.append("| - | - | - | - | - | No challenges raised. |")

    lines.extend(["", "## Verbatim Transcript", ""])
    for message in case_room.messages:
        mentions = ", ".join(message.mentions) or "-"
        lines.extend(
            [
                f"### {message.timestamp.isoformat()} - {message.sender_id}",
                "",
                f"- Type: `{message.message_type}`",
                f"- Mentions: {mentions}",
                "",
                message.body,
                "",
            ]
        )
        if message.attached_challenges:
            lines.extend(["Attached challenges:", ""])
            for challenge in message.attached_challenges:
                resolution = challenge.resolution_text or "Unresolved"
                lines.extend(
                    [
                        (
                            f"- `{challenge.challenge_id}` targets `{challenge.target_claim_id}`: "
                            f"{challenge.reason} Status: `{challenge.status}`. Resolution: {resolution}"
                        ),
                        "",
                    ]
                )

    lines.extend(["## Final Action Packet", ""])
    packet = case_room.final_action_packet
    if packet is None:
        lines.append("No final action packet has been issued.")
    else:
        lines.extend(
            [
                f"- Decision ID: `{packet.decision_id}`",
                f"- Status: `{packet.status}`",
                f"- Created at: `{packet.created_at.isoformat()}`",
                f"- Summary: {packet.summary}",
                "",
                "| Recommended action |",
                "| --- |",
            ]
        )
        for action in packet.recommended_actions:
            lines.append(f"| {_escape_table(action)} |")
        lines.extend(["", "| Unresolved challenge |", "| --- |"])
        for challenge_id in packet.unresolved_challenge_ids or ["None"]:
            lines.append(f"| `{_escape_table(challenge_id)}` |")

    return "\n".join(lines)


def export_pdf(
    markdown_path: str | Path,
    pdf_path: str | Path,
    *,
    converter_path: str | Path | None = None,
) -> Path:
    """Render transcript markdown to PDF using the hackathon submission renderer."""
    markdown_path = Path(markdown_path)
    pdf_path = Path(pdf_path)
    converter = Path(converter_path) if converter_path else default_pdf_converter_path()
    if not converter.exists():
        raise FileNotFoundError(f"Markdown-to-PDF converter not found: {converter}")

    module = _load_converter(converter)
    pdf = module.HackathonPDF()
    pdf.set_title("PARALLAX x Band Case Transcript")
    pdf.set_author("PARALLAX Team")
    _render_markdown_with_converter(pdf, markdown_path, module)
    pdf.output(str(pdf_path))
    return pdf_path


def default_pdf_converter_path() -> Path:
    """Return the expected hackathon submission markdown-to-PDF converter path."""
    return Path(__file__).resolve().parents[4] / "hackathon-submission" / "md_to_pdf.py"


def _escape_table(value: object) -> str:
    text = str(value or "").replace("\n", " ").replace("|", "\\|")
    return re.sub(r"\s+", " ", text).strip()


def _short(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _challenge_rows(messages: list[AgentMessage]) -> list[tuple[Challenge, AgentMessage]]:
    return [
        (challenge, message)
        for message in messages
        for challenge in message.attached_challenges
        if message.sender_id == challenge.challenger_id
    ]


def _load_converter(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("parallax_band_md_to_pdf", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import markdown-to-PDF converter: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _render_markdown_with_converter(pdf, markdown_path: Path, converter: ModuleType) -> None:
    lines = markdown_path.read_text(encoding="utf-8").split("\n")
    in_code = False
    code_buf: list[str] = []
    numbered_counters: dict[int, int] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()

        if s.startswith("```"):
            if in_code:
                pdf.code_block("\n".join(code_buf))
                code_buf = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if s.startswith("# "):
            pdf.h1(s[2:])
        elif s.startswith("## "):
            pdf.h2(s[3:])
            numbered_counters = {0: 0}
        elif s.startswith("### "):
            pdf.h3(s[4:])
            numbered_counters[1] = 0
        elif s.startswith("#### "):
            pdf.h4(s[5:])
        elif s == "---":
            pdf.rule()
        elif (
            s.startswith("|")
            and i + 1 < len(lines)
            and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[i + 1])
        ):
            rows, end_idx = converter.parse_md_table(lines, i)
            if rows:
                pdf.add_table(rows)
                i = end_idx
                continue
        elif re.match(r"^\s*\d+\.\s+", line):
            indent = (len(line) - len(line.lstrip())) // 2
            numbered_counters.setdefault(indent, 0)
            numbered_counters[indent] += 1
            text = re.sub(r"^\s*\d+\.\s+", "", line)
            pdf.numbered(text, numbered_counters[indent], level=indent // 2)
        elif re.match(r"^\s*[-*]\s+", line):
            indent = (len(line) - len(line.lstrip())) // 2
            text = re.sub(r"^\s*[-*]\s+", "", line)
            pdf.bullet(text, level=indent)
        elif not s:
            pdf.ln(2)
        else:
            pdf.para(line)

        i += 1
