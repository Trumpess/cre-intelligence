"""
scoring.py
Scoring engine and gap/positive generator.
All gaps framed around Modern Networks' value proposition:
asset value, tenant satisfaction, operational efficiency.
"""

WEIGHTS = {
    "connectivity": 35,
    "epc":          15,
    "occupiers":    20,
    "flood":        10,
    "crime":        20,
}

SCORE_LABELS = {
    (80, 100): ("Strong Digital Infrastructure",         "#059669"),
    (65,  80): ("Good — Improvement Opportunities Exist","#0099b8"),
    (50,  65): ("Significant Gaps Identified",           "#d97706"),
    (0,   50): ("Critical Action Required",              "#dc2626"),
}


def calculate_score(ofcom, epc, ch, flood, crime):
    raw = {
        "connectivity": ofcom.get("conn_score", 50),
        "epc":          epc.get("epc_score",    50),
        "occupiers":    ch.get("occ_score",      50),
        "flood":        flood.get("flood_score", 80),
        "crime":        crime.get("crime_score", 60),
    }
    composite = round(sum(raw[k] * WEIGHTS[k] / 100 for k in WEIGHTS))
    composite = max(0, min(100, composite))
    for (lo, hi), (label, colour) in SCORE_LABELS.items():
        if lo <= composite <= hi:
            return composite, label, colour
    return composite, "Unknown", "#64748b"


def generate_gaps(ofcom, epc, ch, flood, crime, wiredscore_status="unconfirmed"):
    gaps = []

    # ── WiredScore ────────────────────────────────────────────────────────────
    if wiredscore_status != "certified":
        if wiredscore_status == "not-certified":
            desc = (
                "This building has no WiredScore or SmartScore certification. "
                "Competing buildings with certification achieve 4.9% higher valuations, "
                "8.4% higher lease renewal rates, and 19.4% lower tenant churn. "
                "Without certification, the owner cannot credibly demonstrate digital quality "
                "to premium tenants who now conduct infrastructure due diligence before signing. "
                "Modern Networks are WiredScore and SmartScore Accredited Professionals — "
                "we can lead the certification process end to end."
            )
            sev = "critical"
        else:
            desc = (
                "Certification status has not been confirmed. Use the WiredScore map to verify. "
                "If uncertified, this is typically the highest-value conversation opener — "
                "certified buildings command premium rents and attract better tenants. "
                "Modern Networks are Accredited Professionals for both WiredScore and SmartScore."
            )
            sev = "unconfirmed"
        gaps.append({
            "sev":     sev,
            "icon":    "🏆",
            "title":   "WiredScore / SmartScore Certification",
            "impact":  "Asset Value · Tenant Attraction",
            "desc":    desc,
            "source":  "WiredScore Global Registry — manual verification required",
            "service": "WiredScore AP Services\nSmartScore AP Services",
            "detail":  "MN are Accredited Professionals — we lead the full certification process",
            "url":     "https://modern-networks.co.uk/wiredscore-smartscore-certification",
            "stat":    "4.9% higher valuations for certified buildings",
        })

    # ── Connectivity ──────────────────────────────────────────────────────────
    gigabit_pct = ofcom.get("gigabit_pct", 0)
    sfbb_pct    = ofcom.get("sfbb_pct", 0)
    ufbb_pct    = ofcom.get("ufbb_pct", 0)

    if not ofcom.get("gigabit") and not ofcom.get("fttp"):
        if not ofcom.get("sfbb"):
            sev  = "critical"
            desc = (
                f"Sub-superfast connectivity is confirmed at this postcode "
                f"(gigabit coverage: {gigabit_pct:.0f}%). "
                "This is a significant competitive liability. Modern tenants — "
                "particularly technology, professional services, and life sciences "
                "organisations — require gigabit-capable infrastructure as a baseline. "
                "Buildings without it face higher void rates and lower achievable rents. "
                "Modern Networks can assess and deliver a gigabit upgrade programme."
            )
        else:
            sev  = "critical"
            desc = (
                f"Full fibre (FTTP) is not available at this postcode. "
                f"Superfast (FTTC) is present ({sfbb_pct:.0f}% coverage) but this delivers "
                "significantly lower speeds and resilience than full fibre. "
                "As AI, cloud, and data-intensive workloads grow, FTTC becomes a "
                "competitive liability versus gigabit-capable buildings in the same market. "
                "Modern Networks can assess infrastructure options and deliver an upgrade programme."
            )
        gaps.append({
            "sev":     sev,
            "icon":    "📡",
            "title":   "No Full Fibre (Gigabit) Connectivity",
            "impact":  "Asset Value · Tenant Satisfaction · Future Readiness",
            "desc":    desc,
            "source":  "Ofcom Connected Nations — postcode data",
            "service": "Fibre Optic Broadband\nNetwork-as-a-Service\nManaged Network Services",
            "detail":  "Gigabit infrastructure deployment and ongoing managed network",
            "url":     "https://modern-networks.co.uk/fibre-optic-broadband",
            "stat":    f"Current gigabit coverage: {gigabit_pct:.0f}%",
        })

    # ── EPC ───────────────────────────────────────────────────────────────────
    rating = epc.get("rating", "Unknown")
    if rating not in ("Unknown",) and (epc.get("below_2027") or rating in ("E","F","G")):
        sev = "critical" if rating in ("F","G") else "advisory"
        pot = epc.get("potential_rating","")
        exp = epc.get("expiry_date","")
        desc = (
            f"EPC rating {rating} is below the proposed 2027 minimum of C. "
            f"{'Certificate expires ' + exp + '. ' if exp else ''}"
            f"{'Potential rating ' + pot + ' shows significant improvement is achievable. ' if pot else ''}"
            "Under proposed MEES regulations, sub-C commercial buildings risk becoming "
            "unlettable — a direct financial risk to the asset owner. "
            "Modern Networks' smart building technology and managed infrastructure "
            "upgrades contribute directly to EPC improvement, particularly around "
            "energy monitoring, smart controls, and digital systems efficiency."
        )
        gaps.append({
            "sev":     sev,
            "icon":    "⚡",
            "title":   f"EPC {rating} — 2027 Compliance Risk",
            "impact":  "Asset Value · Regulatory Compliance · Lettability",
            "desc":    desc,
            "source":  f"DLUHC EPC Register{' — expires ' + exp if exp else ''}",
            "service": "Smart Building Technology\nAzure Managed Services",
            "detail":  "Digital infrastructure upgrades contribute to EPC improvement",
            "url":     "https://modern-networks.co.uk/azure-managed-services",
            "stat":    f"Potential rating: {pot}" if pot else "Improvement achievable",
        })
    elif epc.get("expires_soon") and rating not in ("Unknown",):
        gaps.append({
            "sev":     "advisory",
            "icon":    "⚡",
            "title":   "EPC Certificate Expiring Soon",
            "impact":  "Regulatory Compliance",
            "desc":    (
                f"EPC {rating} expires {epc.get('expiry_date','soon')}. "
                "Renewal is an opportunity to improve the rating ahead of 2027 "
                "minimum C requirements. Modern Networks can support the digital "
                "infrastructure component of an EPC improvement programme."
            ),
            "source":  "DLUHC EPC Register",
            "service": "Smart Building Technology",
            "detail":  "Digital upgrades contribute to EPC improvement",
            "url":     "https://modern-networks.co.uk/azure-managed-services",
            "stat":    f"Expires: {epc.get('expiry_date','')}",
        })

    # ── Flood Risk ────────────────────────────────────────────────────────────
    zone_num = flood.get("zone_num", 1)
    if zone_num >= 2 and flood.get("error") is None:
        desc = (
            f"Environment Agency data places this postcode in {flood.get('zone','Flood Zone 2')}. "
            f"{'High' if zone_num==3 else 'Medium'} probability of flooding affects "
            "commercial insurance premiums, lender requirements, and business continuity "
            "obligations for critical IT infrastructure. "
            "Modern Networks provides cloud-based resilience and geographically redundant "
            "managed infrastructure that protects building operations in high-risk locations."
        )
        gaps.append({
            "sev":     "critical" if zone_num==3 else "advisory",
            "icon":    "🌊",
            "title":   f"{flood.get('zone','Flood Zone 2')} — Resilience Planning Required",
            "impact":  "Operational Resilience · Insurance · Business Continuity",
            "desc":    desc,
            "source":  "Environment Agency Flood Map for Planning",
            "service": "Azure Managed Services\nManaged Network Services",
            "detail":  "Cloud resilience with geographic redundancy",
            "url":     "https://modern-networks.co.uk/azure-managed-services",
            "stat":    flood.get("risk_label",""),
        })

    # ── Crime / Security ──────────────────────────────────────────────────────
    crime_score = crime.get("crime_score", 70)
    if crime_score < 50 and crime.get("error") is None:
        total   = crime.get("total_crimes", 0)
        top     = crime.get("top_categories", [])
        top_str = ", ".join(f"{c[0]} ({c[1]})" for c in top[:2]) if top else ""
        desc = (
            f"{total} crimes recorded in the most recent period within this area. "
            f"{'Top categories: ' + top_str + '. ' if top_str else ''}"
            "An elevated crime profile increases cybersecurity and physical security risk "
            "and is increasingly scrutinised by commercial property insurers. "
            "Modern Networks holds ISO 27001 certification and provides managed firewall, "
            "security monitoring, and security awareness training — the full managed "
            "security service required to demonstrate compliance to insurers."
        )
        gaps.append({
            "sev":     "critical" if crime_score < 30 else "advisory",
            "icon":    "🔒",
            "title":   "Elevated Security Risk Profile",
            "impact":  "Security · Insurance Compliance · Tenant Confidence",
            "desc":    desc,
            "source":  f"data.police.uk — {crime.get('period','recent period')}",
            "service": "Cybersecurity Services\nManaged Firewall\nSecurity Awareness Training",
            "detail":  "ISO 27001 certified — full managed security service",
            "url":     "https://modern-networks.co.uk/cybersecurity-services",
            "stat":    f"{total} crimes recorded · {crime.get('period','')}",
        })

    # ── Occupier density ──────────────────────────────────────────────────────
    active = ch.get("active", 0)
    if active >= 5:
        desc = (
            f"{active} active companies are registered at this postcode. "
            f"Multi-occupier buildings with {active}+ tenants create substantial demand "
            "for managed desktop support, device lifecycle management, M365 services, "
            "and cloud phone systems. "
            "Modern Networks acts as Service Guardian — a single point of contact "
            "coordinating IT and operational technology across all tenant organisations, "
            "reducing management burden on building ownership while improving tenant experience."
        )
        gaps.append({
            "sev":     "advisory",
            "icon":    "👥",
            "title":   f"{active} Tenant Organisations — Managed IT Opportunity",
            "impact":  "Tenant Satisfaction · Operational Efficiency · Revenue",
            "desc":    desc,
            "source":  "Companies House — active registrations at postcode",
            "service": "Service Guardian\nDesktop Support\nDevice as a Service\nM365 Managed Services",
            "detail":  "Single point of contact for all tenant IT across the building",
            "url":     "https://modern-networks.co.uk",
            "stat":    f"{active} active tenant organisations",
        })

    order = {"critical": 0, "advisory": 1, "unconfirmed": 2}
    gaps.sort(key=lambda g: order.get(g["sev"], 3))
    return gaps


def generate_positives(ofcom, epc, ch, flood, crime):
    pos = []

    if ofcom.get("gigabit") or ofcom.get("fttp"):
        gig_pct = ofcom.get("gigabit_pct", 0)
        pos.append({
            "icon":  "📡",
            "title": "Gigabit / Full Fibre Connectivity",
            "desc":  f"Ofcom confirms gigabit-capable full fibre at this postcode ({gig_pct:.0f}% coverage). Top tier for tenant expectations — a genuine differentiator in the market.",
        })
    elif ofcom.get("ufbb"):
        pos.append({
            "icon":  "📡",
            "title": "Ultrafast Connectivity Available",
            "desc":  f"Ultrafast broadband ({ofcom.get('ufbb_pct',0):.0f}% coverage) is available. Above average — upgrade to full fibre would further strengthen the asset.",
        })

    rating = epc.get("rating","")
    if rating in ("A","B","C") and not epc.get("expires_soon"):
        pos.append({
            "icon":  "⚡",
            "title": f"EPC {rating} — Meets 2027 Threshold",
            "desc":  f"Current EPC {rating} meets the proposed 2027 minimum C requirement. {('Potential ' + epc.get('potential_rating','') + ' shows further room for improvement.') if epc.get('potential_rating') else ''}",
        })

    if flood.get("zone_num",1) == 1 and flood.get("error") is None:
        pos.append({
            "icon":  "🌊",
            "title": "Flood Zone 1 — Low Risk",
            "desc":  "Environment Agency confirms low flood probability. No material insurance or lender risk from flood data.",
        })

    if crime.get("crime_score",0) >= 70 and crime.get("error") is None:
        pos.append({
            "icon":  "🔒",
            "title": "Low Crime Profile",
            "desc":  f"{crime.get('risk_label','Good')}. {crime.get('total_crimes',0)} crimes recorded in the most recent period. Positive factor for tenant confidence and insurance.",
        })

    active = ch.get("active", 0)
    if active > 0:
        pos.append({
            "icon":  "👥",
            "title": f"Active Occupier Base — {active} Companies",
            "desc":  f"{active} active companies registered at this postcode. {ch.get('churn_estimate','Low churn')}. Established tenant base with managed IT upsell potential.",
        })

    return pos