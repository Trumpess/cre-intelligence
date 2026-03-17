"""
pdf_export.py
Generates internal briefing PDFs using ReportLab.
Matches the dark-themed design of the HTML tool but adapted for print.
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

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#0b1829")
NAVY_MID  = colors.HexColor("#161b26")
NAVY_LITE = colors.HexColor("#1c2333")
TEAL      = colors.HexColor("#00c8f0")
TEAL_DIM  = colors.HexColor("#0099b8")
AMBER     = colors.HexColor("#f5a623")
RED       = colors.HexColor("#f04f4f")
GREEN     = colors.HexColor("#3dd68c")
WHITE     = colors.HexColor("#e8edf5")
MUTED     = colors.HexColor("#6b7a99")
DIM       = colors.HexColor("#3d4f6b")
PAPER     = colors.HexColor("#f1f4f8")

W, H = A4
M = 16 * mm


def _sev_colour(sev: str) -> colors.Color:
    return {"critical": RED, "advisory": AMBER, "unconfirmed": AMBER}.get(sev, AMBER)


def _score_colour(score: int) -> colors.Color:
    if score >= 75: return GREEN
    if score >= 55: return AMBER
    return RED


def _styles():
    base = getSampleStyleSheet()
    def S(name, **kwargs):
        return ParagraphStyle(name, parent=base["Normal"], **kwargs)
    return {
        "mono9":   S("mono9",   fontName="Courier",      fontSize=7,  textColor=MUTED,  leading=10),
        "mono9t":  S("mono9t",  fontName="Courier",      fontSize=7,  textColor=TEAL,   leading=10),
        "mono9r":  S("mono9r",  fontName="Courier",      fontSize=7,  textColor=RED,    leading=10),
        "mono9a":  S("mono9a",  fontName="Courier",      fontSize=7,  textColor=AMBER,  leading=10),
        "mono9g":  S("mono9g",  fontName="Courier",      fontSize=7,  textColor=GREEN,  leading=10),
        "body":    S("body",    fontName="Helvetica",    fontSize=8,  textColor=MUTED,  leading=12),
        "bodyW":   S("bodyW",   fontName="Helvetica",    fontSize=8,  textColor=WHITE,  leading=12),
        "bold9":   S("bold9",   fontName="Helvetica-Bold",fontSize=9, textColor=WHITE,  leading=12),
        "bold10":  S("bold10",  fontName="Helvetica-Bold",fontSize=10,textColor=WHITE,  leading=14),
        "bold12":  S("bold12",  fontName="Helvetica-Bold",fontSize=12,textColor=WHITE,  leading=16),
        "bold18":  S("bold18",  fontName="Helvetica-Bold",fontSize=18,textColor=WHITE,  leading=22),
        "h_teal":  S("h_teal",  fontName="Helvetica-Bold",fontSize=11,textColor=TEAL,   leading=14),
        "small":   S("small",   fontName="Helvetica",    fontSize=7,  textColor=MUTED,  leading=10),
        "smallW":  S("smallW",  fontName="Helvetica",    fontSize=7,  textColor=WHITE,  leading=10),
        "italic":  S("italic",  fontName="Helvetica-Oblique",fontSize=8,textColor=MUTED,leading=12),
    }


def _coloured_table(rows, col_widths, row_heights=None, style_cmds=None):
    t = Table(rows, colWidths=col_widths, rowHeights=row_heights)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_MID),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",(0, 0), (-1, -1), 6),
        ("RIGHTPADDING",(0,0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0,0),(-1, -1), 5),
        ("GRID",       (0, 0), (-1, -1), 0.3, DIM),
    ]
    if style_cmds:
        cmds.extend(style_cmds)
    t.setStyle(TableStyle(cmds))
    return t


def _header_bar(text: str, styles: dict) -> Table:
    """Full-width dark header bar."""
    t = Table([[Paragraph(text, styles["mono9t"])]], colWidths=[W - 2 * M])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_LITE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0,0), (-1, -1), 6),
        ("LINEBELOW",   (0, 0), (-1, -1), 0.5, TEAL_DIM),
    ]))
    return t


def generate_briefing_pdf(report: dict, angle: str) -> bytes:
    """Generate a 4-page internal briefing PDF for a single property."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=14 * mm,
        title=f"MN Briefing — {report.get('postcode', '')}",
    )
    S = _styles()
    story = []
    CW = W - 2 * M
    P = report.get("prospect", {})
    ws = report.get("wiredScore", {})
    score = report.get("score", 0)
    sc = _score_colour(score)

    ANGLES = {
        "owner":      "Building Owner — asset value, EPC risk, valuation uplift",
        "agent":      "Managing Agent — occupier satisfaction, churn, day-one connectivity",
        "management": "Building Management — operational resilience, security, insurance compliance",
    }
    angle_desc = ANGLES.get(angle, "")

    # ── PAGE 1: COVER ─────────────────────────────────────────────────────────
    # Classification strip
    t = Table([[Paragraph("INTERNAL — MODERN NETWORKS SALES INTELLIGENCE  ·  NOT FOR EXTERNAL DISTRIBUTION", S["mono9t"])]],
              colWidths=[CW])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,-1), NAVY_LITE),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("LINEBELOW",(0,0),(-1,-1),1,TEAL),
    ]))
    story.append(t)
    story.append(Spacer(1, 10*mm))

    # Logo + ref
    story.append(Paragraph("Modern Networks  |  Sales Intelligence Platform", S["h_teal"]))
    story.append(Paragraph(
        f"Ref: MN-{report.get('postcode','').replace(' ','')}  ·  "
        f"Prepared by: {P.get('staff','MN Staff')}  ({P.get('initials','MN')})  ·  {report.get('savedAt','')}",
        S["mono9"]
    ))
    story.append(HRFlowable(width=CW, thickness=0.5, color=TEAL_DIM))
    story.append(Spacer(1, 6*mm))

    # Title + score side by side
    postcode_str = report.get("postcode", "")
    company_str  = P.get("company", "")
    title_text   = f"{company_str} — {postcode_str}" if company_str else f"Building Assessment — {postcode_str}"

    score_para = Paragraph(f'<font size="28" color="{sc.hexval()}">{score}</font><br/>'
                           f'<font size="8" color="{MUTED.hexval()}">/100</font><br/>'
                           f'<font size="7" color="{sc.hexval()}">{report.get("scoreLabel","")}</font>',
                           ParagraphStyle("sc", fontName="Helvetica-Bold", alignment=TA_CENTER))
    title_col = [
        Paragraph(title_text, S["bold18"]),
        Spacer(1, 2*mm),
        Paragraph(angle_desc, S["italic"]),
    ]
    header_row = Table(
        [[title_col, score_para]],
        colWidths=[CW - 35*mm, 35*mm]
    )
    header_row.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LEFTPADDING",(0,0),(0,-1),8),
        ("TOPPADDING",(0,0),(-1,-1),10),
        ("BOTTOMPADDING",(0,0),(-1,-1),10),
    ]))
    story.append(header_row)
    story.append(Spacer(1, 5*mm))

    # Prospect details table
    def _prow(label, value):
        return [Paragraph(label, S["mono9"]), Paragraph(str(value) if value else "—", S["bold9"])]

    prospect_rows = [
        _prow("COMPANY",  P.get("company","")),
        _prow("CONTACT",  P.get("contact","")),
        _prow("TITLE",    P.get("title","")),
        _prow("EMAIL",    P.get("email","")),
        _prow("PHONE",    P.get("phone","")),
        _prow("STAGE",    P.get("stage","")),
        _prow("MEETING",  P.get("meeting","")),
        _prow("ANGLE",    angle_desc[:50]),
    ]
    # Split into 2 columns
    half = len(prospect_rows) // 2
    left_rows  = prospect_rows[:half]
    right_rows = prospect_rows[half:]
    col_w = (CW - 6*mm) / 2
    for lr, rr in zip(left_rows, right_rows):
        t = Table([lr + [""] + rr], colWidths=[22*mm, col_w-25*mm, 3*mm, 22*mm, col_w-25*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
            ("LINEBELOW",(0,0),(-1,-1),0.2,DIM),
            ("TOPPADDING",(0,0),(-1,-1),4),
            ("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LEFTPADDING",(0,0),(-1,-1),6),
        ]))
        story.append(t)
    story.append(Spacer(1, 4*mm))

    # WiredScore status
    ws_status = ws.get("status","unconfirmed")
    ws_col = GREEN if ws_status=="certified" else RED if ws_status=="not-certified" else AMBER
    ws_text = (
        f"CERTIFIED — {ws.get('scheme','')} {ws.get('level','')}  ·  Verified {ws.get('verifiedAt','')} by {ws.get('verifiedBy','')}"
        if ws_status == "certified" else
        "NOT CERTIFIED — WiredScore AP Services conversation applicable"
        if ws_status == "not-certified" else
        "UNCONFIRMED — Manual verification required via wiredscore.com/certified-buildings"
    )
    ws_table = Table(
        [[Paragraph("WIREDSCORE / SMARTSCORE", S["mono9t"]),
          Paragraph(ws_text, ParagraphStyle("ws", fontName="Helvetica-Bold", fontSize=8, textColor=ws_col, leading=11))]],
        colWidths=[42*mm, CW-42*mm]
    )
    ws_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
        ("LINEBELOW",(0,0),(-1,-1),0.5,ws_col),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(ws_table)
    story.append(Spacer(1, 3*mm))

    # Internal notes
    if P.get("notes"):
        notes_t = Table(
            [[Paragraph("INTERNAL NOTES", S["mono9a"]),
              Paragraph(P["notes"][:300], S["body"])]],
            colWidths=[28*mm, CW-28*mm]
        )
        notes_t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
            ("LINEBELOW",(0,0),(-1,-1),0.5,AMBER),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(notes_t)

    story.append(PageBreak())

    # ── PAGE 2: DATA OVERVIEW ─────────────────────────────────────────────────
    story.append(_header_bar("DATA OVERVIEW", S))
    story.append(Spacer(1, 4*mm))

    metrics = report.get("metrics", {})
    metric_labels = {
        "connectivity": "Connectivity",
        "epc":          "Energy / EPC",
        "occupiers":    "Occupier Profile",
        "flood":        "Flood Risk",
        "mobile":       "Mobile Indoor",
        "crime":        "Crime Profile",
    }
    metric_rows = []
    items = list(metrics.items())
    for i in range(0, len(items), 3):
        chunk = items[i:i+3]
        row = []
        for k, v in chunk:
            lc = GREEN if v.get("status")=="good" else AMBER if v.get("status")=="warn" else RED
            cell = [
                Paragraph(metric_labels.get(k, k).upper(), S["mono9"]),
                Paragraph(f'<font color="{lc.hexval()}">{v.get("value","—")}</font>',
                          ParagraphStyle("mv", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=WHITE)),
                Paragraph(v.get("detail","").replace("\n","  ·  "), S["small"]),
            ]
            row.append(cell)
        while len(row) < 3:
            row.append([""])
        mw = CW / 3 - 1*mm
        t = Table([row], colWidths=[mw, mw, mw])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),7),
            ("BOTTOMPADDING",(0,0),(-1,-1),7),
            ("LEFTPADDING",(0,0),(-1,-1),7),
            ("GRID",(0,0),(-1,-1),0.3,DIM),
        ]))
        metric_rows.append(t)
        metric_rows.append(Spacer(1, 2*mm))

    story.extend(metric_rows)
    story.append(Spacer(1, 5*mm))

    # Talking points
    from scoring import WEIGHTS
    angle_copy = {
        "owner": {
            "title": "SALES ANGLE — Building Owner",
            "points": [
                'Asset value: "Buildings with 1Gbps and WiredScore certification achieve 4.9% higher valuations."',
                'Regulatory exposure: "EPC compliance risk is a direct threat to lettability under proposed 2027 legislation."',
                'Occupier retention: "19.4% lower tenant churn where buildings have managed digital infrastructure."',
                'WiredScore: "Modern Networks are WiredScore Accredited Professionals. Most buildings certify within 60 days."',
            ]
        },
        "agent": {
            "title": "SALES ANGLE — Managing Agent",
            "points": [
                'Tenant complaints: "Connectivity and mobile signal are the top two complaint categories in multi-tenant buildings."',
                'Day-one connectivity: "Zero onboarding delays when MN provides day-one managed connectivity."',
                'Portfolio WiredScore: "We work with CBRE, JLL, Savills and C&W — portfolio certification at scale."',
                'Single managed service: "One contract, one invoice, one point of contact across all managed buildings."',
            ]
        },
        "management": {
            "title": "SALES ANGLE — Building Management",
            "points": [
                'Insurance compliance: "Insurers require demonstrable cybersecurity controls. We provide the managed firewall needed."',
                'Regulatory compliance: "ISO 27001 and GDPR obligations met via single managed service with regular audits."',
                'Operational resilience: "Resilient managed connectivity with geographic redundancy keeps building systems online."',
                'Single point of accountability: "One managed services partner for network, security, and cloud across 2,000+ UK properties."',
            ]
        },
    }
    ac = angle_copy.get(angle, angle_copy["owner"])
    story.append(_header_bar(ac["title"], S))
    story.append(Spacer(1, 3*mm))
    for pt in ac["points"]:
        row = Table([[Paragraph("→", S["mono9t"]), Paragraph(pt, S["body"])]], colWidths=[6*mm, CW-6*mm])
        row.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),
            ("LINEBELOW",(0,0),(-1,-1),0.2,DIM),
        ]))
        story.append(row)
    story.append(PageBreak())

    # ── PAGE 3: GAPS ──────────────────────────────────────────────────────────
    story.append(_header_bar("GAPS & SERVICE OPPORTUNITIES", S))
    story.append(Spacer(1, 4*mm))

    gaps = report.get("gaps", [])
    for g in gaps:
        lc = _sev_colour(g["sev"])
        sev_label = g["sev"].upper()
        gap_rows = [
            [Paragraph(sev_label, ParagraphStyle("sl", fontName="Courier", fontSize=7,
                        textColor=lc, leading=10)),
             Paragraph(f'{g["icon"]} {g["title"]}', S["bold10"]),
             Paragraph("MN SERVICE", S["mono9t"]),
             Paragraph(g["service"].replace("\n"," · "), S["bold9"])],
            ["",
             Paragraph(g["desc"], S["body"]),
             "",
             Paragraph(g["detail"], S["small"])],
            ["",
             Paragraph(f'src: {g["source"]}', S["mono9"]),
             "", ""],
        ]
        t = Table(gap_rows, colWidths=[14*mm, CW-14*mm-52*mm, 18*mm, 34*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
            ("LINEBEFOREE",(0,0),(0,-1),3,lc),  # left accent
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),6),
            ("LINEBELOW",(0,-1),(-1,-1),0.3,DIM),
            ("SPAN",(0,1),(0,2)),
            ("SPAN",(2,1),(3,2)),
        ]))
        story.append(t)
        story.append(Spacer(1, 2*mm))

    story.append(PageBreak())

    # ── PAGE 4: STRENGTHS + ACTIONS ───────────────────────────────────────────
    story.append(_header_bar("CONFIRMED STRENGTHS", S))
    story.append(Spacer(1, 4*mm))

    positives = report.get("positives", [])
    for p in positives:
        t = Table(
            [[Paragraph(p["icon"], S["bold10"]),
              [Paragraph(p["title"], S["bold9"]),
               Paragraph(p["desc"], S["body"])]]],
            colWidths=[10*mm, CW-10*mm]
        )
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
            ("LINEBEFORE",(0,0),(0,-1),2,GREEN),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("TOPPADDING",(0,0),(-1,-1),5),
            ("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),7),
            ("LINEBELOW",(0,0),(-1,-1),0.2,DIM),
        ]))
        story.append(t)
        story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 5*mm))
    story.append(_header_bar("RECOMMENDED NEXT STEPS", S))
    story.append(Spacer(1, 3*mm))

    steps = [
        "Progress WiredScore / SmartScore certification conversation — MN are Accredited Professionals.",
        "Request a site survey to assess connectivity infrastructure and identify upgrade options.",
        "Present Modern Networks managed services proposal aligned to gaps identified in this briefing.",
        "Follow up on EPC compliance timeline with building owner — 2027 minimum C regulations.",
        "Review cybersecurity and insurance compliance posture across the building.",
    ]
    for i, step in enumerate(steps, 1):
        t = Table([[Paragraph(str(i), S["h_teal"]),
                    Paragraph(step, S["body"])]],
                  colWidths=[8*mm, CW-8*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),6),
            ("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),8),
            ("LINEBELOW",(0,0),(-1,-1),0.2,DIM),
        ]))
        story.append(t)

    story.append(Spacer(1, 5*mm))
    footer_t = Table(
        [[Paragraph("Modern Networks  ·  modern-networks.co.uk  ·  WiredScore & SmartScore Accredited Professionals  ·  2,000+ UK properties", S["small"]),
          Paragraph("CONFIDENTIAL — INTERNAL USE ONLY", S["mono9"])]],
        colWidths=[CW * 0.7, CW * 0.3]
    )
    footer_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY_LITE),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),("ALIGN",(1,0),(1,0),"RIGHT"),
    ]))
    story.append(footer_t)

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(DIM)
        canvas.drawCentredString(
            W / 2, 8*mm,
            f"Page {doc.page}  ·  MN Internal Briefing  ·  {postcode_str}  ·  CONFIDENTIAL"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def generate_portfolio_pdf(reports: list, client_name: str, staff: str) -> bytes:
    """Generate a multi-property portfolio intelligence summary PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=14*mm)
    S   = _styles()
    story = []
    CW  = W - 2*M
    sorted_r = sorted(reports, key=lambda r: r.get("score", 0))
    avg_score = round(sum(r.get("score",0) for r in sorted_r) / len(sorted_r)) if sorted_r else 0
    total_gaps = sum(len(r.get("gaps",[])) for r in sorted_r)

    # Cover
    story.append(Paragraph("INTERNAL — MODERN NETWORKS SALES INTELLIGENCE", S["mono9t"]))
    story.append(HRFlowable(width=CW, color=TEAL, thickness=1))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Modern Networks  |  Portfolio Intelligence Report", S["h_teal"]))
    story.append(Paragraph(f"Prepared by: {staff}  ·  {datetime.now().strftime('%d %b %Y')}", S["mono9"]))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(client_name or "Portfolio Assessment", S["bold18"]))
    story.append(Paragraph(f"{len(sorted_r)} properties assessed", S["body"]))
    story.append(Spacer(1, 6*mm))

    stats = [[str(len(sorted_r)), f"{avg_score}/100", str(total_gaps),
              str(sum(1 for r in sorted_r if r.get("score",0)<60))],
             ["Properties", "Avg Score", "Total Gaps", "Urgent (<60)"]]
    st_t = Table([stats[0], stats[1]], colWidths=[CW/4]*4)
    st_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
        ("TEXTCOLOR",(0,0),(-1,0),TEAL.hexval()),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,0),18),
        ("FONTNAME",(0,1),(-1,1),"Helvetica"),
        ("FONTSIZE",(0,1),(-1,1),8),
        ("TEXTCOLOR",(0,1),(-1,1),MUTED.hexval()),
        ("ALIGN",(0,0),(-1,-1),"LEFT"),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",(0,0),(-1,-1),10),
    ]))
    story.append(st_t)
    story.append(PageBreak())

    # Ranked summary table
    story.append(_header_bar("PORTFOLIO RANKING — PRIORITY ORDER (LOWEST SCORE FIRST)", S))
    story.append(Spacer(1, 3*mm))
    hdr = [Paragraph(h, S["mono9t"]) for h in ["#","POSTCODE","SCORE","CRITICAL","TOP GAP","MN SERVICE"]]
    table_rows = [hdr]
    cws = [8*mm, 24*mm, 16*mm, 16*mm, CW-100*mm, 36*mm]
    for i, r in enumerate(sorted_r, 1):
        sc = _score_colour(r.get("score",0))
        crit = sum(1 for g in r.get("gaps",[]) if g.get("sev")=="critical")
        tg = r.get("gaps",[{}])[0]
        table_rows.append([
            Paragraph(str(i), S["h_teal"]),
            Paragraph(r.get("postcode",""), S["bold9"]),
            Paragraph(f'<font color="{sc.hexval()}">{r.get("score",0)}</font>',
                      ParagraphStyle("sc2",fontName="Helvetica-Bold",fontSize=13,leading=16,textColor=WHITE)),
            Paragraph(f'<font color="{RED.hexval()}">{crit}</font>', S["bold9"]),
            Paragraph(f'{tg.get("icon","")} {tg.get("title","—")[:50]}', S["body"]),
            Paragraph(tg.get("service","—").split("\n")[0][:28], S["small"]),
        ])
    t = Table(table_rows, colWidths=cws)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
        ("BACKGROUND",(0,0),(-1,0),NAVY_LITE),
        ("LINEBELOW",(0,0),(-1,-1),0.3,DIM),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),5),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(t)
    story.append(PageBreak())

    # Individual property summaries
    for r in sorted_r:
        sc = _score_colour(r.get("score",0))
        story.append(Paragraph(
            f'<font color="{TEAL.hexval()}">{r.get("postcode","")}</font>  —  '
            f'<font color="{sc.hexval()}">{r.get("score",0)}/100  {r.get("scoreLabel","")}</font>',
            S["bold12"]
        ))
        story.append(Spacer(1, 2*mm))
        for g in r.get("gaps", [])[:4]:
            lc = _sev_colour(g["sev"])
            t = Table([[Paragraph(g["sev"].upper(), ParagraphStyle("sl2",fontName="Courier",
                                 fontSize=6,textColor=lc,leading=9)),
                        Paragraph(f'{g["icon"]} {g["title"]}', S["bold9"]),
                        Paragraph(g["service"].split("\n")[0], S["small"])]],
                      colWidths=[12*mm, CW-52*mm, 40*mm])
            t.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,-1),NAVY_MID),
                ("LINEBEFORE",(0,0),(0,-1),2,lc),
                ("LINEBELOW",(0,0),(-1,-1),0.2,DIM),
                ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
                ("LEFTPADDING",(0,0),(-1,-1),6),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ]))
            story.append(t)
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width=CW, thickness=0.3, color=DIM))
        story.append(Spacer(1, 4*mm))

    def _pfooter(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 6)
        canvas.setFillColor(DIM)
        canvas.drawCentredString(W/2, 8*mm,
            f"Page {doc.page}  ·  MN Portfolio Report  ·  {client_name}  ·  CONFIDENTIAL")
        canvas.restoreState()

    doc.build(story, onFirstPage=_pfooter, onLaterPages=_pfooter)
    return buf.getvalue()


def generate_amalgamated_pdf(reports: list, staff: str) -> bytes:
    """
    Multi-site amalgamated briefing — executive summary + ranking +
    gap frequency analysis + individual property summaries + next steps.
    """
    # Reuse portfolio PDF for now with amalgamated title
    return generate_portfolio_pdf(reports, "Multi-Site Amalgamated Briefing", staff)
