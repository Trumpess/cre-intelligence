"""
api/companies_house.py
Companies House Advanced Search API.
Returns companies registered at a postcode — used to build occupier profile.
"""

import requests
import streamlit as st
from collections import Counter

BASE_URL = "https://api.company-information.service.gov.uk/advanced-search/companies"

# SIC code categories relevant to commercial property occupier intelligence
SIC_CATEGORIES = {
    "Finance / Insurance":   list(range(64000, 67000)),
    "Professional Services": list(range(69000, 75000)),
    "Technology / IT":       list(range(58000, 64000)) + list(range(95000, 96000)),
    "Life Sciences / R&D":   list(range(72000, 73000)) + list(range(86000, 87000)),
    "Property / Real Estate": list(range(68000, 69000)),
    "Retail / Consumer":     list(range(45000, 48000)) + list(range(56000, 57000)),
    "Manufacturing":         list(range(10000, 34000)),
    "Construction":          list(range(41000, 44000)),
    "Media / Creative":      list(range(73000, 75000)) + list(range(90000, 92000)),
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_occupier_data(postcode: str) -> dict:
    """
    Returns occupier profile data for a postcode.

    Returns:
        {
            "total": int,
            "active": int,
            "top_sector": str,
            "sector_breakdown": dict,
            "churn_estimate": str,
            "profile_label": str,
            "occ_score": int,   # 0-100
            "summary": str,
            "error": str | None,
            "companies": list,  # first 10 company names
        }
    """
    api_key = st.secrets["api_keys"]["companies_house"]
    pc_clean = postcode.replace(" ", "").upper()

    try:
        resp = requests.get(
            BASE_URL,
            params={
                "registered_office_address.postal_code": pc_clean,
                "company_status": "active",
                "size": 100,
            },
            auth=(api_key, ""),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        total_results = data.get("total_results", len(items))

        if not items:
            return _no_data("No companies found at this postcode")

        # Extract SIC codes
        sic_codes = []
        company_names = []
        for company in items:
            company_names.append(company.get("company_name", ""))
            for sic in company.get("sic_codes", []):
                try:
                    sic_codes.append(int(str(sic)[:5]))
                except (ValueError, TypeError):
                    pass

        # Categorise SIC codes
        sector_counts = Counter()
        for sic in sic_codes:
            for sector, codes in SIC_CATEGORIES.items():
                if sic in codes:
                    sector_counts[sector] += 1
                    break
            else:
                sector_counts["Other"] += 1

        top_sector = sector_counts.most_common(1)[0][0] if sector_counts else "Mixed"
        total_sics = sum(sector_counts.values())
        sector_pct = {k: round(v / total_sics * 100) for k, v in sector_counts.most_common(5)} if total_sics else {}

        # Profile label
        active = len(items)  # We filtered active only
        if active > 200:
            profile = "High-density occupier base"
        elif active > 100:
            profile = "Strong occupier base"
        elif active > 50:
            profile = "Moderate occupier base"
        elif active > 20:
            profile = "Small occupier base"
        else:
            profile = "Low occupier density"

        # Occupier model score
        occ_score = min(95, max(20, round((active / 200) * 100)))

        # Churn estimate (proxy based on density — high density = more transience)
        if active > 200:
            churn = "~8% estimated annual churn"
        elif active > 100:
            churn = "~6% estimated annual churn"
        elif active > 50:
            churn = "~5% estimated annual churn"
        else:
            churn = "~4% estimated annual churn"

        top_pct = list(sector_pct.items())[:2]
        sector_str = " · ".join(f"{k} {v}%" for k, v in top_pct)
        summary = f"{active} active companies · {top_sector} dominant · {churn}"

        return {
            "total": total_results,
            "active": active,
            "top_sector": top_sector,
            "sector_breakdown": sector_pct,
            "churn_estimate": churn,
            "profile_label": profile,
            "occ_score": occ_score,
            "summary": summary,
            "error": None,
            "companies": company_names[:10],
        }

    except requests.exceptions.Timeout:
        return _no_data("Companies House API timed out")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            return _no_data("Companies House: authentication failed — check API key")
        return _no_data(f"Companies House HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        return _no_data(f"Companies House API error: {e}")


def _no_data(error: str) -> dict:
    return {
        "total": 0, "active": 0, "top_sector": "Unknown",
        "sector_breakdown": {}, "churn_estimate": "Unknown",
        "profile_label": "Data unavailable",
        "occ_score": 50, "summary": "Occupier data unavailable",
        "error": error, "companies": [],
    }
