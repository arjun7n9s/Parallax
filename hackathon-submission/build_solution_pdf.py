"""Premium Solution Approach PDF builder for PARALLAX.

Hand-built with reportlab: vector architecture diagrams, restrained palette,
clean typography. No em dashes, no italic project name, no repeated per-page
branding (only a discreet page number from page two onward).
"""

from reportlab.graphics.shapes import Drawing, Group, Line, Polygon, Rect, String
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------- palette
INK = HexColor("#13202E")
NAVY = HexColor("#1C3A5E")
TEAL = HexColor("#0E7C86")
GOLD = HexColor("#B07A18")
GREY = HexColor("#5A6672")
BODY = HexColor("#2C3742")
LIGHT = HexColor("#EEF2F5")
PANEL = HexColor("#F5F8FA")
LINE = HexColor("#D4DCE3")
WHITE = white

OUT = "PARALLAX_Solution_Approach.pdf"
PAGE_W, PAGE_H = A4
LM = RM = 1.9 * cm
TM = 1.7 * cm
BM = 1.7 * cm
CONTENT_W = PAGE_W - LM - RM

# ---------------------------------------------------------------- styles
ss = getSampleStyleSheet()


def style(name, **kw):
    base = kw.pop("parent", ss["Normal"])
    return ParagraphStyle(name, parent=base, **kw)


H1 = style("H1", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=NAVY,
           spaceBefore=16, spaceAfter=2)
H1NUM = style("H1NUM", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=TEAL)
H2 = style("H2", fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=INK,
           spaceBefore=11, spaceAfter=3)
BODYS = style("BODYS", fontName="Helvetica", fontSize=9.4, leading=14.2, textColor=BODY,
              alignment=TA_LEFT, spaceAfter=6)
LEAD = style("LEAD", fontName="Helvetica", fontSize=10.4, leading=15.4, textColor=BODY,
             spaceAfter=7)
BULLET = style("BULLET", parent=BODYS, leftIndent=14, bulletIndent=3, spaceAfter=3, leading=13.6)
CAP = style("CAP", fontName="Helvetica-Oblique", fontSize=8, leading=11, textColor=GREY,
            alignment=TA_CENTER, spaceBefore=4, spaceAfter=10)
TH = style("TH", fontName="Helvetica-Bold", fontSize=8.3, leading=11, textColor=WHITE)
TD = style("TD", fontName="Helvetica", fontSize=8.3, leading=11.4, textColor=BODY)
TDB = style("TDB", fontName="Helvetica-Bold", fontSize=8.3, leading=11.4, textColor=INK)
KPIN = style("KPIN", fontName="Helvetica-Bold", fontSize=17, leading=18, textColor=NAVY,
             alignment=TA_CENTER)
KPIL = style("KPIL", fontName="Helvetica", fontSize=7.6, leading=9.6, textColor=GREY,
             alignment=TA_CENTER)

# cover styles
C_LABEL = style("C_LABEL", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=TEAL,
                alignment=TA_LEFT)
C_TITLE = style("C_TITLE", fontName="Helvetica-Bold", fontSize=52, leading=54, textColor=INK,
                alignment=TA_LEFT)
C_SUB = style("C_SUB", fontName="Helvetica", fontSize=12.5, leading=17, textColor=NAVY,
              alignment=TA_LEFT)
C_META = style("C_META", fontName="Helvetica", fontSize=9, leading=14, textColor=GREY,
               alignment=TA_LEFT)
C_METB = style("C_METB", fontName="Helvetica-Bold", fontSize=9, leading=14, textColor=INK,
               alignment=TA_LEFT)


def P(text, st=BODYS):
    return Paragraph(text, st)


def figure(drawing, caption, space_before=6):
    # Keep a diagram and its caption on the same page (no orphaned caption).
    return KeepTogether([Spacer(1, space_before), drawing, Paragraph(caption, CAP)])


def bullets(items, st=BULLET):
    return [Paragraph(f"<bullet>&#8226;</bullet>&nbsp;&nbsp;{t}", st) for t in items]


def rule(color=LINE, thickness=0.8, sb=2, sa=8, width="100%"):
    return HRFlowable(width=width, thickness=thickness, color=color, spaceBefore=sb,
                      spaceAfter=sa, lineCap="round")


def section(num, title):
    t = Table(
        [[Paragraph(num, H1NUM), Paragraph(title, H1)]],
        colWidths=[0.95 * cm, CONTENT_W - 0.95 * cm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [Spacer(1, 4), t, rule(TEAL, 1.2, 3, 9)]


# ---------------------------------------------------------------- tables
def data_table(rows, widths, header=True, zebra=True, align_cols=None):
    body = []
    for r in rows:
        body.append([c if isinstance(c, Flowable) else Paragraph(str(c), TD) for c in r])
    if header:
        body[0] = [Paragraph(str(c), TH) for c in rows[0]]
    t = Table(body, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("LINEAFTER", (0, 0), (-2, -1), 0.4, HexColor("#E6ECF1")),
    ]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TOPPADDING", (0, 0), (-1, 0), 6),
                 ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]
    if zebra:
        for i in range(1, len(body)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), PANEL))
    t.setStyle(TableStyle(cmds))
    return t


# ---------------------------------------------------------------- diagram helpers
def _txt(g, x, y, s, size=8, color=INK, font="Helvetica", anchor="middle"):
    g.add(String(x, y, s, fontName=font, fontSize=size, fillColor=color, textAnchor=anchor))


def _box(g, x, y, w, h, lines, fill, tcolor=WHITE, sub=None, r=5, font_size=8.5,
         stroke=None, sub_color=None):
    g.add(Rect(x, y, w, h, rx=r, ry=r, fillColor=fill,
               strokeColor=stroke or fill, strokeWidth=1))
    cx = x + w / 2
    if isinstance(lines, str):
        lines = [lines]
    n = len(lines) + (1 if sub else 0)
    total = n * (font_size + 2)
    start = y + h / 2 + total / 2 - font_size
    for i, ln in enumerate(lines):
        _txt(g, cx, start - i * (font_size + 2), ln, size=font_size, color=tcolor,
             font="Helvetica-Bold")
    if sub:
        _txt(g, cx, start - len(lines) * (font_size + 2), sub, size=6.6,
             color=sub_color or tcolor, font="Helvetica")


def _arrow(g, x1, y1, x2, y2, color=GREY, width=1.3, head=4.2, dashed=False):
    ln = Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=width)
    if dashed:
        ln.strokeDashArray = [3, 2]
    g.add(ln)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    g.add(Polygon([
        x2, y2,
        x2 - head * math.cos(ang - 0.4), y2 - head * math.sin(ang - 0.4),
        x2 - head * math.cos(ang + 0.4), y2 - head * math.sin(ang + 0.4),
    ], fillColor=color, strokeColor=color))


def diagram_pipeline():
    d = Drawing(CONTENT_W, 188)
    g = Group()
    stages = [
        ("Triage", "manifest +", "permissions", NAVY),
        ("Static", "decompile,", "YARA, taint", NAVY),
        ("Dynamic", "emulator +", "Frida + net", NAVY),
        ("Cortex", "multi-agent", "reasoning", NAVY),
        ("Delivery", "report, STIX,", "YARA, IOCs", NAVY),
    ]
    n = len(stages)
    gap = 11
    bw = (CONTENT_W - (n - 1) * gap) / n
    bh = 50
    top = 150
    for i, (t, s1, s2, fill) in enumerate(stages):
        x = i * (bw + gap)
        g.add(Rect(x, top, bw, bh, rx=5, ry=5, fillColor=fill, strokeColor=fill))
        _txt(g, x + bw / 2, top + bh - 17, t, size=10, color=WHITE, font="Helvetica-Bold")
        _txt(g, x + bw / 2, top + bh - 30, s1, size=6.6, color=HexColor("#C9D6E5"))
        _txt(g, x + bw / 2, top + bh - 39, s2, size=6.6, color=HexColor("#C9D6E5"))
        if i < n - 1:
            _arrow(g, x + bw + 1, top + bh / 2, x + bw + gap - 1, top + bh / 2, TEAL, 1.6)
    # TAIG band
    band_y = 56
    bandh = 46
    g.add(Rect(0, band_y, CONTENT_W, bandh, rx=6, ry=6, fillColor=LIGHT,
               strokeColor=TEAL, strokeWidth=1.1))
    _txt(g, CONTENT_W / 2, band_y + bandh - 16, "TAIG  Threat Analytics Intelligence Graph",
         size=9.5, color=NAVY, font="Helvetica-Bold")
    _txt(g, CONTENT_W / 2, band_y + bandh - 30,
         "Neo4j graph + Qdrant vectors  |  pattern memory, family attribution, campaign clustering, cross-sample search",
         size=6.8, color=GREY)
    for i in range(n):
        x = i * (bw + gap) + bw / 2
        _arrow(g, x, top - 1, x, band_y + bandh + 1, GREY, 0.9, 3.4, dashed=True)
    _txt(g, CONTENT_W / 2, 40, "Every analysis enriches the graph; the graph informs every later analysis.",
         size=7, color=GREY, font="Helvetica-Oblique")
    d.add(g)
    return d


def diagram_cortex():
    d = Drawing(CONTENT_W, 274)
    g = Group()
    cx = CONTENT_W / 2
    # input
    _box(g, cx - 70, 226, 140, 24, "Evidence in (static + dynamic)", NAVY, font_size=8)
    # parallel row
    par = [
        ("Code Interpreter", "code intent", NAVY),
        ("Behavior Analyst", "kill chain", TEAL),
        ("Visual Intel", "phishing / overlay", GOLD),
    ]
    pw = 150
    pgap = (CONTENT_W - 3 * pw) / 2
    ptop = 168
    for i, (t, s, fill) in enumerate(par):
        x = i * (pw + pgap)
        _box(g, x, ptop, pw, 34, [t], fill, sub=s, font_size=8.4)
        _arrow(g, cx, 225, x + pw / 2, ptop + 34 + 1, GREY, 1.0)
    # converge to correlator
    _box(g, cx - 95, 120, 190, 30, ["Intel Correlator"], TEAL,
         sub="ATT&CK mapping + family/campaign attribution (graph RAG)", font_size=8.4)
    for i in range(3):
        x = i * (pw + pgap) + pw / 2
        _arrow(g, x, ptop - 1, cx, 150 + 1, GREY, 1.0)
    # debate
    _box(g, cx - 95, 80, 190, 26, ["Debate"], GREY,
         sub="adversarial static-vs-dynamic check", font_size=8.4)
    _arrow(g, cx, 120, cx, 106 + 1, GREY, 1.1)
    # risk (deterministic)
    _box(g, cx - 95, 40, 190, 26, ["Risk  (deterministic, not LLM)"], INK,
         sub="auditable weighted evidence score", font_size=8, stroke=GOLD)
    _arrow(g, cx, 80, cx, 66 + 1, GREY, 1.1)
    # synthesis + result
    _box(g, cx - 95, 2, 190, 26, ["Synthesis  ->  CortexResult"], NAVY,
         sub="evidence-first verdict, narrative, IOCs", font_size=8.2)
    _arrow(g, cx, 40, cx, 28 + 1, GREY, 1.1)
    # legend
    lg = [("Crown-jewel  Sonnet 4.6", NAVY), ("Economy  GPT-4o-mini", TEAL),
          ("Vision  Gemini 2.5 Flash", GOLD), ("Deterministic", INK)]
    lx = 0
    for txt, col in lg:
        g.add(Rect(lx, 260, 9, 9, fillColor=col, strokeColor=col, rx=1.5, ry=1.5))
        _txt(g, lx + 13, 261, txt, size=6.6, color=GREY, anchor="start")
        lx += 122
    d.add(g)
    return d


def diagram_launch():
    d = Drawing(CONTENT_W, 200)
    g = Group()
    steps = [
        ("1  frida spawn(package)", "works for apps with a launcher icon", NAVY),
        ("2  am start  (any activity)", "non-launcher activities via manifest introspection", NAVY),
        ("3  am start-service", "for malware whose entry point is a service", NAVY),
        ("4  accessibility wake", "enable the AccessibilityService via secure settings", TEAL),
    ]
    bw = CONTENT_W * 0.62
    bh = 26
    gap = 10
    top = 200 - bh
    for i, (t, s, fill) in enumerate(steps):
        y = top - i * (bh + gap)
        _box(g, 0, y, bw, bh, [t], fill, sub=s, font_size=8.2, sub_color=HexColor("#C9D6E5"))
        if i < len(steps) - 1:
            _arrow(g, bw * 0.5, y - 1, bw * 0.5, y - gap + 1, GREY, 1.1)
            _txt(g, bw * 0.5 + 8, y - gap + 2, "if no pid", size=6, color=GREY, anchor="start")
    # success -> attach
    last_y = top - 3 * (bh + gap)
    _arrow(g, bw + 2, last_y + bh / 2, bw + 28, last_y + bh / 2, TEAL, 1.6)
    _box(g, bw + 30, last_y - 6, CONTENT_W - bw - 30, bh + 12,
         ["frida attach(pid)"], GOLD,
         sub="attach needs no launcher; hooks load on the live process", font_size=8.4)
    _txt(g, CONTENT_W / 2, 6,
         "The launch strategy used is recorded on every run, so a result is always provably instrumented.",
         size=7, color=GREY, font="Helvetica-Oblique")
    d.add(g)
    return d


def diagram_graph():
    d = Drawing(CONTENT_W, 200)
    g = Group()
    cx, cy = CONTENT_W / 2, 104
    w, h = 132, 26
    # center node
    g.add(Rect(cx - 42, cy - 17, 84, 34, rx=6, ry=6, fillColor=NAVY, strokeColor=NAVY))
    _txt(g, cx, cy + 3, "APK", size=11, color=WHITE, font="Helvetica-Bold")
    _txt(g, cx, cy - 9, "SHA-256", size=6, color=HexColor("#C9D6E5"))
    left = [
        ("Domain / IP / URL", "COMMUNICATES_WITH", 68, TEAL),
        ("Permission", "REQUESTS", 0, TEAL),
        ("ATT&CK Technique", "EXHIBITS", -68, TEAL),
    ]
    right = [
        ("Family", "ATTRIBUTED_TO", 68, GOLD),
        ("Campaign", "PART_OF", 0, GOLD),
        ("Pattern", "MATCHES", -68, GOLD),
    ]
    for label, rel, dy, col in left:
        x, ny = 0, cy + dy
        g.add(Rect(x, ny - h / 2, w, h, rx=5, ry=5, fillColor=col, strokeColor=col))
        _txt(g, x + w / 2, ny - 3, label, size=7.8, color=WHITE, font="Helvetica-Bold")
        _arrow(g, cx - 43, cy, x + w + 1, ny, GREY, 1.0)
        _txt(g, (x + w + cx - 43) / 2, (cy + ny) / 2 + 5, rel, size=5.6, color=GREY)
    for label, rel, dy, col in right:
        x, ny = CONTENT_W - w, cy + dy
        g.add(Rect(x, ny - h / 2, w, h, rx=5, ry=5, fillColor=col, strokeColor=col))
        _txt(g, x + w / 2, ny - 3, label, size=7.8, color=WHITE, font="Helvetica-Bold")
        _arrow(g, cx + 43, cy, x - 1, ny, GREY, 1.0)
        _txt(g, (x + cx + 43) / 2, (cy + ny) / 2 + 5, rel, size=5.6, color=GREY)
    _txt(g, cx, 6, "All writes use MERGE semantics, so re-analysis updates rather than duplicates.",
         size=7, color=GREY, font="Helvetica-Oblique")
    d.add(g)
    return d


# ---------------------------------------------------------------- KPI strip
def kpi_strip():
    cells = [
        ("5", "pipeline stages"),
        ("7", "reasoning agents"),
        ("~$0.16", "LLM cost / APK"),
        ("6", "outputs per analysis"),
        ("20+", "open-source tools"),
    ]
    row = [[Paragraph(v, KPIN)] for v, _ in cells]
    lab = [[Paragraph(label, KPIL)] for _, label in cells]
    w = CONTENT_W / len(cells)
    t = Table([[Paragraph(v, KPIN) for v, _ in cells],
               [Paragraph(label, KPIL) for _, label in cells]],
              colWidths=[w] * len(cells))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("LINEAFTER", (0, 0), (-2, -1), 0.6, LINE),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 0),
        ("TOPPADDING", (0, 1), (-1, 1), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.8, LINE),
    ]))
    return t


# ---------------------------------------------------------------- page decoration
def on_page(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, PAGE_H - 0.5 * cm, PAGE_W, 0.5 * cm, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.rect(0, PAGE_H - 0.66 * cm, PAGE_W, 0.16 * cm, fill=1, stroke=0)
    else:
        # Minimal footer: a thin rule and a centered page number. No per-page branding.
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.6)
        canvas.line(LM, BM - 0.35 * cm, PAGE_W - RM, BM - 0.35 * cm)
        canvas.setFont("Helvetica", 7.6)
        canvas.setFillColor(GREY)
        canvas.drawCentredString(PAGE_W / 2, BM - 0.72 * cm, str(doc.page))
    canvas.restoreState()


# ---------------------------------------------------------------- build
def build():
    doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=LM, rightMargin=RM,
                          topMargin=TM, bottomMargin=BM, title="PARALLAX Solution Approach",
                          author="arjun7n9s")
    frame = Frame(LM, BM, CONTENT_W, PAGE_H - TM - BM, id="main",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=on_page)])

    s = []

    # ===== COVER =====
    s.append(Spacer(1, 2.6 * cm))
    s.append(Paragraph("SOLUTION APPROACH", C_LABEL))
    s.append(Spacer(1, 0.5 * cm))
    s.append(Paragraph("PARALLAX", C_TITLE))
    s.append(Spacer(1, 0.35 * cm))
    s.append(HRFlowable(width="38%", thickness=2.4, color=TEAL, spaceBefore=2, spaceAfter=14,
                        hAlign="LEFT"))
    s.append(Paragraph(
        "An AI investigator for fraudulent Android applications: generative-AI reverse "
        "engineering, static and dynamic analysis, and evidence-first risk scoring.", C_SUB))
    s.append(Spacer(1, 5.4 * cm))
    meta = Table([
        [Paragraph("CHALLENGE", C_META),
         Paragraph("Harnessing Generative AI for Automated Reverse Engineering, Static and "
                   "Dynamic Analysis, and Risk Scoring of Fraudulent Mobile Applications (APKs) "
                   "and Malware", C_METB)],
        [Paragraph("CONTENTS", C_META),
         Paragraph("Solution approach, system architecture, datasets, open-source stack, "
                   "validation", C_METB)],
        [Paragraph("STATUS", C_META),
         Paragraph("Working prototype, validated end-to-end on a live banking-trojan sample",
                   C_METB)],
    ], colWidths=[2.6 * cm, CONTENT_W - 2.6 * cm])
    meta.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
    ]))
    s.append(meta)
    s.append(PageBreak())

    # ===== EXECUTIVE SUMMARY =====
    s += section("", "Executive Summary")
    s.append(Paragraph(
        "PARALLAX treats every submitted APK as a case to investigate, not a file to scan. "
        "A classical mobile-malware analysis stack (decompilation, taint analysis, an "
        "instrumented Android emulator) feeds a multi-agent generative-AI reasoning layer that "
        "interprets the evidence, attributes the malware family, and produces an explainable "
        "risk verdict. Every analysis also enriches a shared knowledge graph, so detection "
        "compounds with volume rather than resetting on each sample.", LEAD))
    s.append(Paragraph(
        "The design answers the three properties that defeat signature-based defenses: heavy "
        "runtime obfuscation, malicious surfaces hidden behind accessibility and notification "
        "services, and hourly polymorphic repackaging. The verdict is produced by a "
        "deterministic, auditable scoring model over evidence items; the language model writes "
        "the narrative, it does not decide the score.", BODYS))
    s.append(Spacer(1, 4))
    s.append(kpi_strip())

    # ===== 1 PROBLEM =====
    s += section("1", "Problem Context")
    s.append(Paragraph(
        "Fraudsters distribute malicious Android applications through WhatsApp, SMS, email, and "
        "phishing links, then use them to steal customer credentials, harvest sensitive data, and "
        "authorize fraudulent transactions against bank accounts. The analysis that stops them is "
        "still largely manual: slow, costly, and dependent on a small pool of expert reverse "
        "engineers. Sample volume and velocity have outgrown that model.", BODYS))
    s.append(Paragraph(
        "The technical reasons signature-based and manual defenses fall behind are threefold. "
        "Current banking-trojan families such as Cerberus, Hydra, SharkBot, Anatsa, SpyNote, and "
        "TeaBot share three properties:", BODYS))
    s += bullets([
        "<b>Heavy runtime obfuscation.</b> R8 and DexGuard, string encryption, dead-code "
        "injection, and control-flow flattening blunt static signatures.",
        "<b>Gated malicious surface.</b> The payload lives in an AccessibilityService or "
        "NotificationListenerService, not the launcher activity. The manifest main activity is "
        "a decoy, so naive sandboxing that spawns the launcher never reaches the payload.",
        "<b>Polymorphic repackaging.</b> The same family is re-signed and re-bundled hourly by "
        "malware-as-a-service operators, which structurally outmatches hash-based detection.",
    ])
    s.append(Paragraph(
        "A pipeline that ships a fresh signature within 24 hours of a new sample is already a "
        "day behind. The challenge calls for generative AI applied to the analysis itself: not "
        "a faster signature matcher, but a system that reasons about the APK as an investigator "
        "would, forms hypotheses, and tests them at runtime.", BODYS))

    # ===== 2 SOLUTION OVERVIEW =====
    s += section("2", "Solution Approach and Architecture")
    s.append(Paragraph(
        "PARALLAX is a five-stage pipeline with a cross-cutting knowledge layer. Each stage is "
        "independently callable, and the reasoning layer is idempotent, so it can be re-run as "
        "new evidence arrives without restarting the analysis.", BODYS))
    s.append(figure(diagram_pipeline(),
                    "Figure 1. End-to-end analysis pipeline and the compounding knowledge graph."))
    s.append(Paragraph(
        "Triage runs a fast model on the manifest and permissions to route the sample. Static "
        "analysis decompiles the APK and grounds a code-intent classification in real code. "
        "Dynamic analysis executes the sample under instrumentation. The Cortex reasons over the "
        "combined evidence. Delivery emits an evidence-first report and machine-readable "
        "intelligence. The knowledge graph records every result and feeds context back into "
        "future analyses.", BODYS))

    s.append(Paragraph("Coverage of the problem statement", H2))
    s.append(Paragraph(
        "Every capability called for in the brief maps to a concrete component of the system.",
        BODYS))
    cover = [
        ["Required capability", "How PARALLAX delivers it"],
        ["Reverse engineering", "jadx decompilation feeding the Code Interpreter agent"],
        ["Malware pattern recognition", "YARA rules, family attribution, and pattern memory in "
         "the knowledge graph"],
        ["Automated code interpretation", "Code Interpreter agent classifies decompiled code "
         "intent, grounded in real code"],
        ["Intelligent threat summarization", "Synthesis agent produces an evidence-first report "
         "and verdict"],
        ["Static analysis of permissions, APIs, embedded code", "androguard, FlowDroid taint "
         "(source-to-sink API flows), jadx, YARA"],
        ["Dynamic analysis of runtime activity and network", "Frida hooks on the live process "
         "and mitmproxy traffic capture"],
        ["Severity classification and risk score", "Deterministic two-layer score with a LOW to "
         "CRITICAL verdict"],
        ["Investigation report with actionable recommendations", "PDF report, fraud-chain "
         "reconstruction, prioritized actions, STIX, YARA, IOCs"],
        ["Faster than manual analysis, built for banks", "Automated pipeline at about 0.16 US "
         "dollars per sample, bank-readable outputs"],
    ]
    s.append(data_table(cover, [6.4 * cm, CONTENT_W - 6.4 * cm]))

    # ===== 3 CORTEX =====
    s += section("3", "The Reasoning Cortex")
    s.append(Paragraph(
        "The Cortex is a multi-agent system organized as a directed graph. It runs after static "
        "and dynamic stages have produced raw evidence, interprets that evidence, and produces a "
        "final verdict with a full evidence trail. Models are matched to task difficulty, which "
        "keeps quality high where it matters and cost low everywhere else.", BODYS))
    s.append(figure(diagram_cortex(), "Figure 2. The multi-agent reasoning graph, with models tiered by task.", 4))

    s.append(Paragraph("Agent roster", H2))
    roster = [
        ["Agent", "Role", "Model tier"],
        ["Code Interpreter", "Classifies decompiled code intent (banking trojan, dropper, "
         "stealer, adware, benign)", "Crown-jewel"],
        ["Behavior Analyst", "Reconstructs the kill-chain from runtime observations", "Economy"],
        ["Visual Intel", "Detects overlay attacks and brand impersonation in screenshots",
         "Vision"],
        ["Intel Correlator", "ATT&CK mapping and family / campaign attribution via graph RAG",
         "Economy + RAG"],
        ["Debate", "Adversarial check for static-versus-dynamic contradiction", "Economy"],
        ["Risk", "Two-layer weighted evidence score", "Deterministic"],
        ["Synthesis", "Evidence-first report and final verdict", "Crown-jewel"],
    ]
    s.append(data_table(roster, [3.0 * cm, CONTENT_W - 3.0 * cm - 3.0 * cm, 3.0 * cm]))
    s.append(Spacer(1, 8))

    s.append(Paragraph("Why a multi-agent design, and why the score is deterministic", H2))
    s.append(Paragraph(
        "A single large prompt would be slow, brittle, hard to audit, and expensive. "
        "Decomposition lets the independent agents run in parallel, isolates failures to one "
        "agent, makes every step a structured object persisted with a confidence value, and "
        "lets each task use the right model. Crucially, the final score is not an LLM output. "
        "It is a weighted sum of evidence categories, each scored from zero to one and clamped "
        "to a 0 to 100 scale, where every component links back to the evidence that produced "
        "it. A reviewer can audit any verdict by walking that chain.", BODYS))

    cost = [
        ["Risk component", "Weight", "Evidence", "Cost driver"],
    ]
    weights = [
        ["Runtime observations", "0.30", "Frida hooks on sensitive APIs, captured C2 traffic"],
        ["Code intent", "0.20", "Classification of decompiled code"],
        ["Visual phishing", "0.15", "Overlay and brand-impersonation detection"],
        ["ATT&CK coverage", "0.15", "Distinct Mobile ATT&CK techniques matched"],
        ["Packer / obfuscation", "0.10", "APKiD packer and protector signatures"],
        ["Family attribution", "0.05", "Confirmed known family from threat intel"],
        ["Other signals", "0.05", "Manifest and certificate anomalies"],
    ]
    wrows = [["Risk component", "Weight", "Evidence"]] + weights
    s.append(Spacer(1, 4))
    s.append(Paragraph("Two-layer risk score (deterministic)", H2))
    s.append(data_table(wrows, [4.2 * cm, 1.8 * cm, CONTENT_W - 6.0 * cm]))
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "When a confirmed known family is detected, for example Cerberus via a MalwareBazaar "
        "hash lookup, an auditable HIGH floor is applied: the verdict will not drop below "
        "malicious regardless of the narrative. This guards against model under-confidence on "
        "fresh-looking variants of known families.", BODYS))

    # ===== 4 EVIDENCE PIPELINE =====
    s += section("4", "The Evidence Pipeline: Static and Dynamic")
    s.append(Paragraph("Static analysis", H2))
    s.append(Paragraph(
        "From the raw APK, the static stage produces a decompiled source tree, manifest and "
        "certificate data, permission list, packer signatures, YARA matches, and a source-to-sink "
        "taint map. The Code Interpreter reads a ranked subset of the decompiled code, top files "
        "by sensitive-API signal with framework packages filtered out, so the classification is "
        "grounded in real code rather than manifest metadata alone.", BODYS))

    s.append(Paragraph("Dynamic analysis and the launch-resistance problem", H2))
    s.append(Paragraph(
        "The hard problem in dynamic analysis of modern Android malware is launch resistance. "
        "Trojans hide the launcher icon, place the payload in a service with no main activity, "
        "and obfuscate the manifest. A naive call to spawn the launcher fails. PARALLAX uses a "
        "launch fallback chain and, once any process is running, attaches to it rather than "
        "spawning it, since attach needs no launcher.", BODYS))
    s.append(figure(diagram_launch(), "Figure 3. Launch fallback chain for icon-hiding malware.", 4))
    s.append(Paragraph(
        "Once a process is reached, the system injects pre-built Frida Java hooks on high-signal "
        "APIs (SMS interception, accessibility hijacking, crypto key extraction, content-provider "
        "theft), routes device traffic through mitmproxy to capture HTTP and TLS, and drives the "
        "UI with DroidBot while capturing screenshots. Hook callbacks, network flows, and "
        "screenshots are aggregated into structured observation records. A prelude beacon records "
        "that instrumentation attached, so a run with zero malicious observations is "
        "distinguishable from a run that never instrumented the sample.", BODYS))

    # ===== 5 KNOWLEDGE GRAPH =====
    s += section("5", "The Knowledge Graph: A Compounding Layer")
    s.append(Paragraph(
        "Every analysis enriches a shared Threat Analytics Intelligence Graph, stored in Neo4j "
        "for structure and Qdrant for semantic vectors. The graph is what makes PARALLAX a "
        "learning system rather than a per-analysis tool.", BODYS))
    s.append(figure(diagram_graph(), "Figure 4. Core node and relationship types in the knowledge graph.", 4))
    s.append(Paragraph(
        "After a hundred or more samples, the graph answers questions no single-analysis tool "
        "can: which other samples talk to a given C2, what a new variant of a family looks like "
        "by semantic similarity, and whether a new campaign is forming via community detection "
        "over shared infrastructure. The Intel Correlator queries the graph during analysis, so a "
        "report can state that a sample shares a C2 with prior samples attributed to a named "
        "campaign. That is the difference between a per-analysis report and an intelligence "
        "product.", BODYS))

    # ===== 6 DATASETS =====
    s += section("6", "Datasets")
    s.append(Paragraph(
        "PARALLAX operates over real-world, labeled, observable Android malware, not curated toy "
        "examples. Datasets fall into four roles: malware sample corpora for analysis and "
        "validation, benign controls to measure false positives, threat-intelligence feeds for "
        "attribution and standards mapping, and a reference corpus for visual brand comparison.",
        BODYS))

    s.append(Paragraph("Primary data sources", H2))
    src = [
        ["Source", "What it provides", "Access"],
        ["MalwareBazaar (abuse.ch)", "Labeled samples with family tags, hashes, signatures, "
         "malware type", "Public API and bulk download; hash lookup needs no key"],
        ["AndroZoo (Univ. of Liege)", "20M+ APKs, malicious and benign, with VirusTotal labels",
         "Free for academic use, on request"],
        ["VirusTotal", "Per-hash family attribution, behavior tags, detection counts",
         "API, lookup"],
        ["MITRE ATT&CK Mobile", "Standardized technique catalog for mobile malware",
         "Public, free (STIX 2.1)"],
        ["MISP and abuse.ch feeds", "Indicators, events, and campaign context (ThreatFox, URLhaus)",
         "Community feeds or self-hosted"],
        ["Internal TAIG corpus", "Samples already analyzed by PARALLAX; grows per submission",
         "Native to the system"],
    ]
    s.append(data_table(src, [3.4 * cm, CONTENT_W - 3.4 * cm - 4.6 * cm, 4.6 * cm]))
    s.append(Spacer(1, 8))

    s.append(Paragraph("Sample coverage", H2))
    s.append(Paragraph(
        "Malicious families targeted in priority order, based on current banking-trojan "
        "intelligence: Cerberus (accessibility overlay, hidden icon), Hydra (modular dropper), "
        "SharkBot (automatic transfer system, anti-analysis), Anatsa and TeaBot (accessibility "
        "based), SpyNote (wide RAT capability), Octo and Coper (C2-heavy), FluBot (SMS worm), "
        "BRATA, and Joker (billing fraud). Benign controls include popular Google Play apps "
        "across banking, communication, and utility categories, open-source reference apps, and "
        "purpose-built apps with synthetic suspicious behavior for end-to-end testing.", BODYS))

    s.append(Paragraph("Validation methodology", H2))
    s.append(Paragraph(
        "For every submitted sample the system maintains a validation record, so a run on one "
        "sample is a case study and a table of 200 or more samples is a validated system. The "
        "target corpus is 50 or more samples each from four primary families, 30 or more each "
        "from two or three additional families, and 20 or more benign controls. Risk-score "
        "calibration is trained and validated against this corpus.", BODYS))
    valrows = [
        ["Field", "Source of ground truth"],
        ["True family", "MalwareBazaar, VirusTotal, AndroZoo labels"],
        ["True verdict (clean / suspicious / malicious)", "Threat-intel consensus, two or more sources"],
        ["System verdict, family, risk score", "PARALLAX output, compared against truth"],
        ["Per-stage latency and cost", "Telemetry (tokens times model rate)"],
    ]
    s.append(data_table(valrows, [7.2 * cm, CONTENT_W - 7.2 * cm]))
    s.append(Spacer(1, 6))
    s.append(Paragraph(
        "Data governance: all samples are handled as live malware. Files are quarantined in "
        "object storage, are never executed on the API host, and run only inside isolated "
        "emulators whose outbound traffic is confined to the capture proxy. Cloud model routing "
        "can be disabled entirely for on-premise, data-residency deployments.", BODYS))

    # ===== 7 STACK =====
    s += section("7", "Open-Source Technology Stack")
    s.append(Paragraph(
        "PARALLAX is built on established open-source tools. Generative-AI calls are routed "
        "through a single gateway abstraction that allows fully local operation when no cloud "
        "keys are configured.", BODYS))
    stack = [
        ["Component", "Purpose", "License"],
        ["jadx", "Dex-to-Java decompilation", "Apache 2.0"],
        ["androguard", "Manifest, certificate, and DEX analysis", "Apache 2.0"],
        ["YARA", "Pattern matching over decompiled code", "BSD-2"],
        ["APKiD", "Packer and obfuscator identification", "MIT"],
        ["FlowDroid", "Static taint analysis (sources to sinks)", "GPL-2.0"],
        ["Frida", "Dynamic Java instrumentation and hooks", "wxWindows"],
        ["mitmproxy", "TLS-intercepting proxy for network capture", "MIT"],
        ["DroidBot", "UI automation driver for dynamic runs", "MIT"],
        ["Android emulator (QEMU)", "Instrumented x86_64 execution environment", "Apache 2.0"],
        ["Neo4j", "Threat-intelligence knowledge graph", "GPL-3.0 (community)"],
        ["Qdrant", "Vector search across submissions", "Apache 2.0"],
        ["FastAPI, Celery, Redis", "API, distributed task queue, broker", "MIT / BSD"],
        ["PostgreSQL, MinIO", "Relational metadata, object storage", "PostgreSQL / AGPL-3.0"],
        ["MISP, stix2", "Threat-intel sharing and STIX 2.1 export", "AGPL-3.0 / BSD"],
        ["Ollama", "Local model serving (fully on-premise mode)", "MIT"],
    ]
    s.append(data_table(stack, [4.4 * cm, CONTENT_W - 4.4 * cm - 3.4 * cm, 3.4 * cm]))

    # ===== 8 DELIVERABLES + VALIDATION =====
    s += section("8", "Deliverables and Early Validation")
    s.append(Paragraph("Produced for every analysis", H2))
    s += bullets([
        "<b>Evidence-first PDF report</b> readable by a bank security lead: executive summary, "
        "evidence table, ATT&CK mapping, IOC list, a ten-stage fraud-chain reconstruction, and "
        "prioritized, actionable recommendations.",
        "<b>STIX 2.1 bundle</b> compatible with MISP, OpenCTI, and any TAXII consumer.",
        "<b>Auto-generated YARA rule</b>, compile-validated before delivery, plus network "
        "signatures derived from captured traffic.",
        "<b>Signed webhooks</b> to SIEM and SOAR endpoints, and knowledge-graph updates.",
    ])
    s.append(Paragraph("Early validation", H2))
    s.append(Paragraph(
        "The current build runs the full pipeline end-to-end. On a live Cerberus banking-trojan "
        "sample sourced from MalwareBazaar, the system launched the icon-hidden payload through "
        "the accessibility-wake path, attached the instrumentation, captured a runtime "
        "observation, attributed the family as Cerberus, and returned a HIGH verdict with a "
        "complete evidence trail, at a measured cost in the range of 0.15 to 0.20 US dollars per "
        "sample. The next milestone is the 200-sample validation corpus and the empirical "
        "calibration layer trained on it.", BODYS))

    doc.build(s)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
