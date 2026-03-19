"""
api/companies_house.py
Companies House API - postcode search.
"""

import requests
import streamlit as st

SEARCH_URL = "https://api.company-information.service.gov.uk/search/companies"


@st.cache_data(ttl=3600, show_spinner=False)
def get_occupier_data(postcode: str) -> dict:
    api_key = st.secrets["api_keys"]["companies_house"]
    pc_clean = postcode.replace(" ", "").upper()
    pc_spaced = postcode.strip().upper()

    try:
        resp = requests.get(
            SEARCH_URL,
            params={"q": pc_spaced, "items_per_page": 100},
            auth=(api_key, ""),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        all_items = data.get("items", [])

        # Filter to exact postcode match — accept active, open, or no status
        items = [
            c for c in all_items
            if c.get("address", {})
                .get("postal_code", "")
                .replace(" ", "")
                .upper() == pc_clean
            and c.get("company_status", "") not in ("dissolved", "liquidation", "closed")
        ]

        if not items:
            return _no_data(f"No active companies found at {pc_spaced}")

        active = len(items)
        company_names = [c.get("title", "") for c in items]

        if active > 200:
            profile = "High-density occupier base"
            churn = "~8% estimated annual churn"
        elif active > 100:
            profile = "Strong occupier base"
            churn = "~6% estimated annual churn"
        elif active > 50:
            profile = "Moderate occupier base"
            churn = "~5% estimated annual churn"
        elif active > 20:
            profile = "Small occupier base"
            churn = "~4% estimated annual churn"
        else:
            profile = "Low occupier density"
            churn = "~4% estimated annual churn"

        occ_score = min(95, max(20, round((active / 50) * 100)))
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