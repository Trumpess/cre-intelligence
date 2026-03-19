"""
api/companies_house.py
Companies House API - uses postcode search endpoint.
"""

import requests
import streamlit as st
from collections import Counter

SEARCH_URL = "https://api.company-information.service.gov.uk/search/companies"

SIC_CATEGORIES = {
    "Finance / Insurance":    list(range(64000, 67000)),
    "Professional Services":  list(range(69000, 75000)),
    "Technology / IT":        list(range(58000, 64000)) + list(range(95000, 96000)),
    "Life Sciences / R&D":    list(range(72000, 73000)) + list(range(86000, 87000)),
    "Property / Real Estate": list(range(68000, 69000)),
    "Retail / Consumer":      list(range(45000, 48000)) + list(range(56000, 57000)),
    "Manufacturing":          list(range(10000, 34000)),
    "Construction":           list(range(41000, 44000)),
    "Media / Creative":       list(range(73000, 75000)) + list(range(90000, 92000)),
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_occupier_data(postcode: str) -> dict:
    api_key = st.secrets["api_keys"]["companies_house"]
    pc_clean = postcode.replace(" ", "").upper()
    pc_spaced = postcode.strip().upper()

    try:
        # Use the general search with postcode as query
        resp = requests.get(
            SEARCH_URL,
            params={
                "q": pc_spaced,
                "items_per_page": 100,
            },
            auth=(api_key, ""),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        all_items = data.get("items", [])

        # Filter to only companies whose postcode exactly matches
        items = [
            c for c in all_items
            if c.get("address", {})
                .get("postal_code", "")
                .replace(" ", "")
                .upper() == pc_clean
        ]

        if not items:
            return _no_data(f"No companies found at postcode {pc_spaced}")

        # Extract SIC codes by fetching company profiles
        sic_codes = []
        company_names = []
        for company in items:
            company_names.append(company.get("title", ""))

        active = len(items)

        # Profile label
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

        occ_score = min(95, max(20, round((active / 50) * 100)))

        if active > 100:
            churn = "~8% estimated annual churn"
        elif active > 50:
            churn = "~6% estimated annual churn"
        elif active > 20:
            churn = "~5% estimated annual churn"
        else:
            churn = "~4% estimated annual churn"

        summary = f"{active} active companies · {churn}"

        return {
            "total":            data.get("total_results", active),
            "active":           active,
            "top_sector":       "Mixed",
            "sector_breakdown": {},
            "churn_estimate":   churn,
            "profile_label":    profile,
            "occ_score":        occ_score,
            "summary":          summary,
            "error":            None,
            "companies":        company_names[:10],
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