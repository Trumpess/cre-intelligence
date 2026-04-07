"""
pdf_export.py
Clean internal briefing PDFs — white background, black text.
Includes market position verdict and sales meeting checklist.
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

W, H = A4
M    = 18 * mm
CW   = W - 2 * M

# ── Colours ───────────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0b1829")
TEAL   = colors.HexColor("#0099b8")
RED    = colors.HexColor("#dc2626")
AMBER  = colors.HexColor("#d97706")
GREEN  = colors.HexColor("#059669")
GREY   = colors.HexColor("#64748b")
LGREY  = colors.HexColor("#f1f5f9")
MGREY  = colors.HexColor("#e2e8f0")
BLACK  = colors.HexColor("#0f172a")
WHITE  = colors.white
CREAM  = colors.HexColor("#fffbeb")
LGREEN = colors.HexColor("#f0fdf4")
LRED   = colors.HexColor("#fff5f5")
LBLUE  = colors.HexColor("#f0f9ff")


def _score_colour(score):
    if score >= 75: return GREEN
    if score >= 55: return AMBER
    return RED


def _sev_colour(sev):
    return {"critical": RED, "advisory": AMBER, "unconfirmed": TEAL}.get(sev, AMBER)


def _verdict_colour(verdict):
    return {
        "Premium Positioning":  GREEN,
        "Below Market":         AMBER,
        "Urgent Action Needed": RED,
    }.get(verdict, GREY)


def _styles():
    b = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, parent=b["Normal"], **kw)
    return {
        "h1":     S("h1",  fontName="Helvetica-Bold",   fontSize=20, textColor=NAVY,  leading=26),
        "h2":     S("h2",  fontName="Helvetica-Bold",   fontSize=14, textColor=NAVY,  leading=18),
        "h3":     S("h3",  fontName="Helvetica-Bold",   fontSize=11, textColor=NAVY,  leading=14),
        "body":   S("body",fontName="Helvetica",         fontSize=9,  textColor=BLACK, leading=13),
        "bodyW":  S("bodyW",fontName="Helvetica",        fontSize=9,  textColor=WHITE, leading=13),
        "small":  S("sml", fontName="Helvetica",         fontSize=8,  textColor=GREY,  leading=11),
        "smallW": S("smlW",fontName="Helvetica",         fontSize=8,  textColor=WHITE, leading=11),
        "bold9":  S("b9",  fontName="Helvetica-Bold",    fontSize=9,  textColor=BLACK, leading=13),
        "bold10": S("b10", fontName="Helvetica-Bold",    fontSize=10, textColor=BLACK, leading=14),
        "bold11": S("b11", fontName="Helvetica-Bold",    fontSize=11, textColor=BLACK, leading=15),
        "mono":   S("mo",  fontName="Courier",           fontSize=7.5,textColor=GREY,  leading=10),
        "monob":  S("mob", fontName="Courier-Bold",      fontSize=7.5,textColor=NAVY,  leading=10),
        "teal":   S("te",  fontName="Helvetica-Bold",    fontSize=9,  textColor=TEAL,  leading=12),
        "tealS":  S("teS", fontName="Helvetica",         fontSize=8,  textColor=TEAL,  leading=11),
        "red":    S("re",  fontName="Helvetica-Bold",    fontSize=9,  textColor=RED,   leading=12),
        "green":  S("gr",  fontName="Helvetica-Bold",    fontSize=9,  textColor=GREEN, leading=12),
        "amber":  S("am",  fontName="Helvetica-Bold",    fontSize=9,  textColor=AMBER, leading=12),
        "italic": S("it",  fontName="Helvetica-Oblique", fontSize=9,  textColor=GREY,  leading=12),
        "whiteb": S("wb",  fontName="Helvetica-Bold",    fontSize=9,  textColor=WHITE, leading=13),
        "whiteh": S("wh",  fontName="Helvetica-Bold",    fontSize=13, textColor=WHITE, leading=17),
        "whiteS": S("ws",  fontName="Helvetica",         fontSize=8,  textColor=WHITE, leading=11),
    }


def _section_bar(title, S):
    t = Table([[Paragraph(title, S["whiteb"])]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    return t


def _divider():
    return HRFlowable(width=CW, thickness=0.5, color=MGREY, spaceAfter=4, spaceBefore=4)


def _footer_fn(postcode, label):
    def _fn(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GREY)
        canvas.drawString(M, 10*mm,
            f"Modern Networks — Internal Sales Briefing — {postcode} — CONFIDENTIAL")
        canvas.drawRightString(W-M, 10*mm, f"Page {doc.page}  ·  {label}")
        canvas.restoreState()
    return _fn


def generate_briefing_pdf(report: dict, angle: str) -> bytes:
    buf = io.BytesIO()
    S   = _styles()
    P   = report.get("prospect", {})
    ws  = report.get("wiredScore", {})
    pc  = report.get("postcode", "")
    score     = report.get("score", 0)
    sc_col    = _score_colour(score)
    position  = report.get("position", {})
    checklist = report.get("checklist", [])

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

    story = []

    # ══════════════════════════════════════════════════════
    # PAGE 1 — COVER
    # ══════════════════════════════════════════════════════

    # Classification bar
    t = Table([[Paragraph(
        "INTERNAL  ·  MODERN NETWORKS SALES BRIEFING  ·  NOT FOR EXTERNAL DISTRIBUTION",
        S["whiteb"]
    )]], colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    # Title + score
    company_str = P.get("company","")
    title_str   = f"{company_str} — {pc}" if company_str else f"Building Assessment — {pc}"

    score_content = [
        Paragraph(f'<font size="30" color="{sc_col.hexval()}"><b>{score}</b></font>', S["body"]),
        Paragraph("/100", S["small"]),
        Paragraph(report.get("scoreLabel",""), ParagraphStyle(
            "sl", fontName="Helvetica-Bold", fontSize=8, textColor=sc_col, leading=10
        )),
    ]

    title_content = [
        Paragraph(title_str, S["h1"]),
        Paragraph(
            f"UPRN {report.get('uprn','N/A')}  ·  {report.get('savedAt','')}  ·  "
            f"Prepared by {P.get('staff','MN Staff')} ({P.get('initials','MN')})",
            S["mono"]
        ),
        Spacer(1, 3*mm),
        Paragraph(
            f"Angle: {ANGLE_TITLES.get(angle,'')}",
            S["small"]
        ),
    ]

    header_t = Table(
        [[title_content, score_content]],
        colWidths=[CW-36*mm, 36*mm]
    )
    header_t.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(0,-1),  0),
        ("RIGHTPADDING", (0,0),(0,-1),  6),
        ("ALIGN",        (1,0),(1,-1),  "CENTER"),
        ("BACKGROUND",   (1,0),(1,-1),  LGREY),
        ("BOX",          (1,0),(1,-1),  0.5, MGREY),
        ("TOPPADDING",   (1,0),(1,-1),  8),
        ("BOTTOMPADDING",(1,0),(1,-1),  8),
    ]))
    story.append(header_t)
    story.append(_divider())
    story.append(Spacer(1, 3*mm))

    # Market Position Verdict
    if position:
        verdict      = position.get("verdict","")
        verdict_col  = _verdict_colour(verdict)
        verdict_icon = position.get("icon","")
        verdict_bg   = colors.HexColor(
            "#f0fdf4" if verdict=="Premium Positioning" else
            "#fffbeb" if verdict=="Below Market" else
            "#fff5f5"
        )

        story.append(_section_bar("MARKET POSITION VERDICT", S))
        story.append(Spacer(1, 3*mm))

        verdict_rows = [
            [Paragraph(f"{verdict_icon} {verdict}", ParagraphStyle(
                "verd", fontName="Helvetica-Bold", fontSize=14,
                textColor=verdict_col, leading=18
            ))],
            [Paragraph(position.get("headline",""), S["bold10"])],
            [Spacer(1, 2*mm)],
            [Paragraph(position.get("detail",""), S["body"])],
            [Spacer(1, 2*mm)],
            [Paragraph(f"MN Opportunity: {position.get('opportunity','')}", S["italic"])],
        ]
        vt = Table(verdict_rows, colWidths=[CW])
        vt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), verdict_bg),
            ("LINEBELOW",     (0,0),(-1,-1), 2, verdict_col),
            ("BOX",           (0,0),(-1,-1), 0.5, verdict_col),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ]))
        story.append(vt)
        story.append(Spacer(1, 4*mm))

    # Prospect details
    story.append(_section_bar("PROSPECT DETAILS", S))
    story.append(Spacer(1, 3*mm))

    fields = [
        ("COMPANY",  P.get("company","")),
        ("CONTACT",  P.get("contact","")),
        ("TITLE",    P.get("title","")),
        ("EMAIL",    P.get("email","")),
        ("PHONE",    P.get("phone","")),
        ("STAGE",    P.get("stage","")),
        ("MEETING",  P.get("meeting","")),
        ("ANGLE",    ANGLE_TITLES.get(angle,"")),
    ]
    lw = (CW - 6*mm) / 2
    half = len(fields) // 2
    for i in range(half):
        l  = fields[i]
        rf = fields[i+half] if i+half < len(fields) else ("","")
        row = Table(
            [[Paragraph(l[0],  S["mono"]),
              Paragraph(str(l[1])  or "—", S["bold9"]),
              Paragraph("",        S["mono"]),
              Paragraph(rf[0], S["mono"]),
              Paragraph(str(rf[1]) or "—", S["bold9"])]],
            colWidths=[24*mm, lw-27*mm, 6*mm, 24*mm, lw-27*mm]
        )
        row.setStyle(TableStyle([
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, MGREY),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ]))
        story.append(row)

    story.append(Spacer(1, 4*mm))

    # WiredScore
    ws_status = ws.get("status","unconfirmed")
    ws_col    = GREEN if ws_status=="certified" else RED if ws_status=="not-certified" else AMBER
    ws_text   = (
        f"CERTIFIED — {ws.get('scheme','')} {ws.get('level','')}  "
        f"(verified {ws.get('verifiedAt','')} by {ws.get('verifiedBy','')})"
        if ws_status=="certified" else
        "NOT CERTIFIED — WiredScore AP Services conversation applicable"
        if ws_status=="not-certified" else
        "STATUS UNCONFIRMED — verify at wiredscore.com/certified-buildings"
    )
    ws_t = Table(
        [[Paragraph("WIREDSCORE / SMARTSCORE", S["monob"]),
          Paragraph(ws_text, ParagraphStyle(
              "wst", fontName="Helvetica-Bold", fontSize=9, textColor=ws_col, leading=12
          ))]],
        colWidths=[44*mm, CW-44*mm]
    )
    ws_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("BOX",           (0,0),(-1,-1), 0.5, ws_col),
        ("LINEBELOW",     (0,0),(-1,-1), 2,   ws_col),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(ws_t)

    # Mobile Coverage
    mob      = report.get("mobile", {})
    MOB_OPS  = ["EE", "O2", "Three", "Vodafone"]
    MOB_COLS = {"Good": GREEN, "Variable": AMBER, "None": RED, "": GREY}

    def _mob_cell(op, data):
        indoor  = data.get("indoor",  "")
        outdoor = data.get("outdoor", "")
        ci = MOB_COLS.get(indoor,  GREY)
        co = MOB_COLS.get(outdoor, GREY)
        return [
            Paragraph(op, S["monob"]),
            Paragraph(
                f'<font color="{ci.hexval()}"><b>▲ {indoor or "—"}</b></font>',
                ParagraphStyle("mi", fontName="Helvetica-Bold", fontSize=8,
                               textColor=ci, leading=11)
            ),
            Paragraph(
                f'<font color="{co.hexval()}"><b>↑ {outdoor or "—"}</b></font>',
                ParagraphStyle("mo2", fontName="Helvetica-Bold", fontSize=8,
                               textColor=co, leading=11)
            ),
        ]

    mob_any = any(
        mob.get(op, {}).get("indoor") or mob.get(op, {}).get("outdoor")
        for op in MOB_OPS
    )

    story.append(Spacer(1, 3*mm))
    mob_cells = [_mob_cell(op, mob.get(op, {})) for op in MOB_OPS]
    mob_legend = [
        Paragraph("MOBILE COVERAGE", S["monob"]),
        Paragraph("▲ = Indoor  ↑ = Outdoor", S["small"]),
        Paragraph(
            f"{'Recorded ' + mob.get('verifiedAt','') + ' by ' + mob.get('verifiedBy','') if mob_any else 'Not yet recorded — check checker.ofcom.org.uk'}",
            S["mono"]
        ),
    ]
    mob_t = Table(
        [[mob_legend] + mob_cells],
        colWidths=[44*mm] + [(CW - 44*mm) / 4] * 4
    )
    mob_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LGREY),
        ("BACKGROUND",    (0, 0), (0, -1),  LGREY),
        ("BOX",           (0, 0), (-1, -1), 0.5, TEAL),
        ("LINEBELOW",     (0, 0), (-1, -1), 2,   TEAL),
        ("LINEBEFORE",    (1, 0), (-1, -1), 0.5, MGREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(mob_t)

    # Internal notes
    if P.get("notes"):
        story.append(Spacer(1, 3*mm))
        notes_t = Table(
            [[Paragraph("INTERNAL NOTES", S["monob"]),
              Paragraph(str(P["notes"])[:400], S["body"])]],
            colWidths=[28*mm, CW-28*mm]
        )
        notes_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), CREAM),
            ("BOX",           (0,0),(-1,-1), 0.5, AMBER),
            ("LINEBELOW",     (0,0),(-1,-1), 2,   AMBER),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        story.append(notes_t)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════
    # PAGE 2 — DATA OVERVIEW & GAPS
    # ══════════════════════════════════════════════════════
    story.append(_section_bar("BUILDING DATA OVERVIEW", S))
    story.append(Spacer(1, 4*mm))

    metrics = report.get("metrics", {})
    METRIC_LABELS = {
        "connectivity":"Connectivity","epc":"Energy / EPC",
        "occupiers":"Occupier Profile","flood":"Flood Risk","crime":"Crime Profile",
    }
    STATUS_COLS = {"good": GREEN, "warn": AMBER, "bad": RED}

    items = [(k,v) for k,v in metrics.items() if k != "mobile"]
    mw = (CW - 4*mm) / len(items) if items else CW

    if items:
        cells = []
        for k, v in items:
            lc = STATUS_COLS.get(v.get("status",""), GREY)
            cell = [
                Paragraph(METRIC_LABELS.get(k,k).upper(), S["mono"]),
                Paragraph(
                    f'<font color="{lc.hexval()}"><b>{v.get("value","—")}</b></font>',
                    ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=13,
                                   leading=17, textColor=BLACK)
                ),
                Paragraph(
                    v.get("detail","").replace("\n","  ·  ")[:120],
                    S["small"]
                ),
            ]
            cells.append(cell)

        t = Table([cells], colWidths=[mw]*len(items))
        t.setStyle(TableStyle([
            ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
            ("LINEBEFORE",    (1,0),(-1,-1), 0.5, MGREY),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        story.append(t)

    story.append(Spacer(1, 5*mm))

    # Companies
    companies = report.get("companies", [])
    if companies:
        story.append(Paragraph(
            "Registered organisations at this postcode: " +
            ", ".join(companies[:8]) +
            (f" + more" if len(companies) > 8 else ""),
            S["small"]
        ))
        story.append(Spacer(1, 4*mm))

    # Gaps
    story.append(_section_bar("GAPS & SERVICE OPPORTUNITIES", S))
    story.append(Spacer(1, 3*mm))

    gaps = report.get("gaps", [])
    crit_n = sum(1 for g in gaps if g["sev"]=="critical")
    adv_n  = sum(1 for g in gaps if g["sev"]=="advisory")
    story.append(Paragraph(
        f"{crit_n} critical  ·  {adv_n} advisory  ·  Each gap maps to a Modern Networks service",
        S["small"]
    ))
    story.append(Spacer(1, 4*mm))

    for g in gaps:
        lc     = _sev_colour(g["sev"])
        sev_lbl= g["sev"].upper()
        bg_col = LRED if g["sev"]=="critical" else CREAM if g["sev"]=="advisory" else LBLUE

        gap_content = [
            Paragraph(f"{sev_lbl}  ·  {g['icon']}  {g['title']}", ParagraphStyle(
                "gt", fontName="Helvetica-Bold", fontSize=10, textColor=lc, leading=14
            )),
            Spacer(1, 2*mm),
            Paragraph(g["desc"], S["body"]),
            Spacer(1, 1*mm),
            Paragraph(f"Source: {g['source']}", S["mono"]),
        ]
        if g.get("stat"):
            gap_content.append(Paragraph(f"Data: {g['stat']}", S["tealS"]))

        service_content = [
            Paragraph("MN SERVICE", S["monob"]),
            Spacer(1, 2*mm),
            Paragraph(g["service"].replace("\n", "  ·  "), S["bold9"]),
            Spacer(1, 1*mm),
            Paragraph(g["detail"], S["small"]),
        ]

        gap_t = Table(
            [[gap_content, service_content]],
            colWidths=[CW-56*mm, 56*mm]
        )
        gap_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(0,-1), bg_col),
            ("BACKGROUND",    (1,0),(1,-1), LGREY),
            ("LINEBEFORE",    (0,0),(0,-1), 3, lc),
            ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ]))
        story.append(KeepTogether([gap_t, Spacer(1, 4*mm)]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════
    # PAGE 3 — SALES MEETING CHECKLIST
    # ══════════════════════════════════════════════════════
    story.append(_section_bar("PRE-MEETING SALES CHECKLIST", S))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "Building-specific answers to the nine questions you will be asked in every commercial property sales meeting.",
        S["italic"]
    ))
    story.append(Spacer(1, 4*mm))

    for i, item in enumerate(checklist, 1):
        lc_q  = GREEN if item.get("strength") else AMBER
        bg_q  = LGREEN if item.get("strength") else CREAM

        q_rows = [
            [Paragraph(f"Q{i}. {item['q']}", S["bold10"])],
            [Paragraph(f"Evidence: {item['evidence']}", S["mono"])],
            [Spacer(1, 2*mm)],
            [Paragraph(item["answer"], S["body"])],
        ]
        q_t = Table(q_rows, colWidths=[CW])
        q_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bg_q),
            ("BACKGROUND",    (0,0),(-1,0),  NAVY),
            ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
            ("LINEBEFORE",    (0,0),(-1,-1), 3, lc_q),
            ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ]))
        story.append(KeepTogether([q_t, Spacer(1, 4*mm)]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════
    # PAGE 4 — STRENGTHS & NEXT STEPS
    # ══════════════════════════════════════════════════════
    story.append(_section_bar("CONFIRMED STRENGTHS", S))
    story.append(Spacer(1, 4*mm))

    positives = list(report.get("positives", []))
    if ws.get("status") == "certified":
        positives.insert(0, {
            "icon":  "🏆",
            "title": f"{ws.get('scheme','WiredScore')} {ws.get('level','Certified')} Certified",
            "desc":  f"Verified {ws.get('verifiedAt','')} by {ws.get('verifiedBy','')}. "
                     "4.9% higher valuations and 19.4% lower tenant churn for certified buildings.",
        })

    for p in positives:
        p_t = Table(
            [[Paragraph(str(p["icon"]), S["bold10"]),
              [Paragraph(p["title"], S["bold9"]),
               Paragraph(p["desc"],  S["body"])]]],
            colWidths=[12*mm, CW-12*mm]
        )
        p_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), LGREEN),
            ("LINEBEFORE",    (0,0),(0,-1),  3, GREEN),
            ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#86efac")),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        story.append(p_t)
        story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 4*mm))
    story.append(_section_bar("RECOMMENDED NEXT STEPS", S))
    story.append(Spacer(1, 4*mm))

    steps = [
        "Check WiredScore / SmartScore certification status and progress certification if uncertified — MN are Accredited Professionals.",
        "Request a site survey to assess connectivity infrastructure and identify full fibre upgrade options.",
        "Present a Modern Networks managed services proposal aligned to the gaps in this briefing.",
        "Follow up on EPC compliance timeline with the building owner — 2027 minimum C deadline.",
        "Review cybersecurity and insurance compliance posture — ISO 27001 managed security service.",
    ]
    for i, step in enumerate(steps, 1):
        s_t = Table(
            [[Paragraph(str(i), S["teal"]), Paragraph(step, S["body"])]],
            colWidths=[8*mm, CW-8*mm]
        )
        s_t.setStyle(TableStyle([
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, MGREY),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ]))
        story.append(s_t)

    story.append(Spacer(1, 5*mm))

    footer_t = Table(
        [[Paragraph(
              "Modern Networks  ·  modern-networks.co.uk  ·  "
              "WiredScore & SmartScore Accredited Professionals  ·  2,000+ UK properties",
              S["small"]),
          Paragraph("CONFIDENTIAL — INTERNAL USE ONLY", S["mono"])]],
        colWidths=[CW*0.65, CW*0.35]
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

    fn = _footer_fn(pc, f"{ANGLE_TITLES.get(angle,'')} Briefing")
    doc.build(story, onFirstPage=fn, onLaterPages=fn)
    return buf.getvalue()


def generate_portfolio_pdf(reports: list, client_name: str, staff: str) -> bytes:
    buf = io.BytesIO()
    S   = _styles()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M,
                            topMargin=M, bottomMargin=20*mm)
    story    = []
    sorted_r = sorted(reports, key=lambda r: r.get("score",0))
    avg      = round(sum(r.get("score",0) for r in sorted_r)/len(sorted_r)) if sorted_r else 0
    tot_gaps = sum(len(r.get("gaps",[])) for r in sorted_r)

    # Cover
    story.append(Paragraph("INTERNAL  ·  MODERN NETWORKS PORTFOLIO BRIEFING", S["monob"]))
    story.append(HRFlowable(width=CW, thickness=1, color=NAVY, spaceAfter=8))
    story.append(Paragraph(f"Modern Networks  |  Portfolio Intelligence", S["teal"]))
    story.append(Paragraph(
        f"Prepared by: {staff}  ·  {datetime.now().strftime('%d %b %Y')}",
        S["mono"]
    ))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(client_name or "Portfolio Assessment", S["h1"]))
    story.append(Spacer(1, 4*mm))

    stats_data = [
        [Paragraph(str(len(sorted_r)), ParagraphStyle("sn",fontName="Helvetica-Bold",fontSize=22,textColor=NAVY,leading=26)),
         Paragraph(f"{avg}/100", ParagraphStyle("sn2",fontName="Helvetica-Bold",fontSize=22,textColor=_score_colour(avg),leading=26)),
         Paragraph(str(tot_gaps), ParagraphStyle("sn3",fontName="Helvetica-Bold",fontSize=22,textColor=AMBER,leading=26)),
         Paragraph(str(sum(1 for r in sorted_r if r.get("score",0)<60)),
                   ParagraphStyle("sn4",fontName="Helvetica-Bold",fontSize=22,textColor=RED,leading=26))],
        [Paragraph("Properties",S["small"]),
         Paragraph("Avg Score",S["small"]),
         Paragraph("Total Gaps",S["small"]),
         Paragraph("Urgent",S["small"])],
    ]
    st_t = Table(stats_data, colWidths=[CW/4]*4)
    st_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LGREY),
        ("BOX",           (0,0),(-1,-1), 0.5, MGREY),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("LINEBEFORE",    (1,0),(3,-1),  0.5, MGREY),
    ]))
    story.append(st_t)
    story.append(PageBreak())

    # Ranked table
    story.append(_section_bar("PORTFOLIO RANKING — LOWEST SCORE FIRST", S))
    story.append(Spacer(1, 4*mm))

    hdr = [Paragraph(h, S["monob"]) for h in
           ["#","POSTCODE","SCORE","VERDICT","CRITICAL","TOP GAP","MN SERVICE"]]
    cws = [8*mm, 22*mm, 16*mm, 30*mm, 14*mm, CW-118*mm, 28*mm]
    table_rows = [hdr]

    for i, r in enumerate(sorted_r, 1):
        sc     = _score_colour(r.get("score",0))
        crit   = sum(1 for g in r.get("gaps",[]) if g.get("sev")=="critical")
        tg     = r.get("gaps",[{}])[0]
        pos_v  = r.get("position",{}).get("verdict","")
        pos_c  = _verdict_colour(pos_v)
        table_rows.append([
            Paragraph(str(i), S["bold9"]),
            Paragraph(r.get("postcode",""), S["bold9"]),
            Paragraph(f'<font color="{sc.hexval()}"><b>{r.get("score",0)}</b></font>',
                      ParagraphStyle("sc3",fontName="Helvetica-Bold",fontSize=13,leading=16,textColor=BLACK)),
            Paragraph(f'<font color="{pos_c.hexval()}">{pos_v}</font>',
                      ParagraphStyle("pv",fontName="Helvetica-Bold",fontSize=8,leading=11,textColor=BLACK)),
            Paragraph(f'<font color="{RED.hexval()}"><b>{crit}</b></font>', S["bold9"]),
            Paragraph(f'{tg.get("icon","")} {tg.get("title","—")[:40]}', S["small"]),
            Paragraph(tg.get("service","—").split("\n")[0][:22], S["tealS"]),
        ])

    t = Table(table_rows, colWidths=cws)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0),  WHITE),
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
        pos_v = r.get("position",{}).get("verdict","")

        story.append(Paragraph(
            f'{r.get("postcode","")}  —  '
            f'<font color="{sc.hexval()}"><b>{r.get("score",0)}/100  {r.get("scoreLabel","")}</b></font>',
            S["h2"]
        ))
        if pos_v:
            pvc = _verdict_colour(pos_v)
            story.append(Paragraph(
                f'<font color="{pvc.hexval()}"><b>{pos_v}</b></font>',
                S["bold9"]
            ))
        story.append(Paragraph(
            f'{crit} critical  ·  {adv} advisory  ·  Saved {r.get("savedAt","")}',
            S["small"]
        ))
        story.append(Spacer(1, 3*mm))

        for g in r.get("gaps",[])[:4]:
            lc  = _sev_colour(g["sev"])
            row = Table(
                [[Paragraph(g["sev"].upper(), ParagraphStyle(
                      "sl3",fontName="Courier-Bold",fontSize=7,textColor=lc,leading=10)),
                  Paragraph(f'{g["icon"]} {g["title"]}', S["bold9"]),
                  Paragraph(g["service"].split("\n")[0], S["tealS"])]],
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

    fn = _footer_fn(client_name or "Portfolio", "Portfolio Report")
    doc.build(story, onFirstPage=fn, onLaterPages=fn)
    return buf.getvalue()


def generate_amalgamated_pdf(reports: list, staff: str) -> bytes:
    return generate_portfolio_pdf(reports, "Multi-Site Amalgamated Briefing", staff)
