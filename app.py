"""
app.py — Modern Networks Building Intelligence Platform (Internal)
Sales meeting preparation tool — digital premium vs brown discount framing.
"""

import streamlit as st
import time
from datetime import datetime

from api.os_names         import get_coordinates
from api.ofcom            import get_connectivity_data
from api.uprn             import get_uprn
from api.epc              import get_epc_data
from api.companies_house  import get_occupier_data
from api.flood_risk       import get_flood_risk_by_postcode
from api.police           import get_crime_data
from scoring              import (calculate_score, generate_gaps, generate_positives,
                                   generate_market_position, generate_checklist)
from pdf_export           import generate_briefing_pdf, generate_portfolio_pdf, generate_amalgamated_pdf

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
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder{
    color:#6b7a99!important;opacity:1!important}
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
.verdict-box{border-radius:10px;padding:20px 24px;margin-bottom:20px;
             border:1px solid}
.mn-card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;
         padding:16px 18px;margin-bottom:10px}
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
.checklist-item{background:#fff;border:1px solid #e2e8f0;border-radius:8px;
                padding:0;margin-bottom:10px;overflow:hidden}
.checklist-q{background:#0b1829;padding:12px 18px;font-size:14px;
             font-weight:600;color:#fff}
.checklist-evidence{background:#f8faff;border-bottom:1px solid #e2e8f0;
                    padding:8px 18px;font-size:11.5px;color:#64748b;
                    font-family:monospace}
.checklist-answer{padding:14px 18px;font-size:13px;color:#374151;line-height:1.8}
.checklist-strength{border-left:4px solid #059669}
.checklist-risk{border-left:4px solid #d97706}
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
.score-panel{background:#0b1829;border-radius:10px;padding:22px;text-align:center}
.label-mono{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;
            color:#94a3b8;font-family:monospace;margin-bottom:4px}
.company-pill{display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;
              border-radius:20px;padding:3px 12px;font-size:12px;
              color:#334155;margin:3px 2px}
.mn-service-box{background:#f8faff;border:1px solid #e2e8f0;border-radius:6px;
                padding:12px 14px}
.internal-banner{background:#fef3c7;border:1px solid #fcd34d;border-radius:6px;
                 padding:8px 14px;font-size:12px;color:#78350f;
                 margin-bottom:16px;font-weight:500}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "saved_reports":[], "portfolio_results":[], "current_report":None,
    "ws_status":"unconfirmed","ws_scheme":"","ws_level":"",
    "ws_verified_by":"","ws_verified_at":"","selected_ids":set(),
    "active_tab": 0,
    "mob_ee_indoor":"","mob_ee_outdoor":"",
    "mob_o2_indoor":"","mob_o2_outdoor":"",
    "mob_three_indoor":"","mob_three_outdoor":"",
    "mob_voda_indoor":"","mob_voda_outdoor":"",
    "mob_verified_by":"","mob_verified_at":"",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

ANGLES = {
    "Building Owner":      "owner",
    "Managing Agent":      "agent",
    "Building Management": "management",
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
    staff_name     = st.text_input("Name",     placeholder="Your name",    label_visibility="collapsed")
    staff_initials = st.text_input("Initials", placeholder="Initials",     label_visibility="collapsed", max_chars=3)

    st.divider()
    st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:600;margin-bottom:6px">PROPERTY LOOKUP</div>', unsafe_allow_html=True)
    postcode_input = st.text_input("Postcode", placeholder="UK Postcode e.g. EC3V 1AB", label_visibility="collapsed").strip().upper()
    angle_label    = st.selectbox("Angle", list(ANGLES.keys()), label_visibility="collapsed")
    angle_key      = ANGLES[angle_label]

    st.divider()
    st.markdown('<div style="color:#94a3b8;font-size:11px;font-weight:600;margin-bottom:6px">PROSPECT DETAILS</div>', unsafe_allow_html=True)
    p_company = st.text_input("Company",  placeholder="Company / Organisation", label_visibility="collapsed")
    p_contact = st.text_input("Contact",  placeholder="Contact name",           label_visibility="collapsed")
    p_title   = st.text_input("Title",    placeholder="Job title",              label_visibility="collapsed")
    p_email   = st.text_input("Email",    placeholder="Email address",          label_visibility="collapsed")
    p_phone   = st.text_input("Phone",    placeholder="Phone number",           label_visibility="collapsed")
    p_stage   = st.selectbox("Stage", [
        "","Prospecting","Qualified","Meeting Booked",
        "Proposal Sent","Negotiation","Closed Won","Closed Lost"
    ], label_visibility="collapsed")
    p_meeting = st.date_input("Meeting", value=None, label_visibility="collapsed")
    p_notes   = st.text_area("Notes", height=80,
                              placeholder="Prior contact, known requirements, context…",
                              label_visibility="collapsed")
    st.divider()
    run = st.button("Run Intelligence Report", type="primary", use_container_width=True)


# ── TABS ──────────────────────────────────────────────────────────────────────
saved_count = len(st.session_state.saved_reports)
tab1, tab2, tab3 = st.tabs([
    "📊 Assessment",
    "🏢 Portfolio",
    f"📁 Saved ({saved_count})" if saved_count else "📁 Saved Briefings",
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
            st.write("🗺 OS Names — locating postcode…")
            coords = get_coordinates(postcode_input)
            lat = coords.get("lat")
            lon = coords.get("lon")

            st.write("📡 Ofcom — connectivity data…")
            ofcom = get_connectivity_data(postcode_input)

            st.write("🏢 EPC Register — energy performance…")
            epc = get_epc_data(postcode_input)

            st.write("🏛 Companies House — occupier profile…")
            ch = get_occupier_data(postcode_input)

            st.write("🌊 Flood risk database…")
            flood = get_flood_risk_by_postcode(postcode_input)

            if lat and lon:
                st.write("🔒 Police API — crime profile…")
                crime = get_crime_data(lat, lon)
                st.write("🔑 UPRN lookup…")
                uprn_r = get_uprn(lat, lon)
            else:
                crime = {"crime_score":60,"risk_label":"Unavailable",
                         "summary":"No coordinates","total_crimes":0,
                         "top_categories":[],"period":"","error":"No coords"}
                uprn_r = {"uprn":"N/A"}

            st.write("⚡ Calculating score and market position…")

            st.session_state.ws_status      = "unconfirmed"
            st.session_state.ws_scheme      = ""
            st.session_state.ws_level       = ""
            st.session_state.ws_verified_by = ""
            st.session_state.ws_verified_at = ""
            for _mob_key in [
                "mob_ee_indoor","mob_ee_outdoor",
                "mob_o2_indoor","mob_o2_outdoor",
                "mob_three_indoor","mob_three_outdoor",
                "mob_voda_indoor","mob_voda_outdoor",
                "mob_verified_by","mob_verified_at",
            ]:
                st.session_state[_mob_key] = ""

            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            gaps      = generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed")
            positives = generate_positives(ofcom, epc, ch, flood, crime)
            position  = generate_market_position(ofcom, epc, ch, flood, crime, "unconfirmed", score)
            checklist = generate_checklist(ofcom, epc, ch, flood, crime, "unconfirmed", postcode_input)

            def _met(value, detail, status):
                return {"value":value,"detail":detail,"status":status}

            gig_pct  = ofcom.get("gigabit_pct",0)
            sfbb_pct = ofcom.get("sfbb_pct",0)
            ufbb_pct = ofcom.get("ufbb_pct",0)

            metrics = {
                "connectivity": _met(
                    ofcom.get("tier","Unknown"),
                    (f"Gigabit: {gig_pct:.0f}%  ·  Ultrafast: {ufbb_pct:.0f}%  ·  Superfast: {sfbb_pct:.0f}%\n"
                     f"{'✓ Full fibre confirmed' if ofcom.get('gigabit') or ofcom.get('fttp') else '✗ Full fibre not confirmed'}\n"
                     f"Source: {ofcom.get('matched','postcode')} level Ofcom data"),
                    "good" if ofcom.get("gigabit") or ofcom.get("fttp") else
                    "warn" if ofcom.get("ufbb") or ofcom.get("sfbb") else "bad"
                ),
                "epc": _met(
                    f"EPC {epc.get('rating','?')}" if epc.get("rating","Unknown") != "Unknown" else "No Data",
                    (f"Rating: {epc.get('rating','Unknown')}  ·  Cert number: {epc.get('cert_number','N/A')}\n"
                     f"Lodged: {epc.get('lodged','Unknown')}\n"
                     f"{'⚠ Below proposed 2027 minimum (C)' if epc.get('below_2027') else '✓ Meets proposed 2027 threshold'}"),
                    "good" if epc.get("rating","") in ("A","B","C") and not epc.get("expires_soon")
                    else "warn" if epc.get("rating","") == "D" else "bad"
                ),
                "occupiers": _met(
                    f"{ch.get('active',0)} Companies" if ch.get("active",0) > 0 else "None Found",
                    (f"{ch.get('profile_label','Unknown')}\n"
                     f"{ch.get('churn_estimate','')}\n"
                     f"{'Sample: '+', '.join(ch.get('companies',[])[:2]) if ch.get('companies') else 'No exact matches'}"),
                    "good" if ch.get("active",0) > 10 else
                    "warn" if ch.get("active",0) > 0 else "bad"
                ),
                "flood": _met(
                    flood.get("zone","Unknown"),
                    flood.get("detail","") or flood.get("risk_label",""),
                    "good" if flood.get("zone_num",1)==1 else
                    "warn" if flood.get("zone_num",1)==2 else "bad"
                ),
                "crime": _met(
                    crime.get("risk_label","Unknown"),
                    (f"{crime.get('total_crimes',0)} crimes recorded · {crime.get('period','')}\n"
                     f"Top: {', '.join(c[0] for c in crime.get('top_categories',[])[:2]) or 'No data'}"),
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
                "angle":    angle_label,
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
                "position":    position,
                "checklist":   checklist,
                "raw":         {"ofcom":ofcom,"epc":epc,"ch":ch,"flood":flood,"crime":crime},
                "wiredScore":  {"status":"unconfirmed","scheme":"","level":"","verifiedBy":"","verifiedAt":""},
                "mobile":      {"EE":{},"O2":{},"Three":{},"Vodafone":{},"verifiedBy":"","verifiedAt":""},
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
            <p style="font-size:14px;max-width:500px;margin:0 auto 20px;line-height:1.9;color:#64748b">
            Enter a postcode and prospect details in the sidebar, then click
            <strong style="color:#0b1829">Run Intelligence Report</strong>.<br>
            The report will give you a commercial market position verdict,
            building-specific data, and a pre-meeting checklist tailored to
            the nine questions you'll be asked in every sales conversation.
            </p>
            <div style="font-size:12px;color:#94a3b8;line-height:2">
            Ofcom · EPC Register · Companies House · Environment Agency · OS Names · Police API
            </div>
        </div>""", unsafe_allow_html=True)
        st.stop()

    P   = r["prospect"]
    raw = r["raw"]

    # ── Internal banner ────────────────────────────────────────────────────
    st.markdown(
        '<div class="internal-banner">🔒 INTERNAL — Modern Networks Sales Intelligence — Not for external distribution</div>',
        unsafe_allow_html=True
    )

    # ── Header ─────────────────────────────────────────────────────────────
    col_title, col_score = st.columns([3,1])
    with col_title:
        title = f"{P.get('company','')} — {r['postcode']}" if P.get("company") else f"Building Assessment — {r['postcode']}"
        st.markdown(f"## {title}")
        st.markdown(
            f'<div style="font-size:11px;color:#94a3b8;font-family:monospace;margin-bottom:8px">'
            f'UPRN {r["uprn"]}  ·  {r["savedAt"]}  ·  {P.get("staff","MN Staff")}'
            f'{"  ·  " + P.get("stage","") if P.get("stage") else ""}'
            f'{"  ·  " + P.get("angle","") if P.get("angle") else ""}'
            f'</div>',
            unsafe_allow_html=True
        )
        crit  = sum(1 for g in r["gaps"] if g["sev"]=="critical")
        adv   = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
        uncon = sum(1 for g in r["gaps"] if g["sev"]=="unconfirmed")
        st.markdown(
            f'<span style="background:#fee2e2;color:#dc2626;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700">{crit} Critical</span> '
            f'<span style="background:#fef3c7;color:#b45309;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700;margin-left:4px">{adv} Advisory</span> '
            f'{"<span style=\"background:#e0f2fe;color:#0369a1;padding:3px 10px;border-radius:4px;font-size:12px;font-weight:700;margin-left:4px\">"+str(uncon)+" Unconfirmed</span> " if uncon else ""}'
            f'<span style="color:#94a3b8;font-size:12px;margin-left:8px">{len(r["positives"])} strengths confirmed</span>',
            unsafe_allow_html=True
        )

    with col_score:
        sc = r["scoreColour"]
        st.markdown(
            f'<div class="score-panel">'
            f'<div style="font-size:9px;letter-spacing:2px;color:#475569;margin-bottom:4px">DIGITAL INFRASTRUCTURE SCORE</div>'
            f'<div style="font-size:52px;font-weight:800;color:{sc};line-height:1">{r["score"]}</div>'
            f'<div style="font-size:10px;color:#475569;margin-top:2px">/100</div>'
            f'<div style="font-size:11px;color:{sc};margin-top:6px;font-weight:600;line-height:1.4">{r["scoreLabel"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # ── Action buttons ─────────────────────────────────────────────────────
    st.markdown("")
    ba1, ba2, ba3, ba4 = st.columns([1,1,1,1])
    with ba1:
        if st.button("⬇ Download Briefing", use_container_width=True, key="pdf_btn"):
            r["wiredScore"] = {
                "status":     st.session_state.ws_status,
                "scheme":     st.session_state.ws_scheme,
                "level":      st.session_state.ws_level,
                "verifiedBy": st.session_state.ws_verified_by,
                "verifiedAt": st.session_state.ws_verified_at,
            }
            r["gaps"]      = generate_gaps(raw["ofcom"], raw["epc"], raw["ch"],
                                           raw["flood"], raw["crime"], st.session_state.ws_status)
            r["position"]  = generate_market_position(raw["ofcom"], raw["epc"], raw["ch"],
                                                       raw["flood"], raw["crime"],
                                                       st.session_state.ws_status, r["score"])
            r["checklist"] = generate_checklist(raw["ofcom"], raw["epc"], raw["ch"],
                                                raw["flood"], raw["crime"],
                                                st.session_state.ws_status, r["postcode"])
            pdf_bytes = generate_briefing_pdf(r, r.get("angle","owner"))
            st.download_button(
                "⬇ Click to save PDF",
                data=pdf_bytes,
                file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="pdf_download"
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
        with ba3:
            st.link_button(
                "📡 Ofcom Checker ↗",
                f"https://checker.ofcom.org.uk/en-gb/mobile-coverage?postcode={r['postcode'].replace(' ','%20')}",
                use_container_width=True
            )
    with ba4:
        if st.button("🔄 Refresh Data", use_container_width=True):
            get_coordinates.clear()
            get_connectivity_data.clear()
            get_epc_data.clear()
            get_occupier_data.clear()
            get_flood_risk_by_postcode.clear()
            get_crime_data.clear()
            get_uprn.clear()
            st.session_state.current_report = None
            st.rerun()

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # MARKET POSITION VERDICT
    # ══════════════════════════════════════════════════════════════════════
    pos = r.get("position", {})
    if not pos:
        pos = generate_market_position(raw["ofcom"], raw["epc"], raw["ch"],
                                       raw["flood"], raw["crime"],
                                       st.session_state.ws_status, r["score"])

    st.markdown(
        f'<div class="verdict-box" style="background:{pos["bg"]};border-color:{pos["border"]}">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px">'
        f'<div style="flex:1">'
        f'<div style="font-size:11px;letter-spacing:2px;font-family:monospace;color:{pos["colour"]};margin-bottom:6px">MARKET POSITION VERDICT</div>'
        f'<div style="font-size:22px;font-weight:800;color:{pos["colour"]};margin-bottom:8px">'
        f'{pos["icon"]} {pos["verdict"]}</div>'
        f'<div style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:8px">{pos["headline"]}</div>'
        f'<div style="font-size:13px;color:#374151;line-height:1.8;margin-bottom:10px">{pos["detail"]}</div>'
        f'<div style="background:rgba(0,0,0,0.05);border-radius:6px;padding:10px 14px;'
        f'font-size:12.5px;color:#374151;line-height:1.7">'
        f'<strong>MN Opportunity:</strong> {pos["opportunity"]}</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ══════════════════════════════════════════════════════════════════════
    # WIREDSCORE PANEL
    # ══════════════════════════════════════════════════════════════════════
    ws_status = st.session_state.ws_status
    ws_icons  = {"certified":"🟢","not-certified":"🔴","unconfirmed":"🟡"}
    st.markdown(f"#### {ws_icons.get(ws_status,'🟡')} WiredScore / SmartScore")
    st.markdown(
        "No public API exists for WiredScore data. "
        "Check the map manually and record the result here — this updates the verdict, gaps, and PDF."
    )
    wc1, wc2, wc3 = st.columns([2,1,1])
    with wc1:
        new_status = st.radio(
            "Status",
            ["unconfirmed","certified","not-certified"],
            index=["unconfirmed","certified","not-certified"].index(ws_status),
            horizontal=True,
            format_func=lambda x:{"unconfirmed":"? Not yet checked",
                                   "certified":"✓ Certified",
                                   "not-certified":"✕ Not certified"}[x],
            label_visibility="collapsed"
        )
        if new_status != ws_status:
            st.session_state.ws_status      = new_status
            st.session_state.ws_verified_by = (staff_initials or staff_name or "MN").strip().upper() or "MN"
            st.session_state.ws_verified_at = datetime.now().strftime("%d %b %Y")
            st.rerun()
    if st.session_state.ws_status == "certified":
        with wc2:
            scheme_opts = ["","WiredScore","SmartScore","Both"]
            scheme_idx  = scheme_opts.index(st.session_state.ws_scheme) if st.session_state.ws_scheme in scheme_opts else 0
            scheme = st.selectbox("Scheme", scheme_opts, index=scheme_idx,
                                  label_visibility="collapsed")
            st.session_state.ws_scheme = scheme
        with wc3:
            level_opts = ["","Certified","Silver","Gold","Platinum"]
            level_idx  = level_opts.index(st.session_state.ws_level) if st.session_state.ws_level in level_opts else 0
            level = st.selectbox("Level", level_opts, index=level_idx,
                                 label_visibility="collapsed")
            st.session_state.ws_level = level
    lc1, lc2 = st.columns([1,2])
    with lc1:
        st.link_button("🔗 WiredScore certified buildings map ↗",
                       "https://wiredscore.com/map/",
                       use_container_width=True)
    if st.session_state.ws_verified_at:
        with lc2:
            st.caption(f"Recorded {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}")

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # DATA OVERVIEW
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("#### Building Data")
    metric_labels = {
        "connectivity":"Connectivity","epc":"Energy / EPC",
        "occupiers":"Occupier Profile","flood":"Flood Risk","crime":"Crime Profile"
    }
    status_colours = {"good":"#059669","warn":"#d97706","bad":"#dc2626"}
    metrics = r["metrics"]
    display_metrics = {k:v for k,v in metrics.items() if k != "mobile"}
    mcols = st.columns(len(display_metrics))
    for i, (k, v) in enumerate(display_metrics.items()):
        sc_m = status_colours.get(v["status"],"#64748b")
        with mcols[i]:
            st.markdown(
                f'<div class="mn-card mn-card-{"good" if v["status"]=="good" else "warn" if v["status"]=="warn" else "bad"}">'
                f'<div class="label-mono">{metric_labels.get(k,k)}</div>'
                f'<div style="font-size:17px;font-weight:700;color:{sc_m};margin:5px 0;line-height:1.3">{v["value"]}</div>'
                f'<div style="font-size:11px;color:#475569;line-height:1.7">{v["detail"].replace(chr(10),"<br>")}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    # ── Mobile Coverage Panel ──────────────────────────────────────────────
    MOB_OPTS = ["", "Good", "Variable", "None"]
    OPERATORS = [
        ("EE",        "mob_ee_indoor",    "mob_ee_outdoor"),
        ("O2",        "mob_o2_indoor",    "mob_o2_outdoor"),
        ("Three",     "mob_three_indoor", "mob_three_outdoor"),
        ("Vodafone",  "mob_voda_indoor",  "mob_voda_outdoor"),
    ]

    mob_any = any(st.session_state.get(k) for _, k, _ in OPERATORS)
    mob_icon = "📶" if mob_any else "📱"
    st.markdown(f"#### {mob_icon} Mobile Coverage")
    st.markdown(
        "No API is available for per-postcode mobile data. "
        "Check Ofcom manually and record each operator's result here — this saves with the briefing and PDF."
    )
    lm1, lm2 = st.columns([1, 2])
    with lm1:
        st.link_button(
            f"📡 Ofcom Mobile Checker — {r['postcode']} ↗",
            f"https://checker.ofcom.org.uk/en-gb/mobile-coverage?postcode={r['postcode'].replace(' ','%20')}",
            use_container_width=True,
        )

    mob_cols = st.columns(4)
    mob_changed = False
    for col, (label, key_in, key_out) in zip(mob_cols, OPERATORS):
        with col:
            st.markdown(
                f'<div style="font-size:11px;font-weight:700;color:#0b1829;'
                f'letter-spacing:1px;text-transform:uppercase;margin-bottom:4px">{label}</div>',
                unsafe_allow_html=True,
            )
            new_in = st.selectbox(
                f"{label} Indoor",
                MOB_OPTS,
                index=MOB_OPTS.index(st.session_state.get(key_in, "") or ""),
                key=f"sel_{key_in}",
                label_visibility="collapsed",
                format_func=lambda x: "— Indoor —" if x == "" else f"Indoor: {x}",
            )
            new_out = st.selectbox(
                f"{label} Outdoor",
                MOB_OPTS,
                index=MOB_OPTS.index(st.session_state.get(key_out, "") or ""),
                key=f"sel_{key_out}",
                label_visibility="collapsed",
                format_func=lambda x: "— Outdoor —" if x == "" else f"Outdoor: {x}",
            )
            if new_in != st.session_state.get(key_in, ""):
                st.session_state[key_in] = new_in
                mob_changed = True
            if new_out != st.session_state.get(key_out, ""):
                st.session_state[key_out] = new_out
                mob_changed = True

    if mob_changed:
        st.session_state["mob_verified_by"] = (staff_initials or staff_name or "MN").strip().upper() or "MN"
        st.session_state["mob_verified_at"] = datetime.now().strftime("%d %b %Y")
        st.rerun()

    if st.session_state.get("mob_verified_at"):
        st.caption(f"Recorded {st.session_state['mob_verified_at']} by {st.session_state['mob_verified_by']}")

    # Push mobile data into the live report so Save and PDF pick it up
    r["mobile"] = {
        op: {"indoor": st.session_state.get(ki, ""), "outdoor": st.session_state.get(ko, "")}
        for op, ki, ko in OPERATORS
    }
    r["mobile"]["verifiedBy"] = st.session_state.get("mob_verified_by", "")
    r["mobile"]["verifiedAt"] = st.session_state.get("mob_verified_at", "")

    # Companies
    companies = r.get("companies",[])
    if companies:
        st.markdown("**Registered organisations at this postcode:**")
        pills = "".join(f'<span class="company-pill">{c}</span>' for c in companies)
        more  = raw["ch"].get("total",0) - len(companies)
        if more > 0:
            pills += f'<span class="company-pill" style="background:#e2e8f0;color:#64748b">+{more} more</span>'
        st.markdown(
            f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;'
            f'padding:12px 16px;line-height:2.2;margin-bottom:4px">{pills}</div>',
            unsafe_allow_html=True
        )

    # Internal notes
    if P.get("notes"):
        st.markdown(
            f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #d97706;'
            f'border-radius:6px;padding:12px 16px;font-size:13px;color:#374151;line-height:1.7;margin-top:8px">'
            f'<strong>Notes:</strong> {P["notes"]}</div>',
            unsafe_allow_html=True
        )

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # GAPS & OPPORTUNITIES
    # ══════════════════════════════════════════════════════════════════════
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
        f'Every gap maps to a Modern Networks service. '
        f'<span style="color:#dc2626;font-weight:600">{crit} critical</span> · '
        f'<span style="color:#d97706;font-weight:600">{adv} advisory</span>'
        f'{"  ·  <span style=\"color:#0369a1;font-weight:600\">"+str(uncon)+" unconfirmed</span>" if uncon else ""}'
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
                f'<div class="label-mono" style="color:#0099b8">MN Service</div>'
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

    # ══════════════════════════════════════════════════════════════════════
    # CONFIRMED STRENGTHS
    # ══════════════════════════════════════════════════════════════════════
    live_pos = list(generate_positives(
        raw["ofcom"], raw["epc"], raw["ch"], raw["flood"], raw["crime"]
    ))
    if st.session_state.ws_status == "certified":
        scheme_str = st.session_state.ws_scheme or "WiredScore"
        level_str  = st.session_state.ws_level  or "Certified"
        live_pos.insert(0,{
            "icon":  "🏆",
            "title": f"{scheme_str} {level_str} Certified",
            "desc":  (
                f"Verified {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}. "
                "Certified buildings achieve 4.9% higher valuations and 19.4% lower tenant churn. "
                "Lead with this in every owner and agent conversation."
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

    st.divider()

    # ══════════════════════════════════════════════════════════════════════
    # SALES MEETING CHECKLIST
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("#### Pre-Meeting Sales Checklist")
    st.markdown(
        '<div style="font-size:13px;color:#64748b;margin-bottom:16px">'
        'Building-specific answers to the nine questions you\'ll be asked in every commercial property sales meeting. '
        'Answers are tailored to the data for this postcode.'
        '</div>',
        unsafe_allow_html=True
    )

    live_checklist = generate_checklist(
        raw["ofcom"], raw["epc"], raw["ch"],
        raw["flood"], raw["crime"],
        st.session_state.ws_status,
        r["postcode"]
    )

    for i, item in enumerate(live_checklist, 1):
        strength_class = "checklist-strength" if item.get("strength") else "checklist-risk"
        st.markdown(
            f'<div class="checklist-item {strength_class}">'
            f'<div class="checklist-q">Q{i}. {item["q"]}</div>'
            f'<div class="checklist-evidence">📊 Evidence: {item["evidence"]}</div>'
            f'<div class="checklist-answer">{item["answer"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Portfolio Assessment")
    st.markdown("Assess multiple properties simultaneously. Results ranked by score.")

    col_in, col_opt = st.columns([2,1])
    with col_in:
        pf_postcodes = st.text_area(
            "Postcodes",
            height=160,
            placeholder="EC3V 1AB\nSW1A 1AA\nCB4 0WS\nW1G 9RT",
        )
    with col_opt:
        pf_client   = st.text_input("Client / Campaign", placeholder="e.g. JLL Q2 2026")
        pf_audience = st.selectbox("Angle", list(ANGLES.keys()), key="pf_angle_sel")
        pf_run      = st.button("Run Portfolio →", type="primary", use_container_width=True)

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
            flood  = get_flood_risk_by_postcode(pc)
            crime  = get_crime_data(lat, lon) if lat else {
                "crime_score":60,"risk_label":"Unavailable","summary":"N/A",
                "total_crimes":0,"top_categories":[],"period":"","error":"No coords"}
            uprn   = get_uprn(lat, lon) if lat else {"uprn":"N/A"}
            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            gaps = generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed")
            position = generate_market_position(ofcom, epc, ch, flood, crime, "unconfirmed", score)
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
                                "notes":"","stage":"","title":"","email":"","phone":"",
                                "meeting":"","angle":pf_audience},
                "gaps":        gaps,
                "positives":   generate_positives(ofcom, epc, ch, flood, crime),
                "position":    position,
                "checklist":   generate_checklist(ofcom, epc, ch, flood, crime, "unconfirmed", pc),
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
        avg      = round(sum(r["score"] for r in sorted_r)/len(sorted_r))
        tot_gaps = sum(len(r["gaps"]) for r in sorted_r)
        urgent   = sum(1 for r in sorted_r if r["score"]<60)

        st.divider()
        mc1,mc2,mc3,mc4 = st.columns(4)
        mc1.metric("Properties",   len(sorted_r))
        mc2.metric("Avg Score",    f"{avg}/100")
        mc3.metric("Total Gaps",   tot_gaps)
        mc4.metric("Urgent (<60)", urgent)

        ba1, ba2, _ = st.columns([1,1,3])
        with ba1:
            if st.button("🔖 Save All", use_container_width=True):
                added = 0
                for r in sorted_r:
                    if not any(s["id"]==r["id"] for s in st.session_state.saved_reports):
                        st.session_state.saved_reports.append(dict(r))
                        added += 1
                st.success(f"{added} briefings saved.")
                st.rerun()
        with ba2:
            pdf_bytes = generate_portfolio_pdf(sorted_r, pf_client or "Portfolio",
                                               staff_name or "MN Staff")
            st.download_button("⬇ Portfolio PDF", data=pdf_bytes,
                               file_name=f"MN-Portfolio-{(pf_client or 'Report').replace(' ','-')}.pdf",
                               mime="application/pdf", use_container_width=True)

        st.markdown("#### Results — Ranked Worst to Best")
        for i, r in enumerate(sorted_r, 1):
            pos_v = r.get("position",{}).get("verdict","")
            crit  = sum(1 for g in r["gaps"] if g["sev"]=="critical")
            adv   = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
            tg    = r["gaps"][0] if r["gaps"] else {}
            with st.expander(
                f"#{i}  {r['postcode']}  —  {r['score']}/100  —  {pos_v}  —  {crit} critical · {adv} advisory"
            ):
                ec1, ec2 = st.columns([3,1])
                with ec1:
                    if tg:
                        st.markdown(f"**Top priority:** {tg['icon']} {tg['title']}")
                        st.markdown(f"*{tg['desc'][:200]}…*")
                    for g in r["gaps"][1:4]:
                        bc = "#dc2626" if g["sev"]=="critical" else "#d97706"
                        st.markdown(
                            f'<span style="color:{bc}">●</span> {g["icon"]} **{g["title"]}** → *{g["service"].split(chr(10))[0]}*',
                            unsafe_allow_html=True
                        )
                    if r.get("companies"):
                        st.caption("Companies: " + ", ".join(r["companies"][:5]))
                with ec2:
                    already = any(s["id"]==r["id"] for s in st.session_state.saved_reports)
                    if not already:
                        if st.button(f"Save", key=f"save_pf_{r['id']}", use_container_width=True):
                            st.session_state.saved_reports.append(dict(r))
                            st.rerun()
                    else:
                        st.caption("✓ Saved")
                    ipdf = generate_briefing_pdf(r, r.get("angle","owner"))
                    st.download_button("⬇ PDF", data=ipdf,
                                      file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                                      mime="application/pdf",
                                      key=f"pdf_pf_{r['id']}",
                                      use_container_width=True)
    elif not pf_run:
        st.info("Enter postcodes above and click Run Portfolio Assessment.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — SAVED BRIEFINGS
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    saved = st.session_state.saved_reports

    sh1, sh2 = st.columns([2,2])
    with sh1:
        st.markdown("### Saved Briefings")
        st.caption("Select two or more to generate an amalgamated multi-site PDF.")
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
                        f"⬇ Amalgamated ({len(sel_reports)})",
                        data=amalg,
                        file_name=f"MN-Amalgamated-{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
            with sa1:
                if len(saved) > 0:
                    import json as _json
                    export = {
                        "source_app": "building_intelligence",
                        "report_type": "saved_briefings",
                        "exported_at": datetime.now().strftime("%d %b %Y %H:%M"),
                        "briefings": [{
                            "postcode":  r.get("postcode",""),
                            "company":   r.get("prospect",{}).get("company",""),
                            "score":     r.get("score",0),
                            "verdict":   r.get("position",{}).get("verdict",""),
                            "scoreLabel":r.get("scoreLabel",""),
                            "savedAt":   r.get("savedAt",""),
                            "angle":     r.get("angle",""),
                            "gaps":      r.get("gaps",[]),
                            "positives": r.get("positives",[]),
                            "wiredScore":r.get("wiredScore",{}),
                            "mobile":    r.get("mobile",{}),
                            "companies": r.get("companies",[]),
                        } for r in saved]
                    }
                    st.download_button(
                        f"📤 Export {len(saved)} Briefing(s) for Master Report",
                        data=_json.dumps(export, indent=2, default=str),
                        file_name=f"building_intelligence_export_{datetime.now().strftime('%Y%m%d')}.json",
                        mime="application/json",
                        use_container_width=True,
                    )

    if st.session_state.get("confirm_clear"):
        st.warning("Click Clear All again to confirm.")

    if not saved:
        st.info("No briefings saved yet.")
        st.stop()

    n_sel = len(st.session_state.get("selected_ids",set()))
    if n_sel > 0:
        st.markdown(
            f'<div style="background:#e0f2fe;border:1px solid #7dd3fc;border-radius:6px;'
            f'padding:10px 16px;font-size:13px;color:#0369a1;margin-bottom:16px">'
            f'✓ <strong>{n_sel} briefing{"s" if n_sel!=1 else ""} selected</strong> — '
            f'click Amalgamated above to generate a combined PDF</div>',
            unsafe_allow_html=True
        )

    cols = st.columns(3)
    for i, r in enumerate(saved):
        sel    = r["id"] in st.session_state.get("selected_ids",set())
        crit   = sum(1 for g in r["gaps"] if g["sev"]=="critical")
        adv    = sum(1 for g in r["gaps"] if g["sev"]=="advisory")
        ws_s   = r.get("wiredScore",{}).get("status","unconfirmed")
        ws_ico = {"certified":"🟢","not-certified":"🔴","unconfirmed":"🟡"}.get(ws_s,"🟡")
        border = "2px solid #0099b8" if sel else "1px solid #e2e8f0"
        sc_col = r["scoreColour"]
        pos_v  = r.get("position",{}).get("verdict","")
        pos_c  = r.get("position",{}).get("colour","#64748b")

        with cols[i%3]:
            st.markdown(
                f'<div style="background:#fff;border:{border};border-radius:8px;'
                f'padding:16px;margin-bottom:12px">'
                f'<div style="font-size:10px;color:#94a3b8;font-family:monospace;'
                f'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px">'
                f'{r["postcode"]}{" · "+r["prospect"].get("company","") if r["prospect"].get("company") else ""}'
                f'</div>'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">'
                f'<div style="font-size:14px;font-weight:700;color:#0f172a;max-width:140px;line-height:1.3">'
                f'{r["prospect"].get("company") or "Assessment — "+r["postcode"]}</div>'
                f'<div style="font-size:28px;font-weight:800;color:{sc_col};line-height:1">{r["score"]}</div>'
                f'</div>'
                f'{"<div style=\"font-size:12px;font-weight:600;color:"+pos_c+";margin-bottom:6px\">"+pos_v+"</div>" if pos_v else ""}'
                f'<div style="font-size:11.5px;color:#64748b;margin-bottom:6px;line-height:1.8">'
                f'<span style="color:#dc2626;font-weight:600">{crit} critical</span> · '
                f'<span style="color:#d97706;font-weight:600">{adv} advisory</span>'
                f'{" · " + r["prospect"].get("stage","") if r["prospect"].get("stage") else ""}'
                f'</div>'
                f'<div style="font-size:11.5px;color:#64748b">{ws_ico} WiredScore: {ws_s}</div>'
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
                st.download_button("⬇ PDF", data=spdf,
                                   file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                                   mime="application/pdf",
                                   key=f"spdf_{r['id']}",
                                   use_container_width=True)
            with bc3:
                if st.button("View", key=f"view_{r['id']}", use_container_width=True):
                    st.session_state.current_report   = r
                    st.session_state.ws_status        = r.get("wiredScore",{}).get("status","unconfirmed")
                    st.session_state.ws_scheme        = r.get("wiredScore",{}).get("scheme","")
                    st.session_state.ws_level         = r.get("wiredScore",{}).get("level","")
                    st.session_state.ws_verified_by   = r.get("wiredScore",{}).get("verifiedBy","")
                    st.session_state.ws_verified_at   = r.get("wiredScore",{}).get("verifiedAt","")
                    _mob = r.get("mobile", {})
                    for _op, _ki, _ko in [
                        ("EE","mob_ee_indoor","mob_ee_outdoor"),
                        ("O2","mob_o2_indoor","mob_o2_outdoor"),
                        ("Three","mob_three_indoor","mob_three_outdoor"),
                        ("Vodafone","mob_voda_indoor","mob_voda_outdoor"),
                    ]:
                        st.session_state[_ki] = _mob.get(_op, {}).get("indoor", "")
                        st.session_state[_ko] = _mob.get(_op, {}).get("outdoor", "")
                    st.session_state["mob_verified_by"] = _mob.get("verifiedBy", "")
                    st.session_state["mob_verified_at"] = _mob.get("verifiedAt", "")
                    st.rerun()
            with bc4:
                if st.button("✕", key=f"del_{r['id']}", use_container_width=True):
                    st.session_state.saved_reports = [
                        s for s in st.session_state.saved_reports if s["id"]!=r["id"]
                    ]
                    st.session_state.selected_ids.discard(r["id"])
                    st.rerun()
