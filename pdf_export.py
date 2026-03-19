"""
pdf_export.py
Clean, print-friendly internal briefing PDFs.
Black text on white — designed to be read on paper or screen.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

W, H = A4
M = 18 * mm
CW = W - 2 * M

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY    = colors.HexColor("#0b1829")
TEAL    = colors.HexColor("#0099b8")
RED     = colors.HexColor("#dc2626")
AMBER   = colors.HexColor("#d97706")
GREEN   = colors.HexColor("#059669")
GREY    = colors.HexColor("#64748b")
LGREY   = colors.HexColor("#f1f5f9")
MGREY   = colors.HexColor("#e2e8f0")
BLACK   = colors.HexColor("#0f172a")
WHITE   = colors.white


def _score_colour(score):
    if score >= 75: return GREEN
    if score >= 55: return AMBER
    return RED


def _sev_colour(sev):
    return {"critical": RED, "advisory": AMBER, "unconfirmed": TEAL}.get(sev, AMBER)


def _styles():
    b = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, parent=b["Normal"], **kw)
    return {
        "h1":      S("h1",  fontName="Helvetica-Bold",    fontSize=20, textColor=NAVY,  leading=26, spaceAfter=4),
        "h2":      S("h2",  fontName="Helvetica-Bold",    fontSize=14, textColor=NAVY,  leading=18, spaceAfter=3),
        "h3":      S("h3",  fontName="Helvetica-Bold",    fontSize=11, textColor=NAVY,  leading=14, spaceAfter=2),
        "body":    S("body",fontName="Helvetica",          fontSize=9,  textColor=BLACK, leading=13),
        "small":   S("sml", fontName="Helvetica",          fontSize=8,  textColor=GREY,  leading=11),
        "bold9":   S("b9",  fontName="Helvetica-Bold",     fontSize=9,  textColor=BLACK, leading=13),
        "bold10":  S("b10", fontName="Helvetica-Bold",     fontSize=10, textColor=BLACK, leading=14),
        "mono":    S("mo",  fontName="Courier",            fontSize=7.5,textColor=GREY,  leading=10),
        "mono_b":  S("mob", fontName="Courier-Bold",       fontSize=7.5,textColor=NAVY,  leading=10),
        "teal":    S("te",  fontName="Helvetica-Bold",     fontSize=9,  textColor=TEAL,  leading=12),
        "red":     S("re",  fontName="Helvetica-Bold",     fontSize=9,  textColor=RED,   leading=12),
        "green":   S("gr",  fontName="Helvetica-Bold",     fontSize=9,  textColor=GREEN, leading=12),
        "amber":   S("am",  fontName="Helvetica-Bold",     fontSize=9,  textColor=AMBER, leading=12),
        "italic":  S("it",  fontName="Helvetica-Oblique",  fontSize=9,  textColor=GREY,  leading=12),
        "white9":  S("w9",  fontName="Helvetica",          fontSize=9,  textColor=WHITE, leading=13),
        "whiteb":  S("wb",  fontName="Helvetica-Bold",     fontSize=9,  textColor=WHITE, leading=13),
        "whiteh":  S("wh",  fontName="Helvetica-Bold",     fontSize=13, textColor=WHITE, leading=17),
    }


def _section_header(title, S):
    """Dark navy section header bar."""
    t = Table(
        [[Paragraph(title, S["whiteb"])]],
        colWidths=[CW]
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), NAVY),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    return t


def _divider():
    return HRFlowable(width=CW, thickness=0.5, color=MGREY, spaceAfter=6, spaceBefore=6)


def _footer_cb(canvas, doc, postcode, page_label):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GREY)
    canvas.drawString(M, 10*mm, f"Modern Networks — Internal Sales Briefing — {postcode} — CONFIDENTIAL")
    canvas.drawRightString(W - M, 10*mm, f"Page {doc.page}  ·  {page_label}")
    canvas.restoreState()


def generate_briefing_pdf(report: dict, angle: str) -> bytes:
    buf = io.BytesIO()
    S   = _styles()
    P   = report.get("prospect", {})
    ws  = report.get("wiredScore", {})
    pc  = report.get("postcode", "")
    score = report.get("score", 0)
    sc_col = _score_colour(score)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=M, rightMargin=M,
        topMargin=M, bottomMargin=20*mm,
        title=f"MN Briefing — {pc}",
    )

    ANGLE_TITLES = {
        "owner":      "Building Owner",
        "agent":      "Managing Agent",
        "management": "Building Management",
    }
    ANGLE_NOTES = {
        "owner":      "Frame around asset value, EPC compliance risk, and the 4.9% valuation uplift for 1Gbps-certified buildings.",
        "agent":      "Frame around occupier satisfaction, complaint reduction, and day-one connectivity.",
        "management": "Frame around operational resilience, security compliance, and insurance requirements.",
    }
    TALKING_POINTS = {
        "owner": [
            "Buildings with 1Gbps connectivity and WiredScore certification achieve 4.9% higher valuations.",
            "EPC compliance risk is a direct threat to lettability under proposed 2027 legislation — the digital infrastructure component is addressable now.",
            "Research shows 19.4% lower tenant churn where buildings have properly managed digital infrastructure.",
            "Modern Networks are WiredScore Accredited Professionals. Most buildings certify within 60 days.",
        ],
        "agent": [
            "Connectivity and mobile signal are the top two categories of occupier complaints in multi-tenant buildings.",
            "Zero onboarding delays when Modern Networks provides day-one managed connectivity.",
            "We work with CBRE, JLL, Savills, and Cushman & Wakefield — portfolio WiredScore certification at scale.",
            "One contract, one invoice, one point of contact for connectivity, IT support, and security.",
        ],
        "management": [
            "Insurers are requiring demonstrable cybersecurity controls for commercial buildings.",
            "We help meet ISO 27001 and GDPR obligations via a single managed service with regular audits.",
            "Resilient managed connectivity with geographic redundancy keeps building systems online.",
            "One managed services partner for network, security, and cloud across 2,000+ UK properties.",
        ],
    }

    story = []

    # ══════════════════════════════════════════════════════════════
    # PAGE 1 — COVER & PROSPECT DETAILS
    # ══════════════════════════════════════════════════════════════

    # Top classification bar
    t = Table([[Paragraph(
        "INTERNAL  ·  MODERN NETWORKS SALES BRIEFING  ·  NOT FOR EXTERNAL DISTRIBUTION",
        S["whiteb"]
    )]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    # Title row — property name + score box side by side
    company_str = P.get("company","")
    title_str   = f"{company_str} — {pc}" if company_str else f"Building Assessment — {pc}"

    score_table = Table(
        [[
            Paragraph(f'<font size="32" color="{sc_col.hexval()}"><b>{score}</b></font>', S["body"]),
        ],[
            Paragraph("/100", S["small"]),
        ],[
            Paragraph(report.get("scoreLabel",""), ParagraphStyle(
                "sl", fontName="Helvetica-Bold", fontSize=8,
                textColor=sc_col, leading=10
            )),
        ]],
        colWidths=[30*mm]
    )
    score_table.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
    ]))

    title_table = Table(
        [[
            [
                Paragraph(title_str, S["h1"]),
                Paragraph(
                    f"UPRN {report.get('uprn','N/A')}  ·  Generated {report.get('savedAt','')}  ·  "
                    f"Prepared by {P.get('staff','MN Staff')} ({P.get('initials','MN')})",
                    S["mono"]
                ),
                Spacer(1, 3*mm),
                Paragraph(
                    f"<b>Sales angle:</b> {ANGLE_TITLES.get(angle,'')}"
                    f"  ·  <i>{ANGLE_NOTES.get(angle,'')}</i>",
                    S["small"]
                ),
            ],
            score_table,
        ]],
        colWidths=[CW - 34*mm, 34*mm]
    )
    title_table.setStyle(TableStyle([
        ("VALIGN",  (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(0,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1), 6),
    ]))
    story.append(title_table)
    story.append(_divider())
    story.append(Spacer(1, 2*mm))

    # Prospect details — two-column grid
    story.append(_section_header("PROSPECT DETAILS", S))
    story.append(Spacer(1, 3*mm))

    def _prow(label, value):
        return [
            Paragraph(label, S["mono"]),
            Paragraph(str(value) if value else "—", S["bold9"]),
        ]

    fields = [
        ("COMPANY",  P.get("company","")),
        ("CONTACT",  P.get("contact","")),
        ("JOB TITLE",P.get("title","")),
        ("EMAIL",    P.get("email","")),
        ("PHONE",    P.get("phone","")),
        ("STAGE",    P.get("stage","")),
        ("MEETING",  P.get("meeting","")),
        ("ANGLE",    ANGLE_TITLES.get(angle,"")),
    ]
    half   = len(fields) // 2
    lw     = (CW - 6*mm) / 2
    for i in range(half):
        l = fields[i]
        r_f = fields[i + half] if i + half < len(fields) else ("","")
        row = Table(
            [_prow(l[0], l[1]) + [""] + _prow(r_f[0], r_f[1])],
            colWidths=[24*mm, lw-27*mm, 6*mm, 24*mm, lw-27*mm]
        )
        row.setStyle(TableStyle([
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, MGREY),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("BACKGROUND",    (0,0),(-1,-1), WHITE),
        ]))
        story.append(row)

    story.append(Spacer(1, 5*mm))

    # WiredScore status
    ws_status = ws.get("status","unconfirmed")
    ws_col    = GREEN if ws_status=="certified" else RED if ws_status=="not-certified" else TEAL
    ws_label  = (
        f"CERTIFIED — {ws.get('scheme','')} {ws.get('level','')}  "
        f"(verified {ws.get('verifiedAt','')} by {ws.get('verifiedBy','')})"
        if ws_status == "certified" else
        "NOT CERTIFIED — WiredScore AP Services conversation applicable"
        if ws_status == "not-certified" else
        "STATUS UNCONFIRMED — verify at wiredscore.com/certified-buildings"
    )
    ws_table = Table(
        [[
            Paragraph("WIREDSCORE / SMARTSCORE", S["mono_b"]),
            Paragraph(ws_label, ParagraphStyle(
                "wsl", fontName="Helvetica-Bold", fontSize=9,
                textColor=ws_col, leading=12
            )),
        ]],
        colWidths=[44*mm, CW-44*mm]
    )
    ws_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("BOX",           (0,0),(-1,-1), 0.5, ws_col),
        ("LINEBELOW",     (0,0),(-1,-1), 2,   ws_col),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(ws_table)
    story.append(Spacer(1, 4*mm))

    # Internal notes
    if P.get("notes"):
        notes_t = Table(
            [[
                Paragraph("INTERNAL NOTES", S["mono_b"]),
                Paragraph(P["notes"][:400], S["body"]),
            ]],
            colWidths=[28*mm, CW-28*mm]
        )
        notes_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#fffbeb")),
            ("BOX",           (0,0),(-1,-1), 0.5, AMBER),
            ("LINEBELOW",     (0,0),(-1,-1), 2,   AMBER),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        story.append(notes_t)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # PAGE 2 — DATA OVERVIEW & TALKING POINTS
    # ══════════════════════════════════════════════════════════════
    story.append(_section_header("DATA OVERVIEW", S))
    story.append(Spacer(1, 4*mm))

    metrics = report.get("metrics", {})
    METRIC_LABELS = {
        "connectivity":"Connectivity","epc":"Energy / EPC",
        "occupiers":"Occupier Profile","flood":"Flood Risk",
        "mobile":"Mobile Indoor","crime":"Crime Profile",
    }
    STATUS_COLS = {"good": GREEN, "warn": AMBER, "bad": RED}

    items = list(metrics.items())
    mw    = (CW - 4*mm) / 3

    for row_start in range(0, len(items), 3):
        chunk = items[row_start:row_start+3]
        cells = []
        for k, v in chunk:
            lc     = STATUS_COLS.get(v.get("status",""), GREY)
            status_text = {"good":"✓ Good","warn":"⚠ Advisory","bad":"✗ Attention"}.get(v.get("status",""),"")
            cell = [
                Paragraph(METRIC_LABELS.get(k,k).upper(), S["mono"]),
                Paragraph(
                    f'<font color="{lc.hexval()}"><b>{v.get("value","—")}</b></font>',
                    ParagraphStyle("mv2", fontName="Helvetica-Bold",
                                   fontSize=14, leading=18, textColor=BLACK)
                ),
                Paragraph(v.get("detail","").replace("\n","  ·  "), S["small"]),
                Spacer(1, 2*mm),
                Paragraph(
                    f'<font color="{lc.hexval()}">{status_text}</font>',
                    S["small"]
                ),
            ]
            cells.append(cell)
        while len(cells) < 3:
            cells.append([""])

        t = Table([cells], colWidths=[mw, mw, mw])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), WHITE),
            ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
            ("LINEBEFORE",    (1,0),(2,-1),  0.5, MGREY),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 4*mm))
    story.append(_section_header(f"SALES TALKING POINTS — {ANGLE_TITLES.get(angle,'').upper()}", S))
    story.append(Spacer(1, 4*mm))

    for pt in TALKING_POINTS.get(angle, TALKING_POINTS["owner"]):
        row = Table(
            [[Paragraph("→", S["teal"]), Paragraph(pt, S["body"])]],
            colWidths=[8*mm, CW-8*mm]
        )
        row.setStyle(TableStyle([
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, MGREY),
            ("BACKGROUND",    (0,0),(-1,-1), WHITE),
        ]))
        story.append(row)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # PAGE 3 — GAPS & OPPORTUNITIES
    # ══════════════════════════════════════════════════════════════
    story.append(_section_header("GAPS & OPPORTUNITIES", S))
    story.append(Spacer(1, 3*mm))

    gaps = report.get("gaps", [])
    crit_count = sum(1 for g in gaps if g["sev"]=="critical")
    adv_count  = sum(1 for g in gaps if g["sev"]=="advisory")
    uncon_count= sum(1 for g in gaps if g["sev"]=="unconfirmed")
    story.append(Paragraph(
        f"{crit_count} critical  ·  {adv_count} advisory  ·  {uncon_count} unconfirmed  "
        f"·  Each gap maps to a Modern Networks service",
        S["small"]
    ))
    story.append(Spacer(1, 4*mm))

    for g in gaps:
        lc        = _sev_colour(g["sev"])
        sev_label = g["sev"].upper()
        bg_col    = (
            colors.HexColor("#fff5f5") if g["sev"]=="critical" else
            colors.HexColor("#fffbeb") if g["sev"]=="advisory" else
            colors.HexColor("#f0f9ff")
        )

        gap_content = [
            Table(
                [[
                    Paragraph(sev_label, ParagraphStyle(
                        "sl2", fontName="Courier-Bold", fontSize=7.5,
                        textColor=lc, leading=10
                    )),
                    Paragraph(f"{g['icon']}  {g['title']}", S["bold10"]),
                ]],
                colWidths=[18*mm, CW - 18*mm - 52*mm]
            ),
            Spacer(1, 2*mm),
            Paragraph(g["desc"], S["body"]),
            Spacer(1, 2*mm),
            Paragraph(f"Source: {g['source']}", S["mono"]),
        ]

        service_box = Table(
            [
                [Paragraph("MODERN NETWORKS SERVICE", S["mono_b"])],
                [Paragraph(g["service"].replace("\n", "\n"), S["bold9"])],
                [Spacer(1, 1*mm)],
                [Paragraph(g["detail"], S["small"])],
            ],
            colWidths=[50*mm]
        )
        service_box.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), LGREY),
            ("BOX",           (0,0),(-1,-1), 0.5, lc),
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ]))

        gap_row = Table(
            [[gap_content, service_box]],
            colWidths=[CW - 54*mm, 54*mm]
        )
        gap_row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,-1), bg_col),
            ("LINEBEFORE",    (0,0),(0,-1), 3,   lc),
            ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(0,-1), 8),
            ("BOTTOMPADDING", (0,0),(0,-1), 8),
            ("LEFTPADDING",   (0,0),(0,-1), 10),
        ]))
        story.append(KeepTogether([gap_row, Spacer(1, 4*mm)]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════
    # PAGE 4 — STRENGTHS & NEXT STEPS
    # ══════════════════════════════════════════════════════════════
    story.append(_section_header("CONFIRMED STRENGTHS", S))
    story.append(Spacer(1, 4*mm))

    positives = report.get("positives", [])
    if ws.get("status") == "certified":
        positives = [{
            "icon":  "🏆",
            "title": f"{ws.get('scheme','WiredScore')} {ws.get('level','Certified')} Certified",
            "desc":  f"Manually verified {ws.get('verifiedAt','')} by {ws.get('verifiedBy','')}. "
                     "Differentiating asset credential — lead with this in owner and agent conversations.",
        }] + positives

    pos_rows = []
    for p in positives:
        row = Table(
            [[
                Paragraph(p["icon"], S["bold10"]),
                [
                    Paragraph(p["title"], S["bold9"]),
                    Paragraph(p["desc"],  S["body"]),
                ],
            ]],
            colWidths=[12*mm, CW-12*mm]
        )
        row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#f0fdf4")),
            ("LINEBEFORE",    (0,0),(0,-1),  3, GREEN),
            ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#86efac")),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        pos_rows.append(row)
        pos_rows.append(Spacer(1, 3*mm))

    story.extend(pos_rows)
    story.append(Spacer(1, 5*mm))

    # Next steps
    story.append(_section_header("RECOMMENDED NEXT STEPS", S))
    story.append(Spacer(1, 4*mm))

    steps = [
        "Progress WiredScore / SmartScore certification — Modern Networks are Accredited Professionals.",
        "Request a site survey to assess connectivity infrastructure and identify upgrade options.",
        "Present a Modern Networks managed services proposal aligned to the gaps in this briefing.",
        "Follow up on EPC compliance timeline with the building owner — 2027 minimum C regulations.",
        "Review cybersecurity and insurance compliance posture across the building.",
    ]
    for i, step in enumerate(steps, 1):
        row = Table(
            [[Paragraph(str(i), S["teal"]), Paragraph(step, S["body"])]],
            colWidths=[8*mm, CW-8*mm]
        )
        row.setStyle(TableStyle([
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, MGREY),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        story.append(row)

    story.append(Spacer(1, 6*mm))

    # Footer branding block
    footer_t = Table(
        [[
            Paragraph(
                "Modern Networks  ·  modern-networks.co.uk  ·  "
                "WiredScore & SmartScore Accredited Professionals  ·  2,000+ UK properties",
                S["small"]
            ),
            Paragraph("CONFIDENTIAL — INTERNAL USE ONLY", S["mono"]),
        ]],
        colWidths=[CW * 0.65, CW * 0.35]
    )
    footer_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("ALIGN",         (1,0),(1,0),   "RIGHT"),
        ("RIGHTPADDING",  (1,0),(1,0),   8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(footer_t)

    def _footer(canvas, doc):
        _footer_cb(canvas, doc, pc, f"{ANGLE_TITLES.get(angle,'')} Briefing")

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def generate_portfolio_pdf(reports: list, client_name: str, staff: str) -> bytes:
    """Clean portfolio summary PDF."""
    buf = io.BytesIO()
    S   = _styles()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=M, rightMargin=M,
        topMargin=M, bottomMargin=20*mm,
    )
    story  = []
    sorted_r   = sorted(reports, key=lambda r: r.get("score", 0))
    avg_score  = round(sum(r.get("score",0) for r in sorted_r) / len(sorted_r)) if sorted_r else 0
    total_gaps = sum(len(r.get("gaps",[])) for r in sorted_r)

    # Cover
    story.append(Paragraph("INTERNAL  ·  MODERN NETWORKS PORTFOLIO BRIEFING", S["mono_b"]))
    story.append(HRFlowable(width=CW, thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(f"Modern Networks  |  Portfolio Intelligence", S["teal"]))
    story.append(Paragraph(
        f"Prepared by: {staff}  ·  {datetime.now().strftime('%d %b %Y')}",
        S["mono"]
    ))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(client_name or "Portfolio Assessment", S["h1"]))
    story.append(Spacer(1, 4*mm))

    # Summary stats
    stats_row = Table(
        [[
            [Paragraph(str(len(sorted_r)), ParagraphStyle("sn",fontName="Helvetica-Bold",fontSize=24,textColor=NAVY,leading=28)),
             Paragraph("Properties", S["small"])],
            [Paragraph(f"{avg_score}/100", ParagraphStyle("sn2",fontName="Helvetica-Bold",fontSize=24,textColor=_score_colour(avg_score),leading=28)),
             Paragraph("Average Score", S["small"])],
            [Paragraph(str(total_gaps), ParagraphStyle("sn3",fontName="Helvetica-Bold",fontSize=24,textColor=AMBER,leading=28)),
             Paragraph("Total Gaps", S["small"])],
            [Paragraph(str(sum(1 for r in sorted_r if r.get("score",0)<60)),
                       ParagraphStyle("sn4",fontName="Helvetica-Bold",fontSize=24,textColor=RED,leading=28)),
             Paragraph("Urgent (<60)", S["small"])],
        ]],
        colWidths=[CW/4]*4
    )
    stats_row.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("LINEBEFORE",    (1,0),(3,-1),  0.5, MGREY),
    ]))
    story.append(stats_row)
    story.append(PageBreak())

    # Ranked table
    story.append(_section_header("PORTFOLIO RANKING — LOWEST SCORE FIRST", S))
    story.append(Spacer(1, 4*mm))

    hdr = [Paragraph(h, S["mono_b"]) for h in
           ["#","POSTCODE","SCORE","CRITICAL","TOP PRIORITY GAP","MN SERVICE"]]
    table_rows = [hdr]
    cws = [8*mm, 24*mm, 18*mm, 16*mm, CW-102*mm, 36*mm]

    for i, r in enumerate(sorted_r, 1):
        sc   = _score_colour(r.get("score",0))
        crit = sum(1 for g in r.get("gaps",[]) if g.get("sev")=="critical")
        tg   = r.get("gaps",[{}])[0]
        table_rows.append([
            Paragraph(str(i), S["bold9"]),
            Paragraph(r.get("postcode",""), S["bold9"]),
            Paragraph(
                f'<font color="{sc.hexval()}"><b>{r.get("score",0)}</b></font>',
                ParagraphStyle("sc3",fontName="Helvetica-Bold",fontSize=13,leading=16,textColor=BLACK)
            ),
            Paragraph(
                f'<font color="{RED.hexval()}"><b>{crit}</b></font>',
                S["bold9"]
            ),
            Paragraph(f'{tg.get("icon","")} {tg.get("title","—")[:48]}', S["small"]),
            Paragraph(tg.get("service","—").split("\n")[0][:26], S["small"]),
        ])

    t = Table(table_rows, colWidths=cws)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
        ("BACKGROUND",    (0,1),(-1,-1), WHITE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LGREY]),
        ("LINEBELOW",     (0,0),(-1,-1), 0.3, MGREY),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(t)
    story.append(PageBreak())

    # Individual summaries
    for r in sorted_r:
        sc   = _score_colour(r.get("score",0))
        crit = sum(1 for g in r.get("gaps",[]) if g["sev"]=="critical")
        adv  = sum(1 for g in r.get("gaps",[]) if g["sev"]=="advisory")

        story.append(Paragraph(
            f'{r.get("postcode","")}  —  '
            f'<font color="{sc.hexval()}"><b>{r.get("score",0)}/100  {r.get("scoreLabel","")}</b></font>',
            S["h2"]
        ))
        story.append(Paragraph(
            f'{crit} critical gaps  ·  {adv} advisory  ·  Saved {r.get("savedAt","")}',
            S["small"]
        ))
        story.append(Spacer(1, 3*mm))

        for g in r.get("gaps",[])[:4]:
            lc  = _sev_colour(g["sev"])
            row = Table(
                [[
                    Paragraph(g["sev"].upper(), ParagraphStyle(
                        "sl3", fontName="Courier-Bold", fontSize=7,
                        textColor=lc, leading=10
                    )),
                    Paragraph(f'{g["icon"]} {g["title"]}', S["bold9"]),
                    Paragraph(g["service"].split("\n")[0], S["teal"]),
                ]],
                colWidths=[16*mm, CW-60*mm, 44*mm]
            )
            row.setStyle(TableStyle([
                ("LINEBEFORE",    (0,0),(0,-1), 3,   lc),
                ("LINEBELOW",     (0,0),(-1,-1), 0.3, MGREY),
                ("TOPPADDING",    (0,0),(-1,-1), 4),
                ("BOTTOMPADDING", (0,0),(-1,-1), 4),
                ("LEFTPADDING",   (0,0),(-1,-1), 6),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("BACKGROUND",    (0,0),(-1,-1), WHITE),
            ]))
            story.append(row)

        story.append(Spacer(1, 5*mm))
        story.append(_divider())

    def _pfooter(canvas, doc):
        _footer_cb(canvas, doc, client_name or "Portfolio", "Portfolio Report")

    doc.build(story, onFirstPage=_pfooter, onLaterPages=_pfooter)
    return buf.getvalue()


def generate_amalgamated_pdf(reports: list, staff: str) -> bytes:
    """Amalgamated multi-site briefing PDF."""
    return generate_portfolio_pdf(reports, "Multi-Site Amalgamated Briefing", staff)