"""
app.py — Modern Networks Building Intelligence Platform (Internal)
"""

import streamlit as st
import time
from datetime import datetime

from api.os_names        import get_coordinates
from api.ofcom           import get_connectivity_data
from api.uprn            import get_uprn
from api.epc             import get_epc_data
from api.companies_house import get_occupier_data
from api.flood_risk      import get_flood_risk
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
body,.stApp{background:#f4f6f9;color:#0f172a}
[data-testid="stSidebar"]{background:#0b1829}
[data-testid="stSidebar"] *{color:#c4cfe8!important}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] select{
    background:#1c2333!important;color:#e8edf5!important;
    border:1px solid #2a3347!important;border-radius:5px!important}
[data-testid="stSidebar"] .stButton button{
    background:#00c8f0!important;color:#0b1829!important;
    font-weight:700!important;border:none!important;border-radius:6px!important}
.stTabs [data-baseweb="tab-list"]{
    background:#fff;border-radius:8px;padding:4px;
    border:1px solid #e2e8f0;gap:0}
.stTabs [data-baseweb="tab"]{
    color:#64748b;background:transparent;
    border-radius:5px;padding:8px 22px;font-weight:500}
.stTabs [aria-selected="true"]{background:#0b1829!important;color:#fff!important}
.mn-card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;
         padding:18px 20px;margin-bottom:12px}
.mn-card-good{border-left:4px solid #059669}
.mn-card-warn{border-left:4px solid #d97706}
.mn-card-bad{border-left:4px solid #dc2626}
.mn-card-blue{border-left:4px solid #0099b8}
.gap-critical{background:#fff5f5;border:1px solid #fca5a5;
              border-left:4px solid #dc2626;border-radius:8px;
              padding:16px 18px;margin-bottom:12px}
.gap-advisory{background:#fffbeb;border:1px solid #fcd34d;
              border-left:4px solid #d97706;border-radius:8px;
              padding:16px 18px;margin-bottom:12px}
.gap-unconfirmed{background:#f0f9ff;border:1px solid #7dd3fc;
                 border-left:4px solid #0099b8;border-radius:8px;
                 padding:16px 18px;margin-bottom:12px}
.pos-card{background:#f0fdf4;border:1px solid #86efac;
          border-left:4px solid #059669;border-radius:8px;
          padding:14px 18px;margin-bottom:10px}
.impact-tag{display:inline-block;background:#f1f5f9;color:#475569;
            border-radius:20px;padding:2px 10px;font-size:11px;
            margin-right:4px;margin-bottom:4px}
.stat-callout{background:#0b1829;color:#00c8f0;border-radius:6px;
              padding:8px 14px;font-size:12px;font-weight:600;
              display:inline-block;margin-top:8px}
.sev-badge-critical{background:#fee2e2;color:#dc2626;border-radius:4px;
                    padding:2px 9px;font-size:10px;font-family:monospace;
                    font-weight:700;letter-spacing:1px}
.sev-badge-advisory{background:#fef3c7;color:#b45309;border-radius:4px;
                    padding:2px 9px;font-size:10px;font-family:monospace;
                    font-weight:700;letter-spacing:1px}
.sev-badge-unconfirmed{background:#e0f2fe;color:#0369a1;border-radius:4px;
                       padding:2px 9px;font-size:10px;font-family:monospace;
                       font-weight:700;letter-spacing:1px}
.score-panel{background:#0b1829;border-radius:10px;padding:22px;
             text-align:center}
.label-mono{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
            color:#94a3b8;font-family:monospace;margin-bottom:4px}
.company-pill{display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;
              border-radius:20px;padding:3px 12px;font-size:12px;
              color:#334155;margin:3px 2px}
.mn-service-box{background:#f8faff;border:1px solid #e2e8f0;
                border-radius:6px;padding:12px 14px}
.internal-banner{background:#fef3c7;border:1px solid #fcd34d;
                 border-radius:6px;padding:8px 14px;font-size:12px;
                 color:#78350f;margin-bottom:16px;font-weight:500}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "saved_reports":[], "portfolio_results":[], "current_report":None,
    "ws_status":"unconfirmed","ws_scheme":"","ws_level":"",
    "ws_verified_by":"","ws_verified_at":"","selected_ids":set(),
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

ANGLES = {
    "Building Owner":      "owner",
    "Managing Agent":      "agent",
    "Building Management": "management",
}
ANGLE_INTROS = {
    "owner":      "Owner angle — frame around **asset value**, EPC compliance risk, and the 4.9% valuation uplift for WiredScore-certified buildings.",
    "agent":      "Agent angle — frame around **occupier satisfaction**, tenant churn reduction, and day-one connectivity for new tenants.",
    "management": "Management angle — frame around **operational resilience**, ISO 27001 compliance, and insurance requirements.",
}
ANGLE_SUMMARY = {
    "owner": [
        ("4.9%", "Valuation uplift for 1Gbps certified buildings"),
        ("8.4%", "Higher lease renewal rates"),
        ("19.4%","Lower tenant churn with managed digital infrastructure"),
        ("2027", "EPC minimum C — compliance deadline approaching"),
    ],
    "agent": [
        ("19.4%","Lower tenant churn with managed infrastructure"),
        ("#1",   "Connectivity is the top occupier complaint category"),
        ("Day 1","MN provides connectivity from first day of tenancy"),
        ("2,000+","UK properties already supported by Modern Networks"),
    ],
    "management": [
        ("ISO 27001","MN certified — demonstrable to insurers"),
        ("24/7",     "Proactive network monitoring and incident response"),
        ("Single",   "One managed services partner — network, security, cloud"),
        ("2,000+",   "UK properties already supported by Modern Networks"),
    ],
}


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="background:#f59e0b;color:#78350f;border-radius:4px;'
        'padding:4px 10px;font-size:10px;font-family:monospace;letter-spacing:2px;'
        'text-transform:uppercase;margin-bottom:12px;font-weight:700">'
        'INTERNAL USE ONLY</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        '<div style="font-size:18px;font-weight:800;color:#fff;margin-bottom:2px">'
        'Modern Networks</div>'
        '<div style="font-size:12px;color:#64748b">Building Intelligence Platform</div>',
        unsafe_allow_html=True
    )
    st.divider()

    st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:600;margin-bottom:6px">YOUR DETAILS</div>', unsafe_allow_html=True)
    staff_name     = st.text_input("Your name",      placeholder="e.g. Sarah Jones",  label_visibility="collapsed")
    staff_initials = st.text_input("Initials",        placeholder="Initials e.g. SJ",  label_visibility="collapsed", max_chars=3)

    st.divider()
    st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:600;margin-bottom:6px">PROPERTY LOOKUP</div>', unsafe_allow_html=True)
    postcode_input = st.text_input("UK Postcode", placeholder="e.g. EC3V 1AB", label_visibility="collapsed").strip().upper()
    angle_label    = st.selectbox("Sales angle", list(ANGLES.keys()), label_visibility="collapsed")
    angle_key      = ANGLES[angle_label]

    st.divider()
    st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:600;margin-bottom:6px">PROSPECT DETAILS</div>', unsafe_allow_html=True)
    p_company = st.text_input("Company name",   placeholder="Company / Organisation", label_visibility="collapsed")
    p_contact = st.text_input("Contact name",   placeholder="Contact name",           label_visibility="collapsed")
    p_title   = st.text_input("Job title",      placeholder="Job title",              label_visibility="collapsed")
    p_email   = st.text_input("Email",          placeholder="Email address",          label_visibility="collapsed")
    p_phone   = st.text_input("Phone",          placeholder="Phone number",           label_visibility="collapsed")
    p_stage   = st.selectbox("Sales stage", [
        "","Prospecting","Qualified","Meeting Booked",
        "Proposal Sent","Negotiation","Closed Won","Closed Lost"
    ], label_visibility="collapsed")
    p_meeting = st.date_input("Meeting date", value=None, label_visibility="collapsed")
    p_notes   = st.text_area("Internal notes", height=80,
                              placeholder="Prior contact, known requirements, context…",
                              label_visibility="collapsed")
    st.divider()
    run = st.button("Run Intelligence Report", type="primary", use_container_width=True)


# ── TABS ──────────────────────────────────────────────────────────────────────
saved_count = len(st.session_state.saved_reports)
tab1, tab2, tab3 = st.tabs([
    "📊 Assessment",
    "🏢 Portfolio",
    f"📁 Saved Briefings ({saved_count})" if saved_count else "📁 Saved Briefings",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    if run:
        if not postcode_input:
            st.error("Please enter a postcode.")
            st.stop()

        with st.status("Pulling intelligence…", expanded=True) as status:
            st.write("🗺 OS Names API — locating postcode…")
            coords = get_coordinates(postcode_input)
            lat = coords.get("lat")
            lon = coords.get("lon")
            if coords.get("error"):
                st.warning(f"Location: {coords['error']}")

            st.write("📡 Ofcom — connectivity data…")
            ofcom = get_connectivity_data(postcode_input)

            st.write("🏢 EPC Register — energy performance…")
            epc = get_epc_data(postcode_input)

            st.write("🏛 Companies House — occupier profile…")
            ch = get_occupier_data(postcode_input)

            if lat and lon:
                st.write("🌊 Environment Agency — flood risk…")
                flood = get_flood_risk(lat, lon)
                st.write("🔒 Police API — crime profile…")
                crime = get_crime_data(lat, lon)
                st.write("🔑 UPRN lookup…")
                uprn_r = get_uprn(lat, lon)
            else:
                flood = {"zone":"Unknown","zone_num":1,"flood_score":50,
                         "risk_label":"Coordinates unavailable","summary":"No coordinates","error":"No coords"}
                crime = {"crime_score":60,"risk_label":"Unavailable","summary":"No coordinates",
                         "total_crimes":0,"top_categories":[],"period":"","error":"No coords"}
                uprn_r = {"uprn":"N/A","error":"No coords"}

            st.write("⚡ Calculating building score…")

            st.session_state.ws_status     = "unconfirmed"
            st.session_state.ws_scheme     = ""
            st.session_state.ws_level      = ""
            st.session_state.ws_verified_by = ""
            st.session_state.ws_verified_at = ""

            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            gaps      = generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed")
            positives = generate_positives(ofcom, epc, ch, flood, crime)

            # Build metrics
            def _met(value, detail, status):
                return {"value":value,"detail":detail,"status":status}

            gig_pct  = ofcom.get("gigabit_pct",0)
            sfbb_pct = ofcom.get("sfbb_pct",0)
            ufbb_pct = ofcom.get("ufbb_pct",0)

            metrics = {
                "connectivity": _met(
                    ofcom.get("tier","Unknown"),
                    (f"Gigabit coverage: {gig_pct:.0f}%\n"
                     f"Ultrafast: {ufbb_pct:.0f}%  ·  Superfast: {sfbb_pct:.0f}%\n"
                     f"{'✓ Full fibre confirmed' if ofcom.get('gigabit') or ofcom.get('fttp') else '✗ Full fibre not confirmed'}\n"
                     f"Data: {ofcom.get('matched','postcode')} level match"),
                    "good" if ofcom.get("gigabit") or ofcom.get("fttp") else
                    "warn" if ofcom.get("ufbb") or ofcom.get("sfbb") else "bad"
                ),
                "epc": _met(
                    f"EPC {epc.get('rating','?')}" if epc.get("rating","Unknown") != "Unknown" else "No Data",
                    (f"Score: {epc.get('score',0)}  ·  Potential: {epc.get('potential_rating','?')}\n"
                     f"{'⚠ Below proposed 2027 minimum (C)' if epc.get('below_2027') else '✓ Meets proposed 2027 threshold'}\n"
                     f"{'Expires: ' + epc.get('expiry_date','') if epc.get('expiry_date') else ''}\n"
                     f"{'⚠ Certificate expires within 12 months' if epc.get('expires_soon') else ''}"),
                    "good" if epc.get("rating","") in ("A","B","C") and not epc.get("expires_soon")
                    else "warn" if epc.get("rating","") == "D" else "bad"
                ),
                "occupiers": _met(
                    f"{ch.get('active',0)} Companies" if ch.get("active",0) > 0 else "None Found",
                    (f"{ch.get('profile_label','Unknown')}\n"
                     f"{ch.get('churn_estimate','')}\n"
                     f"{'Companies: '+', '.join(ch.get('companies',[])[:3]) if ch.get('companies') else 'No companies matched'}"),
                    "good" if ch.get("active",0) > 10 else
                    "warn" if ch.get("active",0) > 0 else "bad"
                ),
                "flood": _met(
                    flood.get("zone","Unknown"),
                    flood.get("risk_label","") or flood.get("summary",""),
                    "good" if flood.get("zone_num",1)==1 else
                    "warn" if flood.get("zone_num",1)==2 else "bad"
                ),
                "crime": _met(
                    crime.get("risk_label","Unknown"),
                    (f"{crime.get('total_crimes',0)} crimes recorded · {crime.get('period','')}\n"
                     f"Top: {', '.join(c[0] for c in crime.get('top_categories',[])[:2]) or 'No data available'}"),
                    "good" if crime.get("crime_score",60)>=70 else
                    "warn" if crime.get("crime_score",60)>=50 else "bad"
                ),
            }

            prospect = {
                "company":  p_company,
                "contact":  p_contact,
                "title":    p_title,
                "email":    p_email,
                "phone":    p_phone,
                "stage":    p_stage,
                "meeting":  str(p_meeting) if p_meeting else "",
                "notes":    p_notes,
                "staff":    staff_name or "MN Staff",
                "initials": (staff_initials or "MN").upper(),
            }

            report = {
                "id":          f"{postcode_input}_{int(time.time())}",
                "postcode":    postcode_input,
                "uprn":        uprn_r.get("uprn","N/A"),
                "lat":lat,     "lon":lon,
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
                "companies":   ch.get("companies",[]),
            }
            st.session_state.current_report = report
            status.update(label="Report ready.", state="complete", expanded=False)

    # ── Display ────────────────────────────────────────────────────────────
    r = st.session_state.current_report

    if r is None:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;color:#94a3b8">
            <div style="font-size:56px;margin-bottom:20px">🏢</div>
            <h2 style="color:#0b1829;font-size:22px;margin-bottom:10px">Modern Networks Building Intelligence</h2>
            <p style="font-size:14px;max-width:460px;margin:0 auto 20px;line-height:1.8;color:#64748b">
            Enter a postcode and prospect details in the sidebar, then click
            <strong style="color:#0b1829">Run Intelligence Report</strong> to generate
            a sales briefing for that building.
            </p>
            <div style="font-size:12px;color:#94a3b8;line-height:2">
            Data sources: Ofcom · EPC Register · Companies House · Environment Agency · OS Names · Police API
            </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    P   = r["prospect"]
    raw = r["raw"]

    # ── Internal banner ────────────────────────────────────────────────────
    st.markdown(
        '<div class="internal-banner">🔒 INTERNAL USE ONLY — Modern Networks Sales Intelligence Platform — Not for external distribution</div>',
        unsafe_allow_html=True
    )

    # ── Header row ─────────────────────────────────────────────────────────
    col_title, col_score = st.columns([3, 1])
    with col_title:
        title = f"{P.get('company','')} — {r['postcode']}" if P.get("company") else f"Building Assessment — {r['postcode']}"
        st.markdown(f"## {title}")
        st.markdown(
            f'<div style="font-size:11px;color:#94a3b8;font-family:monospace;margin-bottom:8px">'
            f'UPRN {r["uprn"]}  ·  Generated {r["savedAt"]}  ·  {P.get("staff","MN Staff")}'
            f'{"  ·  " + P.get("stage","") if P.get("stage") else ""}'
            f'</div>',
            unsafe_allow_html=True
        )
        crit  = sum(1 for g in r["gaps"] if g["sev"]=="critical")
        adv   = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
        uncon = sum(1 for g in r["gaps"] if g["sev"]=="unconfirmed")
        st.markdown(
            f'<span style="background:#fee2e2;color:#dc2626;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700">{crit} Critical</span> '
            f'<span style="background:#fef3c7;color:#b45309;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700;margin-left:4px">{adv} Advisory</span> '
            f'{"<span style=\"background:#e0f2fe;color:#0369a1;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700;margin-left:4px\">"+str(uncon)+" Unconfirmed</span>" if uncon else ""} '
            f'<span style="color:#94a3b8;font-size:12px;margin-left:8px">{len(r["positives"])} strengths confirmed</span>',
            unsafe_allow_html=True
        )

    with col_score:
        sc = r["scoreColour"]
        st.markdown(
            f'<div class="score-panel">'
            f'<div style="font-size:10px;letter-spacing:2px;color:#475569;margin-bottom:6px">DIGITAL INFRASTRUCTURE SCORE</div>'
            f'<div style="font-size:56px;font-weight:800;color:{sc};line-height:1">{r["score"]}</div>'
            f'<div style="font-size:10px;color:#475569;margin-top:2px">/100</div>'
            f'<div style="font-size:11px;color:{sc};margin-top:8px;font-weight:600;line-height:1.4">{r["scoreLabel"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Action buttons ─────────────────────────────────────────────────────
    st.markdown("")
    ba1, ba2, ba3, ba4 = st.columns([1,1,1,2])
    with ba1:
        r["wiredScore"] = {
            "status":     st.session_state.ws_status,
            "scheme":     st.session_state.ws_scheme,
            "level":      st.session_state.ws_level,
            "verifiedBy": st.session_state.ws_verified_by,
            "verifiedAt": st.session_state.ws_verified_at,
        }
        r["gaps"] = generate_gaps(
            raw["ofcom"], raw["epc"], raw["ch"],
            raw["flood"], raw["crime"],
            st.session_state.ws_status
        )
        pdf_bytes = generate_briefing_pdf(r, r.get("angle","owner"))
        st.download_button(
            "⬇ Download PDF Briefing",
            data=pdf_bytes,
            file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}-{r['savedAt'].replace(' ','-')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with ba2:
        already = any(s["id"]==r["id"] for s in st.session_state.saved_reports)
        if already:
            st.button("✓ Briefing Saved", disabled=True, use_container_width=True)
        else:
            if st.button("🔖 Save Briefing", use_container_width=True):
                st.session_state.saved_reports.append(dict(r))
                st.success("Saved.")
                st.rerun()
    with ba3:
        ofcom_url = f"https://checker.ofcom.org.uk/en-gb/broadband-coverage?postcode={r['postcode'].replace(' ','%20')}"
        st.link_button("📡 Ofcom Coverage Checker ↗", ofcom_url, use_container_width=True)

    st.divider()

    # ── Angle intro + key stats ────────────────────────────────────────────
    st.markdown(f"*{ANGLE_INTROS[r.get('angle','owner')]}*")
    st.markdown("")

    stat_cols = st.columns(4)
    for i, (num, label) in enumerate(ANGLE_SUMMARY[r.get("angle","owner")]):
        with stat_cols[i]:
            st.markdown(
                f'<div class="mn-card" style="text-align:center;padding:14px">'
                f'<div style="font-size:22px;font-weight:800;color:#0b1829">{num}</div>'
                f'<div style="font-size:11px;color:#64748b;margin-top:4px;line-height:1.4">{label}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.divider()

    # ── WiredScore panel ───────────────────────────────────────────────────
    ws_status = st.session_state.ws_status
    ws_col_map = {"certified":"🟢","not-certified":"🔴","unconfirmed":"🟡"}
    st.markdown(f"#### {ws_col_map.get(ws_status,'🟡')} WiredScore / SmartScore Certification Status")
    st.markdown(
        "WiredScore and SmartScore data is not available via any public API. "
        "Verify manually using the certified buildings map, then record the result here. "
        "This updates the gap analysis, score, and PDF briefing."
    )

    wc1, wc2, wc3 = st.columns([2,1,1])
    with wc1:
        new_status = st.radio(
            "Certification status",
            ["unconfirmed","certified","not-certified"],
            index=["unconfirmed","certified","not-certified"].index(ws_status),
            horizontal=True,
            format_func=lambda x:{"unconfirmed":"? Not yet checked","certified":"✓ Certified","not-certified":"✕ Not certified"}[x],
            label_visibility="collapsed"
        )
        if new_status != ws_status:
            st.session_state.ws_status      = new_status
            st.session_state.ws_verified_by = (staff_initials or staff_name or "MN").strip().upper() or "MN"
            st.session_state.ws_verified_at = datetime.now().strftime("%d %b %Y")
            st.rerun()

    if st.session_state.ws_status == "certified":
        with wc2:
            scheme = st.selectbox("Scheme",["","WiredScore","SmartScore","Both"],label_visibility="collapsed")
            if scheme != st.session_state.ws_scheme:
                st.session_state.ws_scheme = scheme
        with wc3:
            level = st.selectbox("Level",["","Certified","Silver","Gold","Platinum"],label_visibility="collapsed")
            if level != st.session_state.ws_level:
                st.session_state.ws_level = level

    c1, c2 = st.columns([1,2])
    with c1:
        st.link_button("🔗 Open WiredScore certified buildings map ↗",
                       "https://wiredscore.com/certified-buildings/",
                       use_container_width=True)
    if st.session_state.ws_verified_at:
        with c2:
            st.caption(f"Recorded {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}")

    st.divider()

    # ── Data Overview ──────────────────────────────────────────────────────
    st.markdown("#### Building Data Overview")
    metric_labels = {
        "connectivity":"Connectivity","epc":"Energy / EPC",
        "occupiers":"Occupier Profile","flood":"Flood Risk","crime":"Crime Profile"
    }
    status_colours = {"good":"#059669","warn":"#d97706","bad":"#dc2626"}
    metrics = r["metrics"]

    # Show 5 metrics in a row (removed mobile as we don't have good data)
    display_metrics = {k:v for k,v in metrics.items() if k != "mobile"}
    mcols = st.columns(len(display_metrics))
    for i, (k, v) in enumerate(display_metrics.items()):
        sc_m = status_colours.get(v["status"],"#64748b")
        detail_html = v["detail"].replace("\n","<br>")
        with mcols[i]:
            st.markdown(
                f'<div class="mn-card mn-card-{"good" if v["status"]=="good" else "warn" if v["status"]=="warn" else "bad"}">'
                f'<div class="label-mono">{metric_labels.get(k,k)}</div>'
                f'<div style="font-size:17px;font-weight:700;color:{sc_m};margin:5px 0;line-height:1.3">{v["value"]}</div>'
                f'<div style="font-size:11.5px;color:#475569;line-height:1.7">{detail_html}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # Mobile coverage note
    st.markdown(
        f'<div style="background:#f8faff;border:1px solid #e2e8f0;border-radius:6px;'
        f'padding:12px 16px;font-size:12.5px;color:#475569;margin-bottom:12px">'
        f'📱 <strong>Indoor mobile coverage</strong> — per-postcode data not available in current Ofcom dataset. '
        f'<a href="https://checker.ofcom.org.uk/en-gb/mobile-coverage?postcode={r["postcode"].replace(" ","%20")}" '
        f'target="_blank" style="color:#0099b8">Check indoor mobile coverage for {r["postcode"]} on Ofcom ↗</a>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Companies at this postcode ─────────────────────────────────────────
    companies = r.get("companies",[])
    if companies:
        st.markdown("#### Registered Organisations at This Postcode")
        ch_data = raw["ch"]
        st.markdown(
            f'<div style="font-size:12.5px;color:#64748b;margin-bottom:10px">'
            f'{ch_data.get("active",0)} active companies registered · '
            f'{ch_data.get("churn_estimate","")} · '
            f'{ch_data.get("profile_label","")}'
            f'</div>',
            unsafe_allow_html=True
        )
        pills = "".join(f'<span class="company-pill">{c}</span>' for c in companies)
        more  = ch_data.get("total",0) - len(companies)
        if more > 0:
            pills += f'<span class="company-pill" style="background:#e2e8f0;color:#64748b">+{more} more</span>'
        st.markdown(
            f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:14px 16px;line-height:2.2">{pills}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ── Gaps & Opportunities ───────────────────────────────────────────────
    live_gaps = generate_gaps(
        raw["ofcom"], raw["epc"], raw["ch"],
        raw["flood"], raw["crime"],
        st.session_state.ws_status
    )

    crit  = sum(1 for g in live_gaps if g["sev"]=="critical")
    adv   = sum(1 for g in live_gaps if g["sev"]=="advisory")
    uncon = sum(1 for g in live_gaps if g["sev"]=="unconfirmed")

    st.markdown("#### Gaps & Service Opportunities")
    st.markdown(
        f'<div style="font-size:13px;color:#64748b;margin-bottom:16px">'
        f'Every gap identified maps to a Modern Networks service. '
        f'<span style="color:#dc2626;font-weight:600">{crit} critical</span> · '
        f'<span style="color:#d97706;font-weight:600">{adv} advisory</span>'
        f'{" · <span style=\"color:#0369a1;font-weight:600\">"+str(uncon)+" unconfirmed</span>" if uncon else ""}'
        f'</div>',
        unsafe_allow_html=True
    )

    for g in live_gaps:
        css   = f"gap-{g['sev']}"
        badge = f'<span class="sev-badge-{g["sev"]}">{g["sev"].upper()}</span>'
        impact_tags = "".join(
            f'<span class="impact-tag">{t.strip()}</span>'
            for t in g.get("impact","").split("·")
        )
        stat_html = (
            f'<div class="stat-callout">📊 {g["stat"]}</div>'
            if g.get("stat") else ""
        )

        gc1, gc2 = st.columns([3,1])
        with gc1:
            st.markdown(
                f'<div class="{css}">'
                f'<div style="margin-bottom:6px">{badge} {impact_tags}</div>'
                f'<div style="font-size:15px;font-weight:700;color:#0f172a;margin-bottom:8px">'
                f'{g["icon"]} {g["title"]}</div>'
                f'<div style="font-size:13px;color:#374151;line-height:1.8;margin-bottom:8px">'
                f'{g["desc"]}</div>'
                f'{stat_html}'
                f'<div style="font-size:10.5px;color:#94a3b8;font-family:monospace;margin-top:8px">'
                f'Source: {g["source"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        with gc2:
            st.markdown(
                f'<div class="mn-service-box" style="height:100%">'
                f'<div class="label-mono" style="color:#0099b8">Modern Networks Service</div>'
                f'<div style="font-size:13px;font-weight:700;color:#0b1829;margin:6px 0;line-height:1.6">'
                f'{g["service"].replace(chr(10),"<br>")}</div>'
                f'<div style="font-size:11.5px;color:#64748b;line-height:1.5;margin-bottom:8px">'
                f'{g["detail"]}</div>'
                f'<a href="{g["url"]}" target="_blank" style="font-size:11.5px;color:#0099b8;text-decoration:none">'
                f'modern-networks.co.uk ↗</a>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.divider()

    # ── Confirmed Strengths ────────────────────────────────────────────────
    live_pos = list(generate_positives(
        raw["ofcom"], raw["epc"], raw["ch"],
        raw["flood"], raw["crime"]
    ))
    if st.session_state.ws_status == "certified":
        scheme_str = st.session_state.ws_scheme or "WiredScore"
        level_str  = st.session_state.ws_level  or "Certified"
        live_pos.insert(0,{
            "icon":  "🏆",
            "title": f"{scheme_str} {level_str} Certified",
            "desc":  (
                f"Verified {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}. "
                "This is a differentiating credential — certified buildings achieve 4.9% higher "
                "valuations and 19.4% lower tenant churn. Lead with this in owner and agent conversations."
            ),
        })

    if live_pos:
        st.markdown("#### Confirmed Strengths")
        pcols = st.columns(2)
        for i, p in enumerate(live_pos):
            with pcols[i%2]:
                st.markdown(
                    f'<div class="pos-card">'
                    f'<div style="font-size:18px;margin-bottom:4px">{p["icon"]}</div>'
                    f'<div style="font-size:13.5px;font-weight:700;color:#0f172a;margin-bottom:4px">{p["title"]}</div>'
                    f'<div style="font-size:12.5px;color:#374151;line-height:1.7">{p["desc"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ── Internal notes ─────────────────────────────────────────────────────
    if P.get("notes"):
        st.divider()
        st.markdown("#### Internal Notes")
        st.markdown(
            f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #d97706;'
            f'border-radius:6px;padding:14px 18px;font-size:13px;color:#374151;line-height:1.7">'
            f'{P["notes"]}</div>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Portfolio Assessment")
    st.markdown(
        "Assess multiple properties simultaneously. "
        "Results are ranked by score to prioritise your territory or campaign."
    )

    col_in, col_opt = st.columns([2,1])
    with col_in:
        pf_postcodes = st.text_area(
            "Postcodes — one per line, max 20",
            height=160,
            placeholder="EC3V 1AB\nSW1A 1AA\nCB4 0WS\nW1G 9RT",
        )
    with col_opt:
        pf_client   = st.text_input("Client / Campaign name", placeholder="e.g. JLL Q2 2026")
        pf_audience = st.selectbox("Sales angle", list(ANGLES.keys()), key="pf_angle_sel")
        pf_run      = st.button("Run Portfolio Assessment →", type="primary", use_container_width=True)

    if pf_run and pf_postcodes.strip():
        pcs = list(dict.fromkeys([
            p.strip().upper() for p in pf_postcodes.strip().split("\n") if p.strip()
        ]))[:20]

        results = []
        prog = st.progress(0, text="Starting…")

        for i, pc in enumerate(pcs):
            prog.progress(i/len(pcs), text=f"Assessing {pc}…")
            coords = get_coordinates(pc)
            lat, lon = coords.get("lat"), coords.get("lon")
            ofcom  = get_connectivity_data(pc)
            epc    = get_epc_data(pc)
            ch     = get_occupier_data(pc)
            flood  = get_flood_risk(lat, lon) if lat else {"zone":"Unknown","zone_num":1,"flood_score":50,"risk_label":"Unavailable","summary":"N/A","error":"No coords"}
            crime  = get_crime_data(lat, lon)  if lat else {"crime_score":60,"risk_label":"Unavailable","summary":"N/A","total_crimes":0,"top_categories":[],"period":"","error":"No coords"}
            uprn   = get_uprn(lat, lon)        if lat else {"uprn":"N/A"}
            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            results.append({
                "id":          f"{pc}_{int(time.time())}_{i}",
                "postcode":    pc,
                "uprn":        uprn.get("uprn","N/A"),
                "lat":lat,     "lon":lon,
                "score":       score,
                "scoreLabel":  score_label,
                "scoreColour": score_colour,
                "savedAt":     datetime.now().strftime("%d %b %Y"),
                "angle":       ANGLES[pf_audience],
                "prospect":    {"company":"","contact":"","staff":staff_name or "MN Staff",
                                "initials":(staff_initials or "MN").upper(),
                                "notes":"","stage":"","title":"","email":"","phone":"","meeting":""},
                "gaps":        generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed"),
                "positives":   generate_positives(ofcom, epc, ch, flood, crime),
                "metrics":     {},
                "raw":         {"ofcom":ofcom,"epc":epc,"ch":ch,"flood":flood,"crime":crime},
                "wiredScore":  {"status":"unconfirmed","scheme":"","level":"","verifiedBy":"","verifiedAt":""},
                "companies":   ch.get("companies",[]),
            })

        prog.progress(1.0, text="Complete.")
        st.session_state.portfolio_results = results

    pf_results = st.session_state.portfolio_results
    if pf_results:
        sorted_r = sorted(pf_results, key=lambda r: r["score"])
        avg       = round(sum(r["score"] for r in sorted_r)/len(sorted_r))
        tot_gaps  = sum(len(r["gaps"]) for r in sorted_r)
        urgent    = sum(1 for r in sorted_r if r["score"]<60)

        st.divider()
        mc1,mc2,mc3,mc4 = st.columns(4)
        mc1.metric("Properties Assessed", len(sorted_r))
        mc2.metric("Average Score",       f"{avg}/100")
        mc3.metric("Total Gaps Found",    tot_gaps)
        mc4.metric("Urgent (<60)",        urgent)

        ba1, ba2, _ = st.columns([1,1,3])
        with ba1:
            if st.button("🔖 Save All to Briefings", use_container_width=True):
                added = 0
                for r in sorted_r:
                    if not any(s["id"]==r["id"] for s in st.session_state.saved_reports):
                        st.session_state.saved_reports.append(dict(r))
                        added += 1
                st.success(f"{added} briefings saved.")
                st.rerun()
        with ba2:
            pdf_bytes = generate_portfolio_pdf(sorted_r, pf_client or "Portfolio", staff_name or "MN Staff")
            st.download_button("⬇ Portfolio PDF",data=pdf_bytes,
                               file_name=f"MN-Portfolio-{(pf_client or 'Report').replace(' ','-')}.pdf",
                               mime="application/pdf",use_container_width=True)

        st.markdown("#### Results — Ranked Worst to Best")
        for i, r in enumerate(sorted_r, 1):
            sc_c = r["scoreColour"]
            crit = sum(1 for g in r["gaps"] if g["sev"]=="critical")
            adv  = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
            tg   = r["gaps"][0] if r["gaps"] else {}
            with st.expander(
                f"#{i}  {r['postcode']}  —  {r['score']}/100  —  {r['scoreLabel']}  —  {crit} critical · {adv} advisory"
            ):
                ec1, ec2 = st.columns([3,1])
                with ec1:
                    if tg:
                        st.markdown(f"**Top priority:** {tg['icon']} {tg['title']}")
                        st.markdown(f"*{tg['desc'][:200]}…*")
                    for g in r["gaps"][1:4]:
                        badge_col = "#dc2626" if g["sev"]=="critical" else "#d97706"
                        st.markdown(
                            f'<span style="color:{badge_col};font-size:12px">● </span>'
                            f'{g["icon"]} **{g["title"]}** → *{g["service"].split(chr(10))[0]}*',
                            unsafe_allow_html=True
                        )
                    if r.get("companies"):
                        st.caption("Registered companies: " + ", ".join(r["companies"][:5]))
                with ec2:
                    already = any(s["id"]==r["id"] for s in st.session_state.saved_reports)
                    if not already:
                        if st.button(f"Save", key=f"save_pf_{r['id']}", use_container_width=True):
                            st.session_state.saved_reports.append(dict(r))
                            st.rerun()
                    else:
                        st.caption("✓ Saved")
                    ipdf = generate_briefing_pdf(r, r.get("angle","owner"))
                    st.download_button(
                        "⬇ PDF", data=ipdf,
                        file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                        mime="application/pdf",
                        key=f"pdf_pf_{r['id']}",
                        use_container_width=True
                    )
    elif not pf_run:
        st.info("Enter postcodes above and click Run Portfolio Assessment to begin.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SAVED BRIEFINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    saved = st.session_state.saved_reports

    sh1, sh2 = st.columns([2,2])
    with sh1:
        st.markdown("### Saved Briefings")
        st.caption("Select two or more reports to generate an amalgamated multi-site PDF.")
    with sh2:
        if saved:
            sa1,sa2,sa3 = st.columns(3)
            with sa1:
                if st.button("Select All", use_container_width=True):
                    st.session_state.selected_ids = {r["id"] for r in saved}
                    st.rerun()
            with sa2:
                if st.button("Clear All", use_container_width=True):
                    if st.session_state.get("confirm_clear"):
                        st.session_state.saved_reports = []
                        st.session_state.selected_ids  = set()
                        st.session_state.pop("confirm_clear",None)
                        st.rerun()
                    else:
                        st.session_state["confirm_clear"] = True
                        st.rerun()
            with sa3:
                sel = st.session_state.get("selected_ids",set())
                if len(sel) >= 2:
                    sel_reports = [r for r in saved if r["id"] in sel]
                    amalg = generate_amalgamated_pdf(sel_reports, staff_name or "MN Staff")
                    st.download_button(
                        f"⬇ Amalgamated PDF ({len(sel_reports)})",
                        data=amalg,
                        file_name=f"MN-Amalgamated-{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

    if st.session_state.get("confirm_clear"):
        st.warning("Click Clear All again to confirm removing all saved briefings.")

    if not saved:
        st.info("No briefings saved yet. Run an assessment and click Save Briefing.")
        st.stop()

    n_sel = len(st.session_state.get("selected_ids",set()))
    if n_sel > 0:
        st.markdown(
            f'<div style="background:#e0f2fe;border:1px solid #7dd3fc;border-radius:6px;'
            f'padding:10px 16px;font-size:13px;color:#0369a1;margin-bottom:16px">'
            f'✓ <strong>{n_sel} briefing{"s" if n_sel!=1 else ""} selected</strong> — '
            f'click "Amalgamated PDF" above to generate a combined report</div>',
            unsafe_allow_html=True
        )

    cols = st.columns(3)
    for i, r in enumerate(saved):
        sel     = r["id"] in st.session_state.get("selected_ids",set())
        crit    = sum(1 for g in r["gaps"] if g["sev"]=="critical")
        adv     = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
        ws_s    = r.get("wiredScore",{}).get("status","unconfirmed")
        ws_icon = {"certified":"🟢","not-certified":"🔴","unconfirmed":"🟡"}.get(ws_s,"🟡")
        border  = "2px solid #0099b8" if sel else "1px solid #e2e8f0"
        sc_col  = r["scoreColour"]

        with cols[i%3]:
            st.markdown(
                f'<div style="background:#fff;border:{border};border-radius:8px;padding:16px;margin-bottom:12px">'
                f'<div style="font-size:10px;color:#94a3b8;font-family:monospace;letter-spacing:1.5px;'
                f'text-transform:uppercase;margin-bottom:4px">'
                f'{r["postcode"]}{" · "+r["prospect"].get("company","") if r["prospect"].get("company") else ""}'
                f'</div>'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">'
                f'<div style="font-size:14px;font-weight:700;color:#0f172a;max-width:140px;line-height:1.3">'
                f'{r["prospect"].get("company") or "Assessment — "+r["postcode"]}</div>'
                f'<div style="font-size:30px;font-weight:800;color:{sc_col};line-height:1">{r["score"]}</div>'
                f'</div>'
                f'<div style="font-size:11.5px;color:#64748b;margin-bottom:6px;line-height:1.8">'
                f'{r["scoreLabel"]}<br>'
                f'<span style="color:#dc2626;font-weight:600">{crit} critical</span> · '
                f'<span style="color:#d97706;font-weight:600">{adv} advisory</span>'
                f'{" · <strong style=\"color:#0b1829\">"+r["prospect"].get("stage","")+"</strong>" if r["prospect"].get("stage") else ""}'
                f'</div>'
                f'<div style="font-size:11.5px;color:#64748b">{ws_icon} WiredScore: {ws_s}</div>'
                f'<div style="font-size:11px;color:#94a3b8;margin-top:4px">Saved {r["savedAt"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

            bc1,bc2,bc3,bc4 = st.columns(4)
            with bc1:
                label = "☑" if sel else "☐"
                if st.button(label, key=f"sel_{r['id']}", use_container_width=True):
                    if sel: st.session_state.selected_ids.discard(r["id"])
                    else:   st.session_state.selected_ids.add(r["id"])
                    st.rerun()
            with bc2:
                spdf = generate_briefing_pdf(r, r.get("angle","owner"))
                st.download_button("⬇ PDF",data=spdf,
                                   file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                                   mime="application/pdf",key=f"spdf_{r['id']}",
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
                        s for s in st.session_state.saved_reports if s["id"]!=r["id"]
                    ]
                    st.session_state.selected_ids.discard(r["id"])
                    st.rerun()