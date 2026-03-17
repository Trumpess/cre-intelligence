"""
scoring.py
Converts raw API data into a weighted composite score, gap cards,
and positive cards for the briefing.
"""

from typing import Any

# Weights must sum to 100
WEIGHTS = {
    "connectivity": 30,
    "mobile":       15,
    "epc":          10,
    "occupiers":    20,
    "flood":        10,
    "crime":        15,
}

SCORE_LABELS = {
    (80, 100): ("Strong",               "#3dd68c"),
    (65,  80): ("Good — Gaps Remain",   "#00c8f0"),
    (50,  65): ("Improvement Required", "#f5a623"),
    (0,   50): ("Significant Gaps",     "#f04f4f"),
}

MN_SERVICES = {
    "wired_missing":    ("WiredScore AP Services\nSmartScore AP Services",
                         "MN are Accredited Professionals for WiredScore and SmartScore",
                         "https://modern-networks.co.uk/wiredscore-smartscore-certification"),
    "no_fttp":          ("Fibre Optic Broadband\nNetwork-as-a-Service",
                         "Gigabit infrastructure deployment and managed network",
                         "https://modern-networks.co.uk/fibre-optic-broadband"),
    "epc_low":          ("Smart Building Technology\nAzure Managed Services",
                         "Digital infrastructure upgrades contribute to EPC improvement",
                         "https://modern-networks.co.uk/azure-managed-services"),
    "poor_mobile":      ("Business Mobile Plans\nManaged Network Services",
                         "In-building mobile coverage solutions and managed connectivity",
                         "https://modern-networks.co.uk/business-mobile-plans"),
    "flood_risk":       ("Azure Managed Services\nManaged Network Services",
                         "Cloud-based resilience and managed infrastructure with geographic redundancy",
                         "https://modern-networks.co.uk/azure-managed-services"),
    "crime":            ("Managed Firewall\nCybersecurity Services\nSecurity Awareness Training",
                         "Managed security services and ongoing compliance monitoring",
                         "https://modern-networks.co.uk/cybersecurity-services"),
    "occupiers":        ("Desktop Support\nDevice as a Service\nM365 Managed Services",
                         "End-user managed IT support for multi-occupier commercial buildings",
                         "https://modern-networks.co.uk/desktop-support"),
}


def calculate_score(ofcom: dict, epc: dict, ch: dict, flood: dict, crime: dict) -> tuple[int, str, str]:
    """Returns (composite_score, label, colour)."""
    raw = {
        "connectivity": ofcom.get("conn_score", 50),
        "mobile":       ofcom.get("mob_score",  50),
        "epc":          epc.get("epc_score",    50),
        "occupiers":    ch.get("occ_score",     50),
        "flood":        flood.get("flood_score", 100),
        "crime":        crime.get("crime_score", 60),
    }
    composite = round(sum(raw[k] * WEIGHTS[k] / 100 for k in WEIGHTS))
    composite = max(0, min(100, composite))

    for (lo, hi), (label, colour) in SCORE_LABELS.items():
        if lo <= composite <= hi:
            return composite, label, colour
    return composite, "Unknown", "#6b7a99"


def generate_gaps(ofcom: dict, epc: dict, ch: dict, flood: dict, crime: dict,
                  wiredscore_status: str = "unconfirmed") -> list[dict]:
    """
    Returns list of gap dicts ordered by severity (critical first).
    wiredscore_status: "unconfirmed" | "certified" | "not-certified"
    """
    gaps = []

    # ── WiredScore / SmartScore ───────────────────────────────────────────────
    if wiredscore_status != "certified":
        svc, detail, url = MN_SERVICES["wired_missing"]
        sev = "unconfirmed" if wiredscore_status == "unconfirmed" else "critical"
        desc = (
            "No WiredScore or SmartScore certification confirmed for this building. "
            "Competing buildings hold WiredScore Silver or above. Without certification "
            "the building cannot credibly differentiate on connectivity quality to "
            "premium tenants who now conduct digital infrastructure due diligence before signing."
            if wiredscore_status == "not-certified" else
            "Certification status has not been manually verified. Check wiredscore.com/certified-buildings "
            "and record the result in the WiredScore panel above. If not certified, this is typically "
            "the highest-value MN conversation opener."
        )
        gaps.append({
            "sev":    sev,
            "icon":   "🏆",
            "title":  "WiredScore / SmartScore — Certification Status",
            "desc":   desc,
            "source": "WiredScore Global Registry — manual verification required",
            "service": svc, "detail": detail, "url": url,
        })

    # ── Connectivity ──────────────────────────────────────────────────────────
    if not ofcom.get("fttp") and not ofcom.get("gigabit"):
        svc, detail, url = MN_SERVICES["no_fttp"]
        sev = "critical" if not ofcom.get("ufbb") else "advisory"
        tier = ofcom.get("tier", "unknown connectivity")
        gaps.append({
            "sev":   sev,
            "icon":  "📡",
            "title": "No Full Fibre (FTTP) Available",
            "desc":  (
                f"Ofcom data confirms full fibre is not available at this postcode. "
                f"Current best available: {tier}. As data demands grow — particularly AI, "
                f"cloud, and video-intensive workloads — FTTC becomes a competitive liability "
                f"versus gigabit-capable buildings in the same market."
            ),
            "source": f"Ofcom Connected Nations — postcode level data",
            "service": svc, "detail": detail, "url": url,
        })

    # ── Mobile Coverage ───────────────────────────────────────────────────────
    g4_count = ofcom.get("4g_operators", 0)
    if g4_count < 3:
        svc, detail, url = MN_SERVICES["poor_mobile"]
        good = ofcom.get("4g_good", [])
        gaps.append({
            "sev":   "critical" if g4_count < 2 else "advisory",
            "icon":  "📱",
            "title": f"Poor Indoor Mobile Coverage — {g4_count}/4 Operators",
            "desc":  (
                f"Only {', '.join(good) if good else 'no operators'} provide reliable indoor 4G signal. "
                f"Mobile dead zones are a documented occupier complaint category in multi-tenant buildings "
                f"and can directly affect tenant retention decisions."
            ),
            "source": "Ofcom Connected Nations — indoor mobile coverage data",
            "service": svc, "detail": detail, "url": url,
        })

    # ── EPC ───────────────────────────────────────────────────────────────────
    rating = epc.get("rating", "Unknown")
    if epc.get("below_2027") or rating in ("E", "F", "G"):
        svc, detail, url = MN_SERVICES["epc_low"]
        sev = "critical" if rating in ("F", "G") else "advisory"
        pot = epc.get("potential_rating", "")
        expiry = epc.get("expiry_date", "")
        gaps.append({
            "sev":   sev,
            "icon":  "⚡",
            "title": f"EPC {rating} — 2027 Compliance Risk",
            "desc":  (
                f"Current EPC rating {rating} is below the proposed 2027 minimum of C. "
                f"{'Certificate expires ' + expiry + '. ' if expiry else ''}"
                f"{'Potential rating ' + pot + ' shows improvement room. ' if pot else ''}"
                f"Without an upgrade programme this building risks commercial unlettability "
                f"under proposed regulations — direct financial exposure for the owner."
            ),
            "source": f"DLUHC EPC Register{' — expires ' + expiry if expiry else ''}",
            "service": svc, "detail": detail, "url": url,
        })
    elif epc.get("expires_soon") and not epc.get("below_2027"):
        svc, detail, url = MN_SERVICES["epc_low"]
        gaps.append({
            "sev":   "advisory",
            "icon":  "⚡",
            "title": "EPC Certificate Expiring Soon",
            "desc":  (
                f"Current EPC {rating} expires {epc.get('expiry_date', 'soon')}. "
                f"Renewal is an opportunity to improve the rating ahead of 2027 minimum C requirements."
            ),
            "source": f"DLUHC EPC Register — expires {epc.get('expiry_date', '')}",
            "service": svc, "detail": detail, "url": url,
        })

    # ── Flood Risk ────────────────────────────────────────────────────────────
    zone_num = flood.get("zone_num", 1)
    if zone_num >= 2:
        svc, detail, url = MN_SERVICES["flood_risk"]
        gaps.append({
            "sev":   "critical" if zone_num == 3 else "advisory",
            "icon":  "🌊",
            "title": f"Flood {flood.get('zone', 'Zone 2')} — Resilience Planning Required",
            "desc":  (
                f"Environment Agency data places this postcode in {flood.get('zone', 'Flood Zone 2')}. "
                f"{'High' if zone_num == 3 else 'Medium'} probability of flooding affects insurance terms, "
                f"lender requirements, and business continuity obligations for critical IT infrastructure."
            ),
            "source": "Environment Agency Flood Map for Planning",
            "service": svc, "detail": detail, "url": url,
        })

    # ── Crime ─────────────────────────────────────────────────────────────────
    crime_score = crime.get("crime_score", 70)
    if crime_score < 50:
        svc, detail, url = MN_SERVICES["crime"]
        total = crime.get("total_crimes", 0)
        top = crime.get("top_categories", [])
        top_str = ", ".join(f"{c[0]} ({c[1]})" for c in top[:2]) if top else ""
        gaps.append({
            "sev":   "critical" if crime_score < 30 else "advisory",
            "icon":  "🔒",
            "title": "Elevated Crime Profile — Cybersecurity Risk",
            "desc":  (
                f"{total} crimes recorded in the most recent period within this area. "
                f"{'Top categories: ' + top_str + '. ' if top_str else ''}"
                f"An elevated crime profile increases cybersecurity and physical security risk, "
                f"and is increasingly a factor in commercial insurance assessments."
            ),
            "source": f"data.police.uk — {crime.get('period', 'recent period')}",
            "service": svc, "detail": detail, "url": url,
        })

    # ── High occupier density — managed IT opportunity ────────────────────────
    active = ch.get("active", 0)
    if active > 80:
        svc, detail, url = MN_SERVICES["occupiers"]
        top_sector = ch.get("top_sector", "Professional Services")
        gaps.append({
            "sev":   "advisory",
            "icon":  "👥",
            "title": f"High Occupier Density — Managed IT Opportunity",
            "desc":  (
                f"{active} active companies registered at this postcode, predominantly "
                f"{top_sector}. High-density multi-occupier buildings create significant "
                f"demand for managed desktop support, device lifecycle management, and M365 services "
                f"that building ownership or management could aggregate through a single provider."
            ),
            "source": "Companies House Advanced Search API",
            "service": svc, "detail": detail, "url": url,
        })

    # Sort: critical first, then advisory, then unconfirmed
    order = {"critical": 0, "advisory": 1, "unconfirmed": 2}
    gaps.sort(key=lambda g: order.get(g["sev"], 3))
    return gaps


def generate_positives(ofcom: dict, epc: dict, ch: dict,
                        flood: dict, crime: dict) -> list[dict]:
    """Returns list of confirmed strength dicts."""
    pos = []

    if ofcom.get("fttp") or ofcom.get("gigabit"):
        pos.append({
            "icon": "📡",
            "title": "Full Fibre / Gigabit Connectivity",
            "desc": f"Ofcom confirms FTTP at this postcode. {ofcom.get('tier', 'Gigabit')} available — top tier for occupier expectations."
        })

    if ofcom.get("4g_operators", 0) >= 4:
        g5 = ofcom.get("5g_good", [])
        pos.append({
            "icon": "📱",
            "title": "Excellent Indoor Mobile Coverage",
            "desc": f"All four operators provide reliable indoor 4G. " +
                    (f"{', '.join(g5)} indoor 5G available." if g5 else "")
        })

    rating = epc.get("rating", "Unknown")
    if rating in ("A", "B", "C") and not epc.get("expires_soon"):
        pos.append({
            "icon": "⚡",
            "title": f"EPC {rating} — Meets 2027 Threshold",
            "desc": f"Current rating {rating} meets the proposed 2027 minimum C requirement. " +
                    (f"Potential {epc.get('potential_rating', '')} shows further room." if epc.get("potential_rating") else "")
        })

    if flood.get("zone_num", 1) == 1:
        pos.append({
            "icon": "🌊",
            "title": "Flood Zone 1 — Low Risk",
            "desc": "Environment Agency confirms low flood probability. Not material for insurance or lender requirements."
        })

    if crime.get("crime_score", 0) >= 70:
        pos.append({
            "icon": "🔒",
            "title": "Low Crime Profile",
            "desc": f"{crime.get('risk_label', 'Good security profile')}. Positive factor for insurance and occupier confidence."
        })

    if ch.get("active", 0) > 50:
        pos.append({
            "icon": "👥",
            "title": f"Strong Occupier Base",
            "desc": f"{ch.get('active', 0)} active companies · {ch.get('top_sector', 'Professional')} dominant · {ch.get('churn_estimate', 'low churn')}."
        })

    return pos
