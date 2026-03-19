"""
scoring.py
Scoring, market position verdict, gap generation, and sales checklist.
"""

WEIGHTS = {
    "connectivity": 35,
    "epc":          15,
    "occupiers":    20,
    "flood":        10,
    "crime":        20,
}

SCORE_LABELS = {
    (80, 100): ("Strong Digital Infrastructure",          "#059669"),
    (65,  80): ("Good — Improvement Opportunities Exist", "#0099b8"),
    (50,  65): ("Significant Gaps Identified",            "#d97706"),
    (0,   50): ("Critical Action Required",               "#dc2626"),
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


def generate_market_position(ofcom, epc, ch, flood, crime, wiredscore_status, score):
    """
    Returns a plain-English commercial verdict on the building's market position.
    Premium Positioning / Below Market / Urgent Action Needed
    """
    has_gigabit    = ofcom.get("gigabit") or ofcom.get("fttp")
    has_superfast  = ofcom.get("sfbb") or ofcom.get("ufbb")
    epc_rating     = epc.get("rating", "Unknown")
    epc_ok         = epc_rating in ("A", "B", "C")
    ws_certified   = wiredscore_status == "certified"
    ws_confirmed   = wiredscore_status != "unconfirmed"
    critical_gaps  = sum(1 for g in generate_gaps(ofcom, epc, ch, flood, crime, wiredscore_status)
                        if g["sev"] == "critical")

    # Premium Positioning — strong connectivity, certified or confirmably no gaps
    if has_gigabit and ws_certified and epc_ok and critical_gaps == 0:
        return {
            "verdict":    "Premium Positioning",
            "colour":     "#059669",
            "bg":         "#f0fdf4",
            "border":     "#86efac",
            "icon":       "🏆",
            "headline":   "This building can command a digital premium.",
            "detail":     (
                "Gigabit connectivity confirmed, WiredScore certified, and EPC compliant. "
                "This building meets the criteria that premium tenants now demand as standard. "
                "The owner is in a position of strength — able to differentiate on digital quality, "
                "command higher rents, and attract occupiers who will pay for future-ready infrastructure."
            ),
            "opportunity": (
                "Focus the conversation on protecting and extending this advantage. "
                "WiredScore renewal, SmartScore upgrade, and managed services to maintain standards."
            ),
        }

    # Premium Positioning — gigabit + certified but EPC not ideal
    if has_gigabit and ws_certified and critical_gaps <= 1:
        return {
            "verdict":    "Premium Positioning",
            "colour":     "#059669",
            "bg":         "#f0fdf4",
            "border":     "#86efac",
            "icon":       "🏆",
            "headline":   "Strong digital positioning — one gap to address.",
            "detail":     (
                "Gigabit connectivity and WiredScore certification place this building ahead of most "
                "competitors in tenant attraction. The remaining gap should be addressed to fully "
                "protect the premium positioning into the 2027 regulatory environment."
            ),
            "opportunity": (
                "Lead with the certification strength, then open the EPC compliance conversation "
                "as a forward-looking risk management discussion."
            ),
        }

    # Below Market — has some strengths but missing key elements
    if (has_gigabit or has_superfast) and (ws_certified or not ws_confirmed) and critical_gaps <= 2:
        ws_note = (
            "WiredScore status unconfirmed — if uncertified, this is the single highest-impact action."
            if not ws_confirmed else
            "WiredScore certified but other gaps prevent full premium positioning."
        )
        return {
            "verdict":    "Below Market",
            "colour":     "#d97706",
            "bg":         "#fffbeb",
            "border":     "#fcd34d",
            "icon":       "⚠️",
            "headline":   "This building is leaving value on the table.",
            "detail":     (
                f"The building has reasonable connectivity infrastructure but is not fully certified "
                f"or compliant. {ws_note} "
                "Without certification, the owner cannot credibly differentiate on digital quality — "
                "even if the underlying infrastructure is good. Competitors with certification "
                "will win premium tenants at higher rents."
            ),
            "opportunity": (
                "This is the ideal MN prospect. The gap between current position and Premium Positioning "
                "is closeable within 60-90 days. WiredScore certification is the fastest win."
            ),
        }

    # Urgent Action Needed — multiple critical gaps, poor connectivity, or EPC risk
    return {
        "verdict":    "Urgent Action Needed",
        "colour":     "#dc2626",
        "bg":         "#fff5f5",
        "border":     "#fca5a5",
        "icon":       "🚨",
        "headline":   "This building is at risk of offering brown discounts to attract tenants.",
        "detail":     (
            f"{'No full fibre connectivity confirmed. ' if not has_gigabit and not has_superfast else ''}"
            f"{'EPC ' + epc_rating + ' creates direct lettability risk under proposed 2027 regulations. ' if not epc_ok and epc_rating != 'Unknown' else ''}"
            f"{str(critical_gaps) + ' critical digital infrastructure gaps identified. ' if critical_gaps > 0 else ''}"
            "Buildings in this position are increasingly being forced to discount rents to maintain "
            "occupancy as tenants migrate to better-connected alternatives. "
            "Without intervention, the gap to competitors will widen as digital expectations rise."
        ),
        "opportunity": (
            "High-value MN opportunity. A managed programme of connectivity upgrade, WiredScore "
            "certification, and infrastructure modernisation can shift this building's market "
            "position within 12 months. Frame as asset protection, not cost."
        ),
    }


def generate_checklist(ofcom, epc, ch, flood, crime, wiredscore_status, postcode=""):
    """
    Returns building-specific answers to the nine standard sales questions.
    """
    has_gigabit   = ofcom.get("gigabit") or ofcom.get("fttp")
    has_ufbb      = ofcom.get("ufbb")
    has_sfbb      = ofcom.get("sfbb")
    gig_pct       = ofcom.get("gigabit_pct", 0)
    epc_rating    = epc.get("rating", "Unknown")
    active        = ch.get("active", 0)
    zone_num      = flood.get("zone_num", 1)
    crime_score   = crime.get("crime_score", 70)
    ws_certified  = wiredscore_status == "certified"
    epc_ok        = epc_rating in ("A", "B", "C")

    conn_str = (
        f"Gigabit full fibre confirmed ({gig_pct:.0f}% coverage at this postcode)"
        if has_gigabit else
        f"Ultrafast broadband available" if has_ufbb else
        f"Superfast broadband available — full fibre upgrade recommended"
        if has_sfbb else
        "Sub-standard connectivity — upgrade required"
    )

    return [
        {
            "q": "Do you have experience supporting commercial, multi-tenant buildings?",
            "evidence": f"{active} active companies registered at this postcode" if active > 0 else "Multi-occupier building",
            "answer": (
                "Yes — Modern Networks supports over 2,000 UK commercial properties including "
                "160 shopping centres, 60 retail parks, and 47 science and innovation parks. "
                f"We have extensive experience managing multi-tenant environments exactly like this one"
                f"{', with ' + str(active) + ' active tenant organisations at this postcode alone' if active > 1 else ''}. "
                "We are trusted by CBRE, JLL, Savills, Avison Young, and Cushman & Wakefield."
            ),
            "strength": True,
        },
        {
            "q": "Do you understand landlord, managing agent, FM, and tenant demarcation?",
            "evidence": "MN operates as Service Guardian across all stakeholder layers",
            "answer": (
                "This is core to how we work. Modern Networks operates as your Service Guardian — "
                "an independent service integrator sitting across landlord, managing agent, FM, and tenant layers. "
                "We do not own every system; we coordinate between vendors, monitor activity, and ensure "
                "issues are directed to the right party. Each provider remains responsible for their systems. "
                "We remove the coordination burden from building management entirely."
            ),
            "strength": True,
        },
        {
            "q": "How do you support secure, segregated networks for multiple tenants?",
            "evidence": f"ISO 27001 certified · {active} tenant organisations at this postcode" if active > 0 else "ISO 27001 certified",
            "answer": (
                "We design and manage fully segregated network infrastructure for each tenant organisation, "
                "ensuring complete separation of data and traffic. Modern Networks holds ISO 27001 certification — "
                "the recognised standard for information security management. "
                f"{'With ' + str(active) + ' active companies at this postcode, ' if active > 1 else ''}"
                "we understand the complexity of multi-tenant network management and have proven "
                "processes for maintaining security across shared infrastructure."
            ),
            "strength": True,
        },
        {
            "q": "Where does your responsibility start and end within the building?",
            "evidence": "Service Guardian model — defined, documented demarcation",
            "answer": (
                "We define responsibility clearly from day one. As Service Guardian, our scope covers "
                "the building's core digital infrastructure — connectivity, network, security, and communications. "
                "We provide documented demarcation agreements so every stakeholder — landlord, managing agent, "
                "FM contractor, and tenant — knows exactly where MN responsibility starts and ends. "
                "This removes ambiguity and prevents the gaps that cause building-wide outages."
            ),
            "strength": True,
        },
        {
            "q": "What happens when there is a building-wide IT or connectivity outage?",
            "evidence": (
                f"Flood Zone {zone_num} — {'resilience planning critical' if zone_num >= 2 else 'low environmental risk'}"
            ),
            "answer": (
                "We provide proactive 24/7 monitoring and a single point of contact for any building-wide incident. "
                "Our managed service includes defined SLAs, escalation paths, and incident response procedures. "
                f"{'For this building in Flood Zone ' + str(zone_num) + ', we would recommend geographically redundant cloud infrastructure and dual-carrier connectivity as part of the managed service. ' if zone_num >= 2 else ''}"
                "Modern Networks coordinates with all third-party vendors to resolve incidents — "
                "the building operator makes one call to us, and we handle the rest."
            ),
            "strength": zone_num < 2,
        },
        {
            "q": "Do you provide resilient, dual-carrier internet connectivity for the building?",
            "evidence": conn_str,
            "answer": (
                f"{'Yes — gigabit full fibre is confirmed at this postcode (' + str(int(gig_pct)) + '% coverage). ' if has_gigabit else ''}"
                f"{'Ultrafast connectivity is available at this postcode. ' if has_ufbb and not has_gigabit else ''}"
                f"{'Superfast connectivity is currently the best available at this postcode — we would recommend a full fibre upgrade programme as a priority. ' if has_sfbb and not has_ufbb and not has_gigabit else ''}"
                f"{'Current connectivity at this postcode is below standard — a connectivity upgrade programme is the first priority. ' if not has_sfbb and not has_gigabit else ''}"
                "We provide dual-carrier resilient connectivity as standard on our managed service, "
                "ensuring continuity if a primary circuit fails. All connectivity is monitored proactively."
            ),
            "strength": has_gigabit or has_ufbb,
        },
        {
            "q": "How do you handle cybersecurity risks in a shared building environment?",
            "evidence": (
                f"{'Elevated crime profile — ' + str(crime.get('total_crimes',0)) + ' crimes recorded nearby' if crime_score < 50 else 'ISO 27001 certified security management'}"
            ),
            "answer": (
                "Modern Networks holds ISO 27001 certification and provides managed firewall, "
                "security monitoring, and security awareness training as a complete managed security service. "
                "In a multi-tenant building, we implement tenant-level network segmentation, "
                "centralised threat monitoring, and regular security audits. "
                f"{'For this location, with an elevated local crime profile, we would recommend a full security audit as an early priority. ' if crime_score < 50 else ''}"
                "We can provide the documented security controls that commercial property insurers "
                "are increasingly requiring as a condition of coverage."
            ),
            "strength": crime_score >= 50,
        },
        {
            "q": "Do you have experience supporting building systems such as BMS, CCTV, and access control?",
            "evidence": "Service Guardian — OT and IT integration",
            "answer": (
                "Yes — as Service Guardian, Modern Networks coordinates across both IT and operational technology (OT). "
                "We work alongside BMS, CCTV, and access control vendors, ensuring these systems are "
                "properly networked, monitored, and integrated with the building's core digital infrastructure. "
                "We do not replace specialist OT vendors — we coordinate between them and ensure "
                "the network infrastructure supports their systems reliably and securely."
            ),
            "strength": True,
        },
        {
            "q": "How quickly can you onboard and offboard tenants?",
            "evidence": (
                f"{active} active tenant organisations — established onboarding process"
                if active > 0 else "Proven tenant onboarding process"
            ),
            "answer": (
                "We provide day-one connectivity and managed IT services for new tenants — "
                "they can be operational from the moment they take possession. "
                f"{'With ' + str(active) + ' active companies at this postcode, ' if active > 1 else ''}"
                "our onboarding process is designed for multi-tenant commercial buildings specifically. "
                "Offboarding is equally clean — tenant network access is removed completely and securely, "
                "with no residual access to building or other tenant systems. "
                "This reduces void management burden and improves the tenant experience from day one."
            ),
            "strength": True,
        },
        {
            "q": "How will your services reduce operational burden and tenant complaints for the building operator?",
            "evidence": (
                f"{'EPC ' + epc_rating + ' — compliance risk adds operational pressure' if not epc_ok and epc_rating != 'Unknown' else ''}"
                f"{'19.4% lower tenant churn with managed digital infrastructure'}"
            ),
            "answer": (
                "Research shows 19.4% lower tenant churn where buildings have properly managed digital infrastructure. "
                "Connectivity and mobile signal are the top two categories of occupier complaints in multi-tenant buildings — "
                "Modern Networks removes both from the building operator's inbox. "
                "As Service Guardian, we are the single point of contact for all digital infrastructure issues, "
                "reducing management burden significantly. "
                f"{'For this building, addressing the EPC ' + epc_rating + ' rating through a digital infrastructure upgrade programme also reduces the regulatory compliance burden on the operator. ' if not epc_ok and epc_rating != 'Unknown' else ''}"
                "One contract, one invoice, one point of contact across connectivity, security, and managed IT."
            ),
            "strength": True,
        },
    ]


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
                "we lead the certification process end to end."
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
            "impact":  "Asset Value · Tenant Attraction · Premium Positioning",
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
        sev  = "critical" if not ofcom.get("sfbb") else "critical"
        desc = (
            f"Full fibre (FTTP) is not available at this postcode "
            f"(gigabit coverage: {gigabit_pct:.0f}%). "
            f"{'Superfast (FTTC) is present (' + str(int(sfbb_pct)) + '% coverage) but delivers significantly lower speeds and resilience. ' if ofcom.get('sfbb') else 'Sub-standard connectivity is the current best available. '}"
            "As AI, cloud, and data-intensive workloads grow, buildings without gigabit connectivity "
            "face higher void rates and lower achievable rents versus fully connected competitors. "
            "Modern Networks can assess infrastructure options and deliver a gigabit upgrade programme."
        )
        gaps.append({
            "sev":     sev,
            "icon":    "📡",
            "title":   "No Full Fibre (Gigabit) Connectivity",
            "impact":  "Asset Value · Tenant Satisfaction · Future Readiness",
            "desc":    desc,
            "source":  "Ofcom Connected Nations — postcode level data",
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
        gaps.append({
            "sev":     sev,
            "icon":    "⚡",
            "title":   f"EPC {rating} — 2027 Compliance Risk",
            "impact":  "Asset Value · Regulatory Compliance · Lettability",
            "desc":    (
                f"EPC rating {rating} is below the proposed 2027 minimum of C. "
                f"{'Certificate expires ' + exp + '. ' if exp else ''}"
                f"{'Potential rating ' + pot + ' shows significant improvement is achievable. ' if pot else ''}"
                "Under proposed MEES regulations, sub-C commercial buildings risk becoming "
                "unlettable — a direct financial risk to the asset owner. "
                "Modern Networks' smart building technology and managed infrastructure "
                "upgrades contribute directly to EPC improvement through energy monitoring, "
                "smart controls, and digital systems efficiency."
            ),
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
                "Renewal is an opportunity to improve the rating ahead of 2027 minimum C requirements."
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
        gaps.append({
            "sev":     "critical" if zone_num==3 else "advisory",
            "icon":    "🌊",
            "title":   f"{flood.get('zone','Flood Zone 2')} — Resilience Planning Required",
            "impact":  "Operational Resilience · Insurance · Business Continuity",
            "desc":    (
                f"Environment Agency data places this postcode in {flood.get('zone','Flood Zone 2')}. "
                f"{'High' if zone_num==3 else 'Medium'} probability of flooding affects "
                "commercial insurance premiums, lender requirements, and business continuity "
                "obligations for critical IT infrastructure. "
                "Modern Networks provides cloud-based resilience and geographically redundant "
                "managed infrastructure that protects building operations in high-risk locations."
            ),
            "source":  "Environment Agency — Postcodes Risk Assessment dataset",
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
        gaps.append({
            "sev":     "critical" if crime_score < 30 else "advisory",
            "icon":    "🔒",
            "title":   "Elevated Security Risk Profile",
            "impact":  "Security · Insurance Compliance · Tenant Confidence",
            "desc":    (
                f"{total} crimes recorded in the most recent period within this area. "
                f"{'Top categories: ' + top_str + '. ' if top_str else ''}"
                "An elevated crime profile increases cybersecurity and physical security risk "
                "and is increasingly scrutinised by commercial property insurers. "
                "Modern Networks holds ISO 27001 certification and provides managed firewall, "
                "security monitoring, and security awareness training."
            ),
            "source":  f"data.police.uk — {crime.get('period','recent period')}",
            "service": "Cybersecurity Services\nManaged Firewall\nSecurity Awareness Training",
            "detail":  "ISO 27001 certified — full managed security service",
            "url":     "https://modern-networks.co.uk/cybersecurity-services",
            "stat":    f"{total} crimes recorded · {crime.get('period','')}",
        })

    # ── Occupier density ──────────────────────────────────────────────────────
    active = ch.get("active", 0)
    if active >= 5:
        gaps.append({
            "sev":     "advisory",
            "icon":    "👥",
            "title":   f"{active} Tenant Organisations — Managed IT Opportunity",
            "impact":  "Tenant Satisfaction · Operational Efficiency · Revenue",
            "desc":    (
                f"{active} active companies are registered at this postcode. "
                "Multi-occupier buildings create substantial demand for managed desktop support, "
                "device lifecycle management, M365 services, and cloud phone systems. "
                "Modern Networks acts as Service Guardian — a single point of contact "
                "coordinating IT and operational technology across all tenant organisations."
            ),
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
            "title": "Gigabit / Full Fibre Connectivity Confirmed",
            "desc":  f"Ofcom confirms gigabit-capable full fibre at this postcode ({gig_pct:.0f}% coverage). Top tier — a genuine differentiator in tenant attraction.",
        })
    elif ofcom.get("ufbb"):
        pos.append({
            "icon":  "📡",
            "title": "Ultrafast Connectivity Available",
            "desc":  f"Ultrafast broadband ({ofcom.get('ufbb_pct',0):.0f}% coverage) is available. Above average — full fibre upgrade would further strengthen the asset.",
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
            "desc":  "Environment Agency data confirms low flood probability. No material insurance or lender risk.",
        })

    if crime.get("crime_score",0) >= 70 and crime.get("error") is None:
        pos.append({
            "icon":  "🔒",
            "title": "Low Crime Profile",
            "desc":  f"{crime.get('risk_label','Good')}. {crime.get('total_crimes',0)} crimes recorded. Positive for tenant confidence and insurance.",
        })

    active = ch.get("active", 0)
    if active > 0:
        pos.append({
            "icon":  "👥",
            "title": f"{active} Active Companies at This Postcode",
            "desc":  f"{ch.get('profile_label','Occupier base confirmed')}. {ch.get('churn_estimate','')}. Established tenant base with managed IT upsell potential.",
        })

    return pos