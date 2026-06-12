"""Investigation report generation (HTML + PDF).

Produces the evidence-first report described in the vision: executive summary,
two-layer risk score, fraud attack chain, the clean Investigation Reasoning
Trace (IRT), evidence, ATT&CK mapping and approval-tagged recommendations.

HTML is the primary, always-available format (self-contained, inline CSS). A
PDF is rendered with reportlab (pure-Python, cross-platform) since WeasyPrint
requires native GTK libraries not present on all hosts.
"""

from __future__ import annotations

import html
import io
import logging

from parallax.ai.schemas import CortexResult

logger = logging.getLogger(__name__)

_VERDICT_COLOR = {
    "CRITICAL": "#b00020",
    "HIGH": "#e65100",
    "MEDIUM": "#f9a825",
    "LOW": "#2e7d32",
    "CLEAN": "#2e7d32",
    "UNCERTAIN": "#616161",
}


def _esc(text: str) -> str:
    return html.escape(str(text or ""))


def render_html(sha256: str, package: str, cortex: CortexResult, fraud_chain: list[dict]) -> str:
    color = _VERDICT_COLOR.get(cortex.verdict, "#616161")
    risk = cortex.risk

    def li(items):
        return "".join(f"<li>{_esc(i)}</li>" for i in items) or "<li><em>none</em></li>"

    irt_rows = ""
    for e in cortex.irt:
        badge = {"CONFIRMED": "✅", "UNRESOLVED": "⚠️", "REJECTED": "❌"}.get(e.status, "•")
        irt_rows += (
            f"<div class='irt'><b>{badge} {_esc(e.status)}: {_esc(e.claim)}</b>"
            f"<p>{_esc(e.explanation)}</p><ul>{li(e.evidence)}</ul></div>"
        )

    chain_rows = ""
    for s in fraud_chain:
        chain_rows += (
            f"<tr><td><b>{_esc(s['stage'])}</b></td><td>{_esc(s['description'])}</td>"
            f"<td>{li(s['evidence'])}</td><td>{_esc(s['recommended_control'])}</td></tr>"
        )

    rec_rows = ""
    for r in cortex.recommendations:
        rec_rows += (
            f"<tr><td><span class='tag'>{_esc(r.approval_mode)}</span></td>"
            f"<td>{_esc(r.action)}</td><td>{_esc(r.rationale)}</td></tr>"
        )

    comp = risk.components
    comp_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{v:.2f}</td><td>{cortex.risk.weights.get(k, 0):.2f}</td></tr>"
        for k, v in comp.model_dump().items()
    )

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>PARALLAX Report — {_esc(package)}</title>
<style>
body{{font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a1a;max-width:900px;margin:0 auto;padding:32px;}}
h1{{margin:0;}} .sub{{color:#666;}}
.verdict{{display:inline-block;color:#fff;background:{color};padding:6px 16px;border-radius:6px;font-weight:700;font-size:20px;}}
.score{{font-size:40px;font-weight:800;color:{color};}}
table{{border-collapse:collapse;width:100%;margin:12px 0;}} th,td{{border:1px solid #ddd;padding:8px;text-align:left;vertical-align:top;font-size:13px;}}
th{{background:#f5f5f5;}} .tag{{background:#37474f;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;}}
.irt{{border-left:4px solid {color};padding:8px 14px;margin:10px 0;background:#fafafa;}}
.section{{margin-top:28px;}} code{{background:#f0f0f0;padding:1px 4px;border-radius:3px;}}
ul{{margin:4px 0;}}
</style></head><body>
<h1>PARALLAX Investigation Report</h1>
<p class="sub">{_esc(package)} &middot; <code>{_esc(sha256)}</code></p>
<p><span class="verdict">{_esc(cortex.verdict)}</span></p>
<div class="section"><h2>Risk Score</h2>
<p class="score">{risk.calibrated_score:.0f}<span style="font-size:18px;color:#666;">/100 &plusmn;{risk.confidence_interval:.0f}</span></p>
<p class="sub">Evidence score {risk.evidence_score:.1f} (Layer A, deterministic) → calibrated {risk.calibrated_score:.1f} (Layer B).</p>
<table><tr><th>Component</th><th>Value (0-1)</th><th>Weight</th></tr>{comp_rows}</table>
</div>
<div class="section"><h2>Executive Summary</h2><p>{_esc(cortex.executive_summary) or "<em>n/a</em>"}</p></div>
<div class="section"><h2>Fraud Attack Chain</h2>
<table><tr><th>Stage</th><th>Description</th><th>Evidence</th><th>Recommended Control</th></tr>{chain_rows or "<tr><td colspan=4><em>No fraud-chain stages evidenced.</em></td></tr>"}</table></div>
<div class="section"><h2>Investigation Reasoning Trace</h2>{irt_rows or "<p><em>No reasoning trace produced.</em></p>"}</div>
<div class="section"><h2>Technical Findings</h2><ul>{li(cortex.technical_findings)}</ul></div>
<div class="section"><h2>MITRE ATT&CK</h2><p>{_esc(", ".join(cortex.attck_techniques)) or "<em>none</em>"}</p></div>
<div class="section"><h2>Indicators of Compromise</h2>
<b>Domains</b><ul>{li(cortex.iocs.get("domains", []))}</ul>
<b>IPs</b><ul>{li(cortex.iocs.get("ips", []))}</ul>
<b>URLs</b><ul>{li(cortex.iocs.get("urls", []))}</ul></div>
<div class="section"><h2>Recommended Actions</h2>
<table><tr><th>Approval</th><th>Action</th><th>Rationale</th></tr>{rec_rows or "<tr><td colspan=3><em>none</em></td></tr>"}</table></div>
</body></html>"""


def render_pdf(sha256: str, package: str, cortex: CortexResult, fraud_chain: list[dict]) -> bytes:
    """Render a PDF report with reportlab. Returns PDF bytes (b'' on failure)."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import (
            ListFlowable,
            ListItem,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        logger.warning("reportlab not installed; PDF unavailable.")
        return b""

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"PARALLAX {package}")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("PARALLAX Investigation Report", styles["Title"]))
    story.append(Paragraph(f"{_esc(package)} — {sha256}", styles["Normal"]))
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            f"<b>Verdict:</b> {cortex.verdict} &nbsp; "
            f"<b>Risk:</b> {cortex.risk.calibrated_score:.0f}/100 "
            f"(±{cortex.risk.confidence_interval:.0f})",
            styles["Heading2"],
        )
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(_esc(cortex.executive_summary) or "n/a", styles["Normal"]))

    if fraud_chain:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Fraud Attack Chain", styles["Heading2"]))
        data = [["Stage", "Description", "Control"]]
        for s in fraud_chain:
            data.append([s["stage"], s["description"][:80], s["recommended_control"][:80]])
        t = Table(data, colWidths=[90, 200, 200])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#37474f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(t)

    story.append(Spacer(1, 10))
    story.append(Paragraph("Investigation Reasoning Trace", styles["Heading2"]))
    for e in cortex.irt:
        story.append(Paragraph(f"<b>{e.status}: {_esc(e.claim)}</b>", styles["Normal"]))
        story.append(Paragraph(_esc(e.explanation), styles["Normal"]))

    if cortex.technical_findings:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Technical Findings", styles["Heading2"]))
        story.append(
            ListFlowable(
                [ListItem(Paragraph(_esc(f), styles["Normal"])) for f in cortex.technical_findings],
                bulletType="bullet",
            )
        )

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(f"ATT&CK: {_esc(', '.join(cortex.attck_techniques)) or 'none'}", styles["Normal"])
    )

    try:
        doc.build(story)
    except Exception as exc:
        logger.warning("PDF build failed: %s", exc)
        return b""
    return buf.getvalue()
