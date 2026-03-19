"""
app.py — Modern Networks Building Intelligence Platform (Internal)
Run with: streamlit run app.py
"""

import streamlit as st
import time
from datetime import datetime

from api.os_names        import get_coordinates
from api.ofcom           import get_connectivity_data
from api.uprn            import get_uprn
from api.epc             import get_epc_data
from api.companies_house import get_occupier_data
from api.flood_risk      import get_flood_risk, get_flood_risk_by_postcode
from api.police          import get_crime_data
from scoring             import calculate_score, generate_gaps, generate_positives
from pdf_export          import generate_briefing_pdf, generate_portfolio_pdf, generate_amalgamated_pdf

st.set_page_config(
    page_title="MN Intelligence Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
body, .stApp { background:#f4f6f9; color:#1a2336; }
[data-testid="stSidebar"] { background:#0b1829; }
[data-testid="stSidebar"] * { color:#c4cfe8 !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] select {
    background:#1c2333 !important;
    color:#e8edf5 !important;
    border:1px solid #2a3347 !important;
    border-radius:5px !important;
}
[data-testid="stSidebar"] .stButton button {
    background:#00c8f0 !important;
    color:#0b1829 !important;
    font-weight:700 !important;
    border:none !important;
}
.stTabs [data-baseweb="tab-list"] {
    background:#fff;
    border-radius:8px;
    padding:4px;
    border:1px solid #e2e8f0;
    gap:0;
}
.stTabs [data-baseweb="tab"] {
    color:#64748b;
    background:transparent;
    border-radius:5px;
    padding:8px 20px;
    font-weight:500;
}
.stTabs [aria-selected="true"] {
    background:#0b1829 !important;
    color:#fff !important;
}
.card {
    background:#fff;
    border:1px solid #e2e8f0;
    border-radius:8px;
    padding:18px 20px;
    margin-bottom:12px;
}
.card-good  { border-left:4px solid #10b981; }
.card-warn  { border-left:4px solid #f59e0b; }
.card-bad   { border-left:4px solid #ef4444; }
.card-teal  { border-left:4px solid #00c8f0; }
.metric-val-good { color:#10b981; font-size:22px; font-weight:700; }
.metric-val-warn { color:#f59e0b; font-size:22px; font-weight:700; }
.metric-val-bad  { color:#ef4444; font-size:22px; font-weight:700; }
.metric-val-blue { color:#00c8f0; font-size:22px; font-weight:700; }
.label { font-size:10px; letter-spacing:1.5px; text-transform:uppercase;
         color:#94a3b8; font-family:monospace; margin-bottom:4px; }
.gap-critical { background:#fff5f5; border:1px solid #fca5a5;
                border-left:4px solid #ef4444; border-radius:6px;
                padding:14px 16px; margin-bottom:10px; }
.gap-advisory { background:#fffbeb; border:1px solid #fcd34d;
                border-left:4px solid #f59e0b; border-radius:6px;
                padding:14px 16px; margin-bottom:10px; }
.gap-unconfirmed { background:#f0f9ff; border:1px solid #7dd3fc;
                   border-left:4px solid #00c8f0; border-radius:6px;
                   padding:14px 16px; margin-bottom:10px; }
.pos-card { background:#f0fdf4; border:1px solid #86efac;
            border-left:4px solid #10b981; border-radius:6px;
            padding:12px 16px; margin-bottom:8px; }
.sev-critical    { background:#fee2e2; color:#ef4444; border-radius:3px;
                   padding:2px 8px; font-size:10px; font-family:monospace;
                   letter-spacing:1px; font-weight:600; }
.sev-advisory    { background:#fef3c7; color:#d97706; border-radius:3px;
                   padding:2px 8px; font-size:10px; font-family:monospace;
                   letter-spacing:1px; font-weight:600; }
.sev-unconfirmed { background:#e0f2fe; color:#0284c7; border-radius:3px;
                   padding:2px 8px; font-size:10px; font-family:monospace;
                   letter-spacing:1px; font-weight:600; }
.score-box { background:#0b1829; border-radius:10px; padding:20px;
             text-align:center; color:#fff; }
.company-pill { display:inline-block; background:#f1f5f9; border:1px solid #e2e8f0;
                border-radius:20px; padding:3px 12px; font-size:12px;
                color:#334155; margin:3px; }
.internal-badge { background:#fef3c7; color:#92400e; border:1px solid #fcd34d;
                  border-radius:4px; padding:3px 10px; font-size:10px;
                  font-family:monospace; letter-spacing:2px; }
h1, h2, h3 { color:#0b1829 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "saved_reports": [], "portfolio_results": [], "current_report": None,
    "ws_status": "unconfirmed", "ws_scheme": "", "ws_level": "",
    "ws_verified_by": "", "ws_verified_at": "", "selected_ids": set(),
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

ANGLES = {
    "Building Owner":      "owner",
    "Managing Agent":      "agent",
    "Building Management": "management",
}
ANGLE_MSG = {
    "owner":      "Owner angle — asset value, EPC compliance risk, 4.9% valuation uplift for 1Gbps-certified buildings.",
    "agent":      "Agent angle — occupier satisfaction, complaint reduction, day-one connectivity.",
    "management": "Management angle — operational resilience, security compliance, insurance requirements.",
}

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="internal-badge">INTERNAL USE ONLY</div>', unsafe_allow_html=True)
    st.markdown("## Modern Networks")
    st.caption("Building Intelligence Platform")
    st.divider()

    st.markdown("**Your Details**")
    staff_name     = st.text_input("Your name",      placeholder="e.g. Sarah Jones")
    staff_initials = st.text_input("Initials (PDF)", placeholder="SJ", max_chars=3)

    st.divider()
    st.markdown("**Property Lookup**")
    postcode_input = st.text_input("UK Postcode", placeholder="e.g. EC3V 1AB").strip().upper()
    angle_label    = st.selectbox("Sales angle", list(ANGLES.keys()))
    angle_key      = ANGLES[angle_label]

    st.divider()
    st.markdown("**Prospect Details**")
    p_company = st.text_input("Company name",    placeholder="Organisation name")
    p_contact = st.text_input("Contact name")
    p_title   = st.text_input("Job title")
    p_email   = st.text_input("Email")
    p_phone   = st.text_input("Phone")
    p_stage   = st.selectbox("Sales stage", [
        "", "Prospecting", "Qualified", "Meeting Booked",
        "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"
    ])
    p_meeting = st.date_input("Meeting date", value=None)
    p_notes   = st.text_area("Internal notes", height=90,
                              placeholder="Prior contact, known requirements…")

    st.divider()
    run = st.button("Run Intelligence Report", type="primary", use_container_width=True)


# ── TABS ──────────────────────────────────────────────────────────────────────
saved_count = len(st.session_state.saved_reports)
tab1, tab2, tab3 = st.tabs([
    "Assessment",
    "Portfolio",
    f"Saved Briefings ({saved_count})" if saved_count else "Saved Briefings"
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    if run:
        if not postcode_input:
            st.error("Enter a postcode to run an assessment.")
            st.stop()

        with st.status("Pulling intelligence…", expanded=True) as status:
            st.write("🗺 OS Data Hub — resolving postcode…")
            coords = get_coordinates(postcode_input)
            lat = coords.get("lat")
            lon = coords.get("lon")

            st.write("📡 Ofcom — connectivity data…")
            ofcom = get_connectivity_data(postcode_input)

            st.write("🏢 EPC Register — energy performance…")
            epc = get_epc_data(postcode_input)

            st.write("🏛 Companies House — occupier profile…")
            ch = get_occupier_data(postcode_input)

            if lat and lon:
                st.write("🌊 Environment Agency — flood risk…")
                flood = get_flood_risk_by_postcode(postcode_input)
                st.write("🔒 Police API — crime profile…")
                crime = get_crime_data(lat, lon)
                st.write("🔑 UPRN lookup…")
                uprn_result = get_uprn(lat, lon)
            else:
                flood = {"zone":"Unknown","zone_num":1,"flood_score":50,"risk_label":"Unknown","summary":"No coordinates","error":"No coords"}
                crime = {"crime_score":60,"risk_label":"Unknown","summary":"No coordinates","total_crimes":0,"top_categories":[],"period":"","error":"No coords"}
                uprn_result = {"uprn":"N/A","error":"No coords"}

            st.write("⚡ Building score…")

            st.session_state.ws_status     = "unconfirmed"
            st.session_state.ws_scheme     = ""
            st.session_state.ws_level      = ""
            st.session_state.ws_verified_by = ""
            st.session_state.ws_verified_at = ""

            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            gaps      = generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed")
            positives = generate_positives(ofcom, epc, ch, flood, crime)

            def _met(value, detail, status):
                return {"value": value, "detail": detail, "status": status}

            metrics = {
                "connectivity": _met(
                    ofcom.get("tier","Unknown"),
                    f"{'✓ FTTP full fibre confirmed' if ofcom.get('fttp') or ofcom.get('gigabit') else '✗ No full fibre — FTTC only'}\n"
                    f"{ofcom.get('4g_operators',0)}/4 operators indoor 4G · "
                    f"{'Indoor 5G: '+', '.join(ofcom.get('5g_good',[])) if ofcom.get('5g_good') else 'No indoor 5G'}",
                    "good" if ofcom.get("fttp") or ofcom.get("gigabit") else
                    "warn" if ofcom.get("sfbb") else "bad"
                ),
                "epc": _met(
                    f"EPC {epc.get('rating','?')}",
                    f"Score {epc.get('score',0)} · Potential {epc.get('potential_rating','?')}\n"
                    f"{'⚠ Below 2027 minimum (C)' if epc.get('below_2027') else '✓ Meets 2027 threshold'}"
                    f"{' · Expires '+epc.get('expiry_date','') if epc.get('expiry_date') else ''}",
                    "good" if epc.get("rating","") in ("A","B","C") and not epc.get("expires_soon")
                    else "warn" if epc.get("rating","") == "D" else "bad"
                ),
                "occupiers": _met(
                    f"{ch.get('active',0)} Companies",
                    f"{ch.get('profile_label','Unknown')}\n{ch.get('churn_estimate','Unknown')}\n"
                    f"Top names: {', '.join(ch.get('companies',[])[:3]) if ch.get('companies') else 'None found'}",
                    "good" if ch.get("active",0) > 20 else
                    "warn" if ch.get("active",0) > 5 else "bad"
                ),
                "flood": _met(
                    flood.get("zone","Unknown"),
                    flood.get("risk_label",""),
                    "good" if flood.get("zone_num",1)==1 else
                    "warn" if flood.get("zone_num",1)==2 else "bad"
                ),
                "mobile": _met(
                    f"{ofcom.get('4g_operators',0)}/4 Operators",
                    f"Good indoor 4G: {', '.join(ofcom.get('4g_good',[])) or 'None confirmed'}\n"
                    f"Indoor 5G: {', '.join(ofcom.get('5g_good',[])) or 'None confirmed'}",
                    "good" if ofcom.get("4g_operators",0)>=4 else
                    "warn" if ofcom.get("4g_operators",0)>=2 else "bad"
                ),
                "crime": _met(
                    crime.get("risk_label","Unknown"),
                    f"{crime.get('total_crimes',0)} crimes recorded · {crime.get('period','')}\n"
                    f"Top: {', '.join(c[0] for c in crime.get('top_categories',[])[:2]) or 'No data'}",
                    "good" if crime.get("crime_score",60)>=70 else
                    "warn" if crime.get("crime_score",60)>=50 else "bad"
                ),
            }

            prospect = {
                "company":  p_company, "contact": p_contact,
                "title":    p_title,   "email":   p_email,
                "phone":    p_phone,   "stage":   p_stage,
                "meeting":  str(p_meeting) if p_meeting else "",
                "notes":    p_notes,
                "staff":    staff_name or "MN Staff",
                "initials": (staff_initials or "MN").upper(),
            }

            report = {
                "id":          f"{postcode_input}_{int(time.time())}",
                "postcode":    postcode_input,
                "uprn":        uprn_result.get("uprn","N/A"),
                "lat": lat,    "lon": lon,
                "score":       score,
                "scoreLabel":  score_label,
                "scoreColour": score_colour,
                "savedAt":     datetime.now().strftime("%d %b %Y"),
                "angle":       angle_key,
                "prospect":    prospect,
                "metrics":     metrics,
                "gaps":        gaps,
                "positives":   positives,
                "raw":         {"ofcom":ofcom,"epc":epc,"ch":ch,"flood":flood,"crime":crime},
                "wiredScore":  {"status":"unconfirmed","scheme":"","level":"","verifiedBy":"","verifiedAt":""},
                "companies":   ch.get("companies", []),
            }
            st.session_state.current_report = report
            status.update(label="Report ready.", state="complete", expanded=False)

    # ── Display ────────────────────────────────────────────────────────────
    r = st.session_state.current_report

    if r is None:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;color:#94a3b8">
            <div style="font-size:48px;margin-bottom:16px">🔍</div>
            <h3 style="color:#64748b;font-size:20px;margin-bottom:8px">No briefing loaded</h3>
            <p style="font-size:14px;max-width:380px;margin:0 auto;line-height:1.7">
            Enter a postcode and prospect details in the sidebar,
            then click <strong style="color:#0b1829">Run Intelligence Report</strong>.
            </p>
        </div>""", unsafe_allow_html=True)
    else:
        P  = r["prospect"]
        ch = r["raw"]["ch"]

        # ── Header ─────────────────────────────────────────────────────────
        col_title, col_score = st.columns([3, 1])
        with col_title:
            st.markdown(f'<div class="label">UPRN {r["uprn"]}  ·  {r["savedAt"]}  ·  {P.get("staff","MN Staff")}</div>', unsafe_allow_html=True)
            title = f"{P.get('company','')} — {r['postcode']}" if P.get("company") else f"Building Assessment — {r['postcode']}"
            st.markdown(f"## {title}")
            crit  = sum(1 for g in r["gaps"] if g["sev"]=="critical")
            adv   = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
            st.markdown(
                f'<span style="color:#ef4444;font-weight:600">{crit} critical gaps</span>'
                f'<span style="color:#94a3b8"> · </span>'
                f'<span style="color:#f59e0b;font-weight:600">{adv} advisory</span>'
                f'<span style="color:#94a3b8"> · {len(r["positives"])} strengths confirmed</span>',
                unsafe_allow_html=True
            )
            st.caption(f"*{ANGLE_MSG[r.get('angle','owner')]}*")

        with col_score:
            sc = r["scoreColour"]
            st.markdown(
                f'<div class="score-box">'
                f'<div style="font-size:11px;letter-spacing:2px;color:#64748b;margin-bottom:4px">SCORE</div>'
                f'<div style="font-size:52px;font-weight:800;color:{sc};line-height:1">{r["score"]}</div>'
                f'<div style="font-size:11px;color:#475569;margin-top:2px">/ 100</div>'
                f'<div style="font-size:11px;color:{sc};margin-top:6px;font-weight:600">{r["scoreLabel"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # ── Action buttons ─────────────────────────────────────────────────
        ba1, ba2, ba3 = st.columns([1, 1, 3])
        with ba1:
            r["wiredScore"] = {
                "status":     st.session_state.ws_status,
                "scheme":     st.session_state.ws_scheme,
                "level":      st.session_state.ws_level,
                "verifiedBy": st.session_state.ws_verified_by,
                "verifiedAt": st.session_state.ws_verified_at,
            }
            r["gaps"] = generate_gaps(
                r["raw"]["ofcom"], r["raw"]["epc"], r["raw"]["ch"],
                r["raw"]["flood"], r["raw"]["crime"],
                st.session_state.ws_status
            )
            pdf_bytes = generate_briefing_pdf(r, r.get("angle","owner"))
            st.download_button(
                "⬇ Download Briefing PDF",
                data=pdf_bytes,
                file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with ba2:
            already = any(s["id"]==r["id"] for s in st.session_state.saved_reports)
            if already:
                st.button("✓ Saved", disabled=True, use_container_width=True)
            else:
                if st.button("🔖 Save Briefing", use_container_width=True):
                    st.session_state.saved_reports.append(dict(r))
                    st.success("Saved.")
                    st.rerun()

        st.divider()

        # ── WiredScore panel ───────────────────────────────────────────────
        ws_status = st.session_state.ws_status
        ws_icons  = {"certified":"🟢","not-certified":"🔴","unconfirmed":"🟡"}
        st.markdown(f"#### {ws_icons.get(ws_status,'🟡')} WiredScore / SmartScore Certification")

        wc1, wc2, wc3 = st.columns([2,1,1])
        with wc1:
            st.markdown(
                "No public API exists for WiredScore data. "
                "[Check the WiredScore map ↗](https://wiredscore.com/certified-buildings/) "
                "then record the result here."
            )
            new_status = st.radio(
                "Status",
                ["unconfirmed","certified","not-certified"],
                index=["unconfirmed","certified","not-certified"].index(ws_status),
                horizontal=True,
                format_func=lambda x: {"unconfirmed":"? Unconfirmed","certified":"✓ Certified","not-certified":"✕ Not Certified"}[x]
            )
            if new_status != ws_status:
                st.session_state.ws_status      = new_status
                st.session_state.ws_verified_by = (staff_initials or staff_name or "MN").upper()
                st.session_state.ws_verified_at = datetime.now().strftime("%d %b %Y")
                st.rerun()

        if st.session_state.ws_status == "certified":
            with wc2:
                scheme = st.selectbox("Scheme", ["","WiredScore","SmartScore","Both"])
                if scheme != st.session_state.ws_scheme:
                    st.session_state.ws_scheme = scheme
            with wc3:
                level = st.selectbox("Level", ["","Certified","Silver","Gold","Platinum"])
                if level != st.session_state.ws_level:
                    st.session_state.ws_level = level

        if st.session_state.ws_verified_at:
            st.caption(f"Recorded {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}")

        st.divider()

        # ── Metrics ────────────────────────────────────────────────────────
        st.markdown("#### Data Overview")
        metric_labels = {
            "connectivity":"Connectivity","epc":"Energy / EPC",
            "occupiers":"Occupier Profile","flood":"Flood Risk",
            "mobile":"Mobile Indoor","crime":"Crime Profile"
        }
        status_colours = {"good":"#10b981","warn":"#f59e0b","bad":"#ef4444"}
        metrics = r["metrics"]
        cols = st.columns(5)
        for i, (k, v) in enumerate({key:val for key,val in metrics.items() if key != "mobile"}.items()):
            sc = status_colours.get(v["status"],"#94a3b8")
            with cols[i % 3]:
                detail_html = v["detail"].replace("\n","<br>")
                st.markdown(
                    f'<div class="card card-{"good" if v["status"]=="good" else "warn" if v["status"]=="warn" else "bad"}">'
                    f'<div class="label">{metric_labels[k]}</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{sc};margin-bottom:5px">{v["value"]}</div>'
                    f'<div style="font-size:12px;color:#64748b;line-height:1.6">{detail_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # ── Companies list ─────────────────────────────────────────────────
        companies = r.get("companies", []) or ch.get("companies", [])
        if companies:
            st.markdown("#### Registered Companies at This Postcode")
            pills = "".join(f'<span class="company-pill">{c}</span>' for c in companies)
            st.markdown(
                f'<div class="card" style="line-height:2">{pills}'
                f'{"<span class=\"company-pill\" style=\"background:#e2e8f0\">+ more</span>" if ch.get("total",0) > len(companies) else ""}'
                f'</div>',
                unsafe_allow_html=True
            )

        st.divider()

        # ── Gaps ───────────────────────────────────────────────────────────
        live_gaps = generate_gaps(
            r["raw"]["ofcom"], r["raw"]["epc"], r["raw"]["ch"],
            r["raw"]["flood"], r["raw"]["crime"],
            st.session_state.ws_status
        )
        crit  = sum(1 for g in live_gaps if g["sev"]=="critical")
        adv   = sum(1 for g in live_gaps if g["sev"]=="advisory")
        uncon = sum(1 for g in live_gaps if g["sev"]=="unconfirmed")

        st.markdown(
            f'#### Gaps & Opportunities '
            f'<span style="font-size:13px;color:#ef4444;font-weight:600">{crit} critical</span>'
            f'<span style="color:#94a3b8"> · </span>'
            f'<span style="font-size:13px;color:#f59e0b;font-weight:600">{adv} advisory</span>'
            f'{f"<span style=\'color:#94a3b8\'> · </span><span style=\'font-size:13px;color:#0284c7;font-weight:600\'>{uncon} unconfirmed</span>" if uncon else ""}',
            unsafe_allow_html=True
        )

        for g in live_gaps:
            gc1, gc2 = st.columns([3, 1])
            with gc1:
                css = f"gap-{g['sev']}"
                badge = f'<span class="sev-{g["sev"]}">{g["sev"].upper()}</span>'
                st.markdown(
                    f'<div class="{css}">'
                    f'{badge}'
                    f'<div style="font-size:14px;font-weight:600;color:#0f172a;margin:5px 0">'
                    f'{g["icon"]} {g["title"]}</div>'
                    f'<div style="font-size:12.5px;color:#475569;line-height:1.7;margin-bottom:6px">{g["desc"]}</div>'
                    f'<div style="font-size:10.5px;color:#94a3b8;font-family:monospace">Source: {g["source"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with gc2:
                st.markdown(
                    f'<div class="card card-teal" style="height:100%">'
                    f'<div class="label">MN Service</div>'
                    f'<div style="font-size:13px;font-weight:600;color:#0b1829;margin-bottom:4px;line-height:1.5">'
                    f'{g["service"].replace(chr(10),"<br>")}</div>'
                    f'<div style="font-size:11.5px;color:#64748b;line-height:1.4">{g["detail"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.divider()

        # ── Positives ──────────────────────────────────────────────────────
        live_pos = list(generate_positives(
            r["raw"]["ofcom"], r["raw"]["epc"], r["raw"]["ch"],
            r["raw"]["flood"], r["raw"]["crime"]
        ))
        if st.session_state.ws_status == "certified":
            scheme_str = st.session_state.ws_scheme or "WiredScore"
            level_str  = st.session_state.ws_level  or "Certified"
            live_pos.insert(0, {
                "icon":  "🏆",
                "title": f"{scheme_str} {level_str} Certified",
                "desc":  f"Verified {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}. "
                         "Differentiating asset credential — lead with this in owner and agent conversations.",
            })

        st.markdown("#### Confirmed Strengths")
        pcols = st.columns(2)
        for i, p in enumerate(live_pos):
            with pcols[i % 2]:
                st.markdown(
                    f'<div class="pos-card">'
                    f'<span style="font-size:18px">{p["icon"]}</span>'
                    f'<strong style="color:#0f172a;margin-left:8px">{p["title"]}</strong>'
                    f'<div style="font-size:12.5px;color:#475569;margin-top:4px;line-height:1.6">{p["desc"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Portfolio Assessment")
    st.caption("Batch-assess multiple properties. One postcode per line, max 20.")

    col_in, col_opt = st.columns([2, 1])
    with col_in:
        pf_postcodes = st.text_area(
            "Postcodes",
            height=160,
            placeholder="EC3V 1AB\nSW1A 1AA\nCB4 0WS",
        )
    with col_opt:
        pf_client   = st.text_input("Client / Campaign name")
        pf_audience = st.selectbox("Angle", list(ANGLES.keys()), key="pf_angle")
        pf_run      = st.button("Run Portfolio →", type="primary", use_container_width=True)

    if pf_run and pf_postcodes.strip():
        pcs = list(dict.fromkeys([
            p.strip().upper() for p in pf_postcodes.strip().split("\n") if p.strip()
        ]))[:20]

        results = []
        prog = st.progress(0, text="Starting…")

        for i, pc in enumerate(pcs):
            prog.progress(i / len(pcs), text=f"Assessing {pc}…")
            coords = get_coordinates(pc)
            lat, lon = coords.get("lat"), coords.get("lon")
            ofcom  = get_connectivity_data(pc)
            epc    = get_epc_data(pc)
            ch     = get_occupier_data(pc)
            flood  = get_flood_risk_by_postcode(pc)
            crime  = get_crime_data(lat, lon)  if lat else {"crime_score":60,"risk_label":"Unknown","summary":"N/A","total_crimes":0,"top_categories":[],"period":"","error":"No coords"}
            uprn   = get_uprn(lat, lon)        if lat else {"uprn":"N/A"}
            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            results.append({
                "id": f"{pc}_{int(time.time())}_{i}",
                "postcode": pc, "uprn": uprn.get("uprn","N/A"),
                "lat": lat, "lon": lon,
                "score": score, "scoreLabel": score_label, "scoreColour": score_colour,
                "savedAt": datetime.now().strftime("%d %b %Y"),
                "angle": ANGLES[pf_audience],
                "prospect": {"company":"","contact":"","staff":staff_name or "MN Staff",
                             "initials":(staff_initials or "MN").upper(),
                             "notes":"","stage":"","title":"","email":"","phone":"","meeting":""},
                "gaps":      generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed"),
                "positives": generate_positives(ofcom, epc, ch, flood, crime),
                "metrics":   {},
                "raw":       {"ofcom":ofcom,"epc":epc,"ch":ch,"flood":flood,"crime":crime},
                "wiredScore":{"status":"unconfirmed","scheme":"","level":"","verifiedBy":"","verifiedAt":""},
                "companies": ch.get("companies",[]),
            })

        prog.progress(1.0, text="Complete.")
        st.session_state.portfolio_results = results

    pf_results = st.session_state.portfolio_results
    if pf_results:
        sorted_r = sorted(pf_results, key=lambda r: r["score"])
        avg = round(sum(r["score"] for r in sorted_r) / len(sorted_r))

        st.divider()
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Properties",   len(sorted_r))
        mc2.metric("Avg Score",    f"{avg}/100")
        mc3.metric("Total Gaps",   sum(len(r["gaps"]) for r in sorted_r))
        mc4.metric("Urgent (<60)", sum(1 for r in sorted_r if r["score"] < 60))

        ba1, ba2, _ = st.columns([1, 1, 3])
        with ba1:
            if st.button("🔖 Save All", use_container_width=True):
                added = sum(1 for r in sorted_r
                           if not any(s["id"]==r["id"] for s in st.session_state.saved_reports)
                           and not st.session_state.saved_reports.append(dict(r)))
                st.success(f"Saved.")
                st.rerun()
        with ba2:
            pdf_bytes = generate_portfolio_pdf(sorted_r, pf_client or "Portfolio", staff_name or "MN Staff")
            st.download_button("⬇ Portfolio PDF", data=pdf_bytes,
                               file_name=f"MN-Portfolio-{(pf_client or 'Report').replace(' ','-')}.pdf",
                               mime="application/pdf", use_container_width=True)

        st.markdown("#### Results — Lowest Score First")
        for i, r in enumerate(sorted_r, 1):
            sc   = r["scoreColour"]
            crit = sum(1 for g in r["gaps"] if g["sev"]=="critical")
            adv  = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
            with st.expander(f"#{i}  {r['postcode']}  —  {r['score']}/100  {r['scoreLabel']}  —  {crit} critical · {adv} advisory"):
                ec1, ec2 = st.columns([3, 1])
                with ec1:
                    for g in r["gaps"][:4]:
                        icon = "🔴" if g["sev"]=="critical" else "🟡"
                        st.markdown(f"{icon} **{g['icon']} {g['title']}**  →  *{g['service'].split(chr(10))[0]}*")
                    if r.get("companies"):
                        st.caption("Companies: " + ", ".join(r["companies"][:5]))
                with ec2:
                    already = any(s["id"]==r["id"] for s in st.session_state.saved_reports)
                    if not already:
                        if st.button(f"Save", key=f"save_pf_{r['id']}"):
                            st.session_state.saved_reports.append(dict(r))
                            st.rerun()
                    else:
                        st.caption("✓ Saved")
                    ipdf = generate_briefing_pdf(r, r.get("angle","owner"))
                    st.download_button("⬇ PDF", data=ipdf,
                                      file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                                      mime="application/pdf", key=f"pdf_pf_{r['id']}")
    elif not pf_run:
        st.info("Enter postcodes above and click Run Portfolio Assessment.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SAVED BRIEFINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    saved = st.session_state.saved_reports

    sh1, sh2 = st.columns([2, 2])
    with sh1:
        st.markdown("### Saved Briefings")
        st.caption("Select two or more to generate an amalgamated PDF.")
    with sh2:
        if saved:
            sa1, sa2, sa3 = st.columns(3)
            with sa1:
                if st.button("Select All", use_container_width=True):
                    st.session_state.selected_ids = {r["id"] for r in saved}
                    st.rerun()
            with sa2:
                if st.button("Clear All", use_container_width=True):
                    if st.session_state.get("confirm_clear"):
                        st.session_state.saved_reports = []
                        st.session_state.selected_ids  = set()
                        st.session_state.pop("confirm_clear", None)
                        st.rerun()
                    else:
                        st.session_state["confirm_clear"] = True
                        st.rerun()
            with sa3:
                sel = st.session_state.get("selected_ids", set())
                if len(sel) >= 2:
                    sel_reports = [r for r in saved if r["id"] in sel]
                    amalg = generate_amalgamated_pdf(sel_reports, staff_name or "MN Staff")
                    st.download_button(
                        f"⬇ Amalgamated ({len(sel_reports)})",
                        data=amalg,
                        file_name=f"MN-Amalgamated-{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

    if st.session_state.get("confirm_clear"):
        st.warning("Click Clear All again to confirm.")

    if not saved:
        st.info("No briefings saved yet. Run an assessment and click Save Briefing.")
    else:
        n_sel = len(st.session_state.get("selected_ids", set()))
        if n_sel > 0:
            st.caption(f"{n_sel} report{'s' if n_sel!=1 else ''} selected")

        cols = st.columns(5)
        for i, r in enumerate(saved):
            sel     = r["id"] in st.session_state.get("selected_ids", set())
            crit    = sum(1 for g in r["gaps"] if g["sev"]=="critical")
            adv     = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
            ws_s    = r.get("wiredScore",{}).get("status","unconfirmed")
            ws_icon = {"certified":"🟢","not-certified":"🔴","unconfirmed":"🟡"}.get(ws_s,"🟡")
            border  = "2px solid #00c8f0" if sel else "1px solid #e2e8f0"
            sc      = r["scoreColour"]

            with cols[i % 3]:
                st.markdown(
                    f'<div style="background:#fff;border:{border};border-radius:8px;'
                    f'padding:16px;margin-bottom:12px">'
                    f'<div style="font-size:10px;color:#94a3b8;font-family:monospace;'
                    f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px">'
                    f'{r["postcode"]}{" · "+r["prospect"].get("company","") if r["prospect"].get("company") else ""}</div>'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
                    f'<div style="font-size:15px;font-weight:700;color:#0f172a">'
                    f'{r["prospect"].get("company") or "Assessment — "+r["postcode"]}</div>'
                    f'<div style="font-size:28px;font-weight:800;color:{sc}">{r["score"]}</div>'
                    f'</div>'
                    f'<div style="font-size:12px;color:#64748b;margin:6px 0">'
                    f'{r["scoreLabel"]} · {r["savedAt"]}<br>'
                    f'<span style="color:#ef4444;font-weight:600">{crit} critical</span> · '
                    f'<span style="color:#f59e0b;font-weight:600">{adv} advisory</span>'
                    f'{" · <span style=\'color:#0b1829;font-weight:600\'>"+r["prospect"].get("stage","")+"</span>" if r["prospect"].get("stage") else ""}'
                    f'</div>'
                    f'<div style="font-size:12px;color:#64748b">{ws_icon} WiredScore: {ws_s}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                bc1, bc2, bc3, bc4 = st.columns(4)
                with bc1:
                    label = "☑ Desel" if sel else "☐ Select"
                    if st.button(label, key=f"sel_{r['id']}", use_container_width=True):
                        if sel:
                            st.session_state.selected_ids.discard(r["id"])
                        else:
                            st.session_state.selected_ids.add(r["id"])
                        st.rerun()
                with bc2:
                    spdf = generate_briefing_pdf(r, r.get("angle","owner"))
                    st.download_button("⬇ PDF", data=spdf,
                                      file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                                      mime="application/pdf", key=f"spdf_{r['id']}",
                                      use_container_width=True)
                with bc3:
                    if st.button("View", key=f"view_{r['id']}", use_container_width=True):
                        st.session_state.current_report   = r
                        st.session_state.ws_status        = r.get("wiredScore",{}).get("status","unconfirmed")
                        st.session_state.ws_scheme        = r.get("wiredScore",{}).get("scheme","")
                        st.session_state.ws_level         = r.get("wiredScore",{}).get("level","")
                        st.session_state.ws_verified_by   = r.get("wiredScore",{}).get("verifiedBy","")
                        st.session_state.ws_verified_at   = r.get("wiredScore",{}).get("verifiedAt","")
                        st.rerun()
                with bc4:
                    if st.button("✕", key=f"del_{r['id']}", use_container_width=True):
                        st.session_state.saved_reports = [
                            s for s in st.session_state.saved_reports if s["id"] != r["id"]
                        ]
                        st.session_state.selected_ids.discard(r["id"])
                        st.rerun()