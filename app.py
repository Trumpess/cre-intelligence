"""
app.py — Modern Networks Building Intelligence Platform (Internal)
Run with: streamlit run app.py
"""

import streamlit as st
import time
from datetime import datetime

from api.os_names       import get_coordinates
from api.ofcom          import get_connectivity_data
from api.uprn           import get_uprn
from api.epc            import get_epc_data
from api.companies_house import get_occupier_data
from api.flood_risk     import get_flood_risk
from api.police         import get_crime_data
from scoring            import calculate_score, generate_gaps, generate_positives
from pdf_export         import generate_briefing_pdf, generate_portfolio_pdf, generate_amalgamated_pdf

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MN Intelligence Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root{--teal:#00c8f0;--navy:#0b1829;--amber:#f5a623;--red:#f04f4f;--green:#3dd68c}
[data-testid="stSidebar"]{background:#161b26;border-right:1px solid #2a3347}
[data-testid="stSidebar"] label{color:#6b7a99!important;font-size:11px!important}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox select,
[data-testid="stSidebar"] .stTextArea textarea{
  background:#1c2333!important;color:#e8edf5!important;
  border:1px solid #2a3347!important;border-radius:5px!important}
.stTabs [data-baseweb="tab-list"]{background:#161b26;border-radius:6px;padding:4px;gap:0}
.stTabs [data-baseweb="tab"]{color:#6b7a99;background:transparent;border-radius:4px;padding:8px 20px}
.stTabs [aria-selected="true"]{background:#1c2333!important;color:#00c8f0!important}
.metric-card{background:#161b26;border:1px solid #2a3347;border-radius:6px;padding:14px;margin-bottom:8px}
.metric-card.good{border-left:3px solid #3dd68c}
.metric-card.warn{border-left:3px solid #f5a623}
.metric-card.bad {border-left:3px solid #f04f4f}
.gap-card{background:#161b26;border:1px solid #2a3347;border-radius:6px;padding:14px;margin-bottom:8px}
.gap-card.critical{border-left:3px solid #f04f4f}
.gap-card.advisory{border-left:3px solid #f5a623}
.gap-card.unconfirmed{border-left:3px solid #f5a623}
.pos-card{background:#161b26;border-left:3px solid #3dd68c;border:1px solid #2a3347;
          border-radius:6px;padding:12px;margin-bottom:8px}
.sev-badge{font-family:monospace;font-size:9px;letter-spacing:1px;padding:2px 7px;border-radius:3px}
.sev-critical{background:rgba(240,79,79,.12);color:#f04f4f;border:1px solid rgba(240,79,79,.2)}
.sev-advisory{background:rgba(245,166,35,.1);color:#f5a623;border:1px solid rgba(245,166,35,.2)}
.sev-unconfirmed{background:rgba(245,166,35,.1);color:#f5a623;border:1px solid rgba(245,166,35,.2)}
.sev-confirmed{background:rgba(61,214,140,.1);color:#3dd68c;border:1px solid rgba(61,214,140,.2)}
.ws-card{background:#161b26;border:1px solid #2a3347;border-radius:6px;padding:14px;margin-bottom:14px}
.intel-badge{background:rgba(245,166,35,.1);color:#f5a623;border:1px solid rgba(245,166,35,.2);
             font-family:monospace;font-size:9px;letter-spacing:2px;padding:3px 8px;border-radius:3px}
div[data-testid="stMetricValue"]{color:#00c8f0}
.stButton button{border-radius:5px}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "saved_reports"     not in st.session_state: st.session_state.saved_reports = []
if "portfolio_results" not in st.session_state: st.session_state.portfolio_results = []
if "current_report"    not in st.session_state: st.session_state.current_report = None
if "ws_status"         not in st.session_state: st.session_state.ws_status = "unconfirmed"
if "ws_scheme"         not in st.session_state: st.session_state.ws_scheme = ""
if "ws_level"          not in st.session_state: st.session_state.ws_level = ""
if "ws_verified_by"    not in st.session_state: st.session_state.ws_verified_by = ""
if "ws_verified_at"    not in st.session_state: st.session_state.ws_verified_at = ""

ANGLES = {
    "Building Owner":      "owner",
    "Managing Agent":      "agent",
    "Building Management": "management",
}

ANGLE_MSG = {
    "owner":      "Owner angle — frame around asset value, EPC risk, and the 4.9% valuation uplift for 1Gbps-certified buildings.",
    "agent":      "Agent angle — frame around occupier satisfaction, complaint reduction, and day-one connectivity.",
    "management": "Management angle — frame around operational reliability, security compliance, and insurance requirements.",
}

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="intel-badge">INTERNAL</div>', unsafe_allow_html=True)
    st.markdown("### Modern Networks")
    st.caption("Sales Intelligence Platform")
    st.divider()

    st.markdown("**Your Details**")
    staff_name     = st.text_input("Your name",     key="staff_name",     placeholder="e.g. Sarah Jones")
    staff_initials = st.text_input("Initials (PDF)", key="staff_initials", placeholder="SJ", max_chars=3)

    st.divider()
    st.markdown("**Property Lookup**")
    postcode_input = st.text_input("UK Postcode", key="pc_input", placeholder="e.g. EC2M 4YE").strip().upper()
    angle_label    = st.selectbox("Sales angle", list(ANGLES.keys()), key="angle_sel")
    angle_key      = ANGLES[angle_label]

    st.divider()
    st.markdown("**Prospect Details**")
    p_company = st.text_input("Company / Organisation", key="p_company", placeholder="Company name")
    p_contact = st.text_input("Contact name",           key="p_contact")
    p_title   = st.text_input("Job title",              key="p_title")
    p_email   = st.text_input("Email",                  key="p_email")
    p_phone   = st.text_input("Phone",                  key="p_phone")
    p_stage   = st.selectbox("Sales stage", [
        "", "Prospecting", "Qualified", "Meeting Booked",
        "Proposal Sent", "Negotiation", "Closed Won", "Closed Lost"
    ], key="p_stage")
    p_meeting = st.date_input("Meeting date", value=None, key="p_meeting")
    p_notes   = st.text_area("Internal notes", key="p_notes", height=90,
                              placeholder="Prior contact, known requirements, context…")

    st.divider()
    run = st.button("Run Intelligence Report", type="primary", use_container_width=True)

# ── TABS ──────────────────────────────────────────────────────────────────────
saved_count = len(st.session_state.saved_reports)
tab_labels = ["Assessment", "Portfolio",
              f"Saved Briefings ({saved_count})" if saved_count else "Saved Briefings"]
tab1, tab2, tab3 = st.tabs(tab_labels)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ASSESSMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:

    if run:
        if not postcode_input:
            st.error("Enter a postcode to run an assessment.")
            st.stop()

        # ── Data collection ────────────────────────────────────────────────
        with st.status("Pulling intelligence…", expanded=True) as status:

            st.write("🗺 OS Data Hub — resolving postcode…")
            coords = get_coordinates(postcode_input)
            if coords.get("error"):
                st.warning(f"OS Names: {coords['error']} — continuing with limited data")
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
                flood = get_flood_risk(lat, lon)

                st.write("🔒 Police API — crime profile…")
                crime = get_crime_data(lat, lon)

                st.write("🔑 OS Open UPRN — property reference…")
                uprn_result = get_uprn(lat, lon)
            else:
                flood = {"zone":"Unknown","zone_num":1,"flood_score":50,"summary":"No coordinates","error":"No coords"}
                crime = {"crime_score":60,"summary":"No coordinates","total_crimes":0,"top_categories":[],"period":"","error":"No coords"}
                uprn_result = {"uprn":"N/A","error":"No coords"}

            st.write("⚡ Scoring engine…")

            # Reset WiredScore state for new assessment
            st.session_state.ws_status    = "unconfirmed"
            st.session_state.ws_scheme    = ""
            st.session_state.ws_level     = ""
            st.session_state.ws_verified_by = ""
            st.session_state.ws_verified_at = ""

            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            gaps     = generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed")
            positives = generate_positives(ofcom, epc, ch, flood, crime)

            # Build metrics dict for PDF
            def _met(value, detail, status):
                return {"value": value, "detail": detail, "status": status}

            tier = ofcom.get("tier","Unknown")
            metrics = {
                "connectivity": _met(
                    tier,
                    f"{'FTTP confirmed' if ofcom.get('fttp') else 'FTTC only — no full fibre'}\n"
                    f"{ofcom.get('4g_operators',0)}/4 operators indoor 4G",
                    "good" if ofcom.get("fttp") or ofcom.get("gigabit") else
                    "warn" if ofcom.get("ufbb") or ofcom.get("sfbb") else "bad"
                ),
                "epc": _met(
                    f"EPC {epc.get('rating','?')}",
                    f"Score {epc.get('score',0)} · Potential {epc.get('potential_rating','?')}\n"
                    f"{'Below 2027 minimum' if epc.get('below_2027') else 'Meets 2027 threshold'}",
                    "good" if epc.get("rating","") in ("A","B","C") and not epc.get("expires_soon")
                    else "warn" if epc.get("rating","") == "D" else "bad"
                ),
                "occupiers": _met(
                    f"{ch.get('active',0)} Active",
                    f"{ch.get('top_sector','Mixed')} dominant\n{ch.get('churn_estimate','Unknown')}",
                    "good" if ch.get("active",0) > 80 else "warn" if ch.get("active",0) > 30 else "bad"
                ),
                "flood": _met(
                    flood.get("zone","Unknown"),
                    flood.get("risk_label",""),
                    "good" if flood.get("zone_num",1) == 1 else
                    "warn" if flood.get("zone_num",1) == 2 else "bad"
                ),
                "mobile": _met(
                    f"{ofcom.get('4g_operators',0)}/4 operators",
                    f"Indoor 4G: {', '.join(ofcom.get('4g_good',[])) or 'None'}\n"
                    f"{'Indoor 5G: '+', '.join(ofcom.get('5g_good',[])) if ofcom.get('5g_good') else 'No indoor 5G'}",
                    "good" if ofcom.get("4g_operators",0) >= 4 else
                    "warn" if ofcom.get("4g_operators",0) >= 2 else "bad"
                ),
                "crime": _met(
                    crime.get("risk_label","Unknown"),
                    f"{crime.get('total_crimes',0)} crimes · {crime.get('period','')}",
                    "good" if crime.get("crime_score",60) >= 70 else
                    "warn" if crime.get("crime_score",60) >= 50 else "bad"
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
                "uprn":        uprn_result.get("uprn", "N/A"),
                "lat":         lat, "lon": lon,
                "score":       score,
                "scoreLabel":  score_label,
                "scoreColour": score_colour,
                "savedAt":     datetime.now().strftime("%d %b %Y"),
                "angle":       angle_key,
                "prospect":    prospect,
                "metrics":     metrics,
                "gaps":        gaps,
                "positives":   positives,
                "raw": {
                    "ofcom": ofcom, "epc": epc, "ch": ch,
                    "flood": flood, "crime": crime,
                },
                "wiredScore": {
                    "status": "unconfirmed", "scheme": "", "level": "",
                    "verifiedBy": "", "verifiedAt": "",
                },
            }
            st.session_state.current_report = report
            status.update(label="Intelligence report ready.", state="complete", expanded=False)

    # ── Display results ────────────────────────────────────────────────────
    r = st.session_state.current_report

    if r is None:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;color:#3d4f6b">
            <div style="font-size:48px;margin-bottom:16px">🔍</div>
            <h3 style="color:#6b7a99;font-size:18px;margin-bottom:8px">No briefing loaded</h3>
            <p style="font-size:13px;max-width:360px;margin:0 auto;line-height:1.6">
            Enter a postcode and prospect details in the sidebar, then click
            <strong>Run Intelligence Report</strong>.
            </p>
        </div>""", unsafe_allow_html=True)
    else:
        P      = r["prospect"]
        sc_col = r["scoreColour"]
        ws     = r.get("wiredScore", {})

        # Header
        col_title, col_score = st.columns([3, 1])
        with col_title:
            st.caption(f"UPRN {r['uprn']}  ·  Generated {r['savedAt']}  ·  {P.get('staff','MN Staff')}")
            title_str = f"{P.get('company','')} — {r['postcode']}" if P.get("company") else f"Building Assessment — {r['postcode']}"
            st.markdown(f"### {title_str}")
            st.caption(f"{len(r['gaps'])} gaps identified  ·  {len(r['positives'])} strengths  ·  Ofcom · Companies House · EA · DLUHC · OS Names")
        with col_score:
            st.metric("Score", f"{r['score']}/100", r["scoreLabel"])

        # Action buttons
        col_pdf, col_save, col_space = st.columns([1, 1, 3])
        with col_pdf:
            # Generate PDF with current WiredScore state
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
                file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}-{r['savedAt'].replace(' ','-')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with col_save:
            already_saved = any(s["id"] == r["id"] for s in st.session_state.saved_reports)
            if already_saved:
                st.button("✓ Saved", disabled=True, use_container_width=True)
            else:
                if st.button("🔖 Save Briefing", use_container_width=True):
                    r["wiredScore"] = {
                        "status":     st.session_state.ws_status,
                        "scheme":     st.session_state.ws_scheme,
                        "level":      st.session_state.ws_level,
                        "verifiedBy": st.session_state.ws_verified_by,
                        "verifiedAt": st.session_state.ws_verified_at,
                    }
                    st.session_state.saved_reports.append(dict(r))
                    st.success("Briefing saved.")
                    st.rerun()

        st.caption(f"*{ANGLE_MSG[r.get('angle','owner')]}*")
        st.divider()

        # ── WiredScore Panel ───────────────────────────────────────────────
        ws_status = st.session_state.ws_status
        ws_col_map = {"certified": "🟢", "not-certified": "🔴", "unconfirmed": "🟡"}
        ws_icon    = ws_col_map.get(ws_status, "🟡")

        with st.container():
            st.markdown(f"#### {ws_icon} WiredScore / SmartScore Certification")
            st.markdown(
                "No public API exists for WiredScore data. "
                "[Check the WiredScore certified buildings map ↗](https://wiredscore.com/certified-buildings/) "
                "then record the result below.",
                unsafe_allow_html=False
            )

            ws_col1, ws_col2, ws_col3 = st.columns([2, 1.5, 1.5])
            with ws_col1:
                new_status = st.radio(
                    "Certification status",
                    ["unconfirmed", "certified", "not-certified"],
                    index=["unconfirmed","certified","not-certified"].index(ws_status),
                    horizontal=True,
                    key="ws_radio",
                    format_func=lambda x: {"unconfirmed":"? Unconfirmed","certified":"✓ Certified","not-certified":"✕ Not Certified"}[x]
                )
                if new_status != ws_status:
                    st.session_state.ws_status     = new_status
                    st.session_state.ws_verified_by = (staff_initials or staff_name or "MN").strip().upper()
                    st.session_state.ws_verified_at = datetime.now().strftime("%d %b %Y")
                    st.rerun()

            if st.session_state.ws_status == "certified":
                with ws_col2:
                    scheme = st.selectbox("Scheme", ["","WiredScore","SmartScore","Both"],
                                          index=["","WiredScore","SmartScore","Both"].index(st.session_state.ws_scheme)
                                          if st.session_state.ws_scheme in ["","WiredScore","SmartScore","Both"] else 0,
                                          key="ws_scheme_sel")
                    if scheme != st.session_state.ws_scheme:
                        st.session_state.ws_scheme = scheme
                with ws_col3:
                    level = st.selectbox("Level", ["","Certified","Silver","Gold","Platinum"],
                                         index=["","Certified","Silver","Gold","Platinum"].index(st.session_state.ws_level)
                                         if st.session_state.ws_level in ["","Certified","Silver","Gold","Platinum"] else 0,
                                         key="ws_level_sel")
                    if level != st.session_state.ws_level:
                        st.session_state.ws_level = level

            if st.session_state.ws_verified_at:
                st.caption(f"Recorded {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}")

        st.divider()

        # ── Metrics Grid ───────────────────────────────────────────────────
        st.markdown("#### Data Overview")
        metric_labels = {
            "connectivity": "Connectivity",
            "epc":          "Energy / EPC",
            "occupiers":    "Occupier Profile",
            "flood":        "Flood Risk",
            "mobile":       "Mobile Indoor",
            "crime":        "Crime Profile",
        }
        metrics = r["metrics"]
        keys = list(metrics.keys())
        cols = st.columns(3)
        for i, k in enumerate(keys):
            v = metrics[k]
            status_icon = {"good": "🟢", "warn": "🟡", "bad": "🔴"}.get(v["status"], "⚪")
            with cols[i % 3]:
                st.markdown(
                    f"""<div class="metric-card {v['status']}">
                    <div style="font-family:monospace;font-size:9px;color:#3d4f6b;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:5px">{metric_labels[k]}</div>
                    <div style="font-size:18px;font-weight:700;color:{'#3dd68c' if v['status']=='good' else '#f5a623' if v['status']=='warn' else '#f04f4f'};margin-bottom:4px">{v['value']}</div>
                    <div style="font-size:11px;color:#6b7a99;line-height:1.5">{v['detail'].replace(chr(10),'<br>')}</div>
                    </div>""",
                    unsafe_allow_html=True
                )

        st.divider()

        # ── Gaps ───────────────────────────────────────────────────────────
        live_gaps = generate_gaps(
            r["raw"]["ofcom"], r["raw"]["epc"], r["raw"]["ch"],
            r["raw"]["flood"], r["raw"]["crime"],
            st.session_state.ws_status
        )
        crit  = sum(1 for g in live_gaps if g["sev"] == "critical")
        adv   = sum(1 for g in live_gaps if g["sev"] == "advisory")
        uncon = sum(1 for g in live_gaps if g["sev"] == "unconfirmed")
        st.markdown(f"#### Gaps & Opportunities  "
                    f"<span style='font-size:12px;color:#f04f4f'>{crit} critical</span>  "
                    f"<span style='font-size:12px;color:#f5a623'> · {adv} advisory</span>"
                    f"{f'  <span style=\"font-size:12px;color:#f5a623\"> · {uncon} unconfirmed</span>' if uncon else ''}",
                    unsafe_allow_html=True)

        for g in live_gaps:
            sev_badge = f'<span class="sev-badge sev-{g["sev"]}">{g["sev"].upper()}</span>'
            with st.container():
                gc1, gc2 = st.columns([3, 1])
                with gc1:
                    st.markdown(
                        f"""<div class="gap-card {g['sev']}">
                        {sev_badge}
                        <div style="font-size:14px;font-weight:600;color:#e8edf5;margin:5px 0">{g['icon']} {g['title']}</div>
                        <div style="font-size:12px;color:#6b7a99;line-height:1.6;margin-bottom:6px">{g['desc']}</div>
                        <div style="font-family:monospace;font-size:9.5px;color:#3d4f6b">src: {g['source']}</div>
                        </div>""",
                        unsafe_allow_html=True
                    )
                with gc2:
                    st.markdown(
                        f"""<div style="background:#1c2333;border:1px solid #2a3347;border-radius:6px;padding:12px;height:100%">
                        <div style="font-family:monospace;font-size:8.5px;color:#0099b8;letter-spacing:1.5px;margin-bottom:5px">MN SERVICE</div>
                        <div style="font-size:12px;font-weight:600;color:#e8edf5;margin-bottom:5px;line-height:1.5">{g['service'].replace(chr(10),'<br>')}</div>
                        <div style="font-size:11px;color:#6b7a99;line-height:1.4">{g['detail']}</div>
                        </div>""",
                        unsafe_allow_html=True
                    )

        st.divider()

        # ── WiredScore as strength if certified ────────────────────────────
        live_positives = list(generate_positives(
            r["raw"]["ofcom"], r["raw"]["epc"], r["raw"]["ch"],
            r["raw"]["flood"], r["raw"]["crime"]
        ))
        if st.session_state.ws_status == "certified":
            scheme_str = st.session_state.ws_scheme or "WiredScore"
            level_str  = st.session_state.ws_level  or "Certified"
            live_positives.insert(0, {
                "icon":  "🏆",
                "title": f"{scheme_str} {level_str} Certified",
                "desc":  f"Verified {st.session_state.ws_verified_at} by {st.session_state.ws_verified_by}. "
                         "This is a differentiating asset credential — lead with it in any owner or agent conversation.",
            })

        st.markdown("#### Confirmed Strengths")
        scols = st.columns(2)
        for i, p in enumerate(live_positives):
            with scols[i % 2]:
                st.markdown(
                    f"""<div class="pos-card">
                    <span style="font-size:16px">{p['icon']}</span>
                    <strong style="color:#e8edf5;margin-left:6px">{p['title']}</strong>
                    <div style="font-size:12px;color:#6b7a99;margin-top:3px;line-height:1.5">{p['desc']}</div>
                    </div>""",
                    unsafe_allow_html=True
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Portfolio Assessment")
    st.caption("Batch-assess multiple properties. Enter one postcode per line.")

    col_in, col_opt = st.columns([2, 1])
    with col_in:
        pf_postcodes = st.text_area(
            "Postcodes (one per line, max 20)",
            height=160,
            placeholder="EC2M 4YE\nSW1A 1AA\nCB4 0WS\nW1A 1AA",
            key="pf_postcodes"
        )
    with col_opt:
        pf_client   = st.text_input("Client / Campaign name", key="pf_client")
        pf_audience = st.selectbox("Angle", list(ANGLES.keys()), key="pf_angle")
        pf_run      = st.button("Run Portfolio Assessment →", type="primary", use_container_width=True)

    if pf_run and pf_postcodes.strip():
        raw_pcs = [p.strip().upper() for p in pf_postcodes.strip().split("\n") if p.strip()]
        pcs = list(dict.fromkeys(raw_pcs))[:20]  # dedupe, max 20

        results = []
        prog = st.progress(0, text="Starting…")

        for i, pc in enumerate(pcs):
            prog.progress((i) / len(pcs), text=f"Assessing {pc}…")

            coords = get_coordinates(pc)
            lat, lon = coords.get("lat"), coords.get("lon")
            ofcom  = get_connectivity_data(pc)
            epc    = get_epc_data(pc)
            ch     = get_occupier_data(pc)
            flood  = get_flood_risk(lat, lon) if lat else {"zone":"Unknown","zone_num":1,"flood_score":50,"summary":"N/A","error":"No coords"}
            crime  = get_crime_data(lat, lon)  if lat else {"crime_score":60,"summary":"N/A","total_crimes":0,"top_categories":[],"period":"","error":"No coords"}
            uprn   = get_uprn(lat, lon)        if lat else {"uprn":"N/A"}

            score, score_label, score_colour = calculate_score(ofcom, epc, ch, flood, crime)
            gaps      = generate_gaps(ofcom, epc, ch, flood, crime, "unconfirmed")
            positives = generate_positives(ofcom, epc, ch, flood, crime)

            results.append({
                "id":          f"{pc}_{int(time.time())}_{i}",
                "postcode":    pc,
                "uprn":        uprn.get("uprn","N/A"),
                "lat": lat,    "lon": lon,
                "score":       score,
                "scoreLabel":  score_label,
                "scoreColour": score_colour,
                "savedAt":     datetime.now().strftime("%d %b %Y"),
                "angle":       ANGLES[pf_audience],
                "prospect":    {"company":"","contact":"","staff":staff_name or "MN Staff",
                                "initials":(staff_initials or "MN").upper(),"notes":"","stage":"",
                                "title":"","email":"","phone":"","meeting":""},
                "gaps":        gaps,
                "positives":   positives,
                "metrics":     {},
                "raw":         {"ofcom":ofcom,"epc":epc,"ch":ch,"flood":flood,"crime":crime},
                "wiredScore":  {"status":"unconfirmed","scheme":"","level":"","verifiedBy":"","verifiedAt":""},
            })

        prog.progress(1.0, text="Complete.")
        st.session_state.portfolio_results = results

    pf_results = st.session_state.portfolio_results
    if pf_results:
        sorted_r = sorted(pf_results, key=lambda r: r["score"])
        avg = round(sum(r["score"] for r in sorted_r) / len(sorted_r))
        total_gaps = sum(len(r["gaps"]) for r in sorted_r)

        st.divider()
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Properties",  len(sorted_r))
        mc2.metric("Avg Score",   f"{avg}/100")
        mc3.metric("Total Gaps",  total_gaps)
        mc4.metric("Urgent (<60)",sum(1 for r in sorted_r if r["score"] < 60))

        # Action buttons
        ba1, ba2, ba3 = st.columns([1, 1, 3])
        with ba1:
            if st.button("🔖 Save All", use_container_width=True):
                added = 0
                for r in sorted_r:
                    if not any(s["id"] == r["id"] for s in st.session_state.saved_reports):
                        st.session_state.saved_reports.append(dict(r))
                        added += 1
                st.success(f"{added} briefings saved.")
                st.rerun()
        with ba2:
            pdf_bytes = generate_portfolio_pdf(sorted_r, pf_client or "Portfolio",
                                               staff_name or "MN Staff")
            st.download_button(
                "⬇ Portfolio PDF",
                data=pdf_bytes,
                file_name=f"MN-Portfolio-{(pf_client or 'Report').replace(' ','-')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        # Results table
        st.markdown("#### Ranked Results — Lowest Score First")
        for i, r in enumerate(sorted_r, 1):
            sc = r["scoreColour"]
            crit = sum(1 for g in r["gaps"] if g["sev"] == "critical")
            adv  = sum(1 for g in r["gaps"] if g["sev"] == "advisory")
            tg   = r["gaps"][0] if r["gaps"] else {}

            with st.expander(
                f"#{i}  {r['postcode']}  —  "
                f"{r['score']}/100  {r['scoreLabel']}  —  "
                f"{crit} critical  ·  {adv} advisory",
                expanded=False
            ):
                ec1, ec2 = st.columns([3, 1])
                with ec1:
                    for g in r["gaps"][:3]:
                        sev_icon = "🔴" if g["sev"]=="critical" else "🟡"
                        st.caption(f"{sev_icon} {g['icon']} {g['title']}  →  {g['service'].split(chr(10))[0]}")
                with ec2:
                    # Save individual
                    already = any(s["id"] == r["id"] for s in st.session_state.saved_reports)
                    if not already:
                        if st.button(f"Save {r['postcode']}", key=f"save_pf_{r['id']}"):
                            st.session_state.saved_reports.append(dict(r))
                            st.rerun()
                    else:
                        st.caption("✓ Saved")
                    # Individual PDF
                    ipdf = generate_briefing_pdf(r, r.get("angle","owner"))
                    st.download_button(
                        "⬇ PDF",
                        data=ipdf,
                        file_name=f"MN-Briefing-{r['postcode'].replace(' ','')}.pdf",
                        mime="application/pdf",
                        key=f"pdf_pf_{r['id']}",
                    )
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
        st.caption("Select reports to generate an amalgamated multi-site PDF.")
    with sh2:
        if saved:
            sa1, sa2, sa3 = st.columns(3)
            with sa1:
                if st.button("Select All", use_container_width=True):
                    st.session_state["sel_all"] = True
                    st.rerun()
            with sa2:
                if st.button("Clear All", use_container_width=True):
                    if st.session_state.get("confirm_clear"):
                        st.session_state.saved_reports = []
                        st.session_state.pop("confirm_clear", None)
                        st.rerun()
                    else:
                        st.session_state["confirm_clear"] = True
                        st.rerun()
            with sa3:
                selected_ids = st.session_state.get("selected_ids", set())
                if len(selected_ids) >= 2:
                    sel_reports = [r for r in saved if r["id"] in selected_ids]
                    amalg_pdf   = generate_amalgamated_pdf(sel_reports, staff_name or "MN Staff")
                    st.download_button(
                        f"⬇ Amalgamated PDF ({len(sel_reports)})",
                        data=amalg_pdf,
                        file_name=f"MN-Amalgamated-{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )

    if st.session_state.get("confirm_clear"):
        st.warning("Click Clear All again to confirm removing all saved briefings.")

    if not saved:
        st.info("No briefings saved yet. Run an assessment and click Save Briefing.")
    else:
        if "selected_ids" not in st.session_state:
            st.session_state.selected_ids = set()

        if st.session_state.get("sel_all"):
            st.session_state.selected_ids = {r["id"] for r in saved}
            st.session_state.pop("sel_all", None)

        # Show selection count
        n_sel = len(st.session_state.get("selected_ids", set()))
        if n_sel > 0:
            st.caption(f"{n_sel} report{'s' if n_sel != 1 else ''} selected for amalgamated PDF")

        # Grid
        cols = st.columns(3)
        for i, r in enumerate(saved):
            sel = r["id"] in st.session_state.get("selected_ids", set())
            crit = sum(1 for g in r["gaps"] if g["sev"] == "critical")
            adv  = sum(1 for g in r["gaps"] if g["sev"] == "advisory")
            ws_s = r.get("wiredScore", {}).get("status", "unconfirmed")
            ws_icon = {"certified":"🟢","not-certified":"🔴","unconfirmed":"🟡"}.get(ws_s,"🟡")

            with cols[i % 3]:
                border = "border:1px solid #00c8f0" if sel else "border:1px solid #2a3347"
                st.markdown(
                    f"""<div style="background:#161b26;{border};border-radius:8px;
                        padding:14px;margin-bottom:10px;cursor:pointer">
                        <div style="font-family:monospace;font-size:9px;color:#00c8f0;
                             letter-spacing:1.5px;text-transform:uppercase;margin-bottom:3px">
                             {r['postcode']}{' · '+r['prospect'].get('company','') if r['prospect'].get('company') else ''}</div>
                        <div style="display:flex;justify-content:space-between;align-items:flex-start">
                          <div style="font-size:14px;font-weight:700;color:#e8edf5">
                            {r['prospect'].get('company') or 'Assessment — '+r['postcode']}</div>
                          <div style="font-size:26px;font-weight:800;color:{r['scoreColour']}">{r['score']}</div>
                        </div>
                        <div style="font-size:11.5px;color:#6b7a99;margin:6px 0">
                            {r['scoreLabel']} · {r['savedAt']}<br>
                            <span style="color:#f04f4f">{crit} critical</span> ·
                            <span style="color:#f5a623">{adv} advisory</span>
                            {' · <span style="color:#00c8f0">'+r['prospect'].get('stage','')+'</span>' if r['prospect'].get('stage') else ''}
                        </div>
                        <div style="font-size:11px;color:#6b7a99">{ws_icon} WiredScore: {ws_s}</div>
                    </div>""",
                    unsafe_allow_html=True
                )

                bc1, bc2, bc3, bc4 = st.columns(4)
                with bc1:
                    check_label = "☑ Deselect" if sel else "☐ Select"
                    if st.button(check_label, key=f"sel_{r['id']}", use_container_width=True):
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
                        st.session_state.current_report = r
                        st.session_state.ws_status    = r.get("wiredScore",{}).get("status","unconfirmed")
                        st.session_state.ws_scheme    = r.get("wiredScore",{}).get("scheme","")
                        st.session_state.ws_level     = r.get("wiredScore",{}).get("level","")
                        st.session_state.ws_verified_by = r.get("wiredScore",{}).get("verifiedBy","")
                        st.session_state.ws_verified_at = r.get("wiredScore",{}).get("verifiedAt","")
                        st.rerun()
                with bc4:
                    if st.button("✕", key=f"del_{r['id']}", use_container_width=True):
                        st.session_state.saved_reports = [
                            s for s in st.session_state.saved_reports if s["id"] != r["id"]
                        ]
                        st.session_state.selected_ids.discard(r["id"])
                        st.rerun()
