"""
api/police.py
data.police.uk — Street-level crime data by lat/lon.
No API key required.
"""

import requests
import streamlit as st
from datetime import datetime, timedelta
from collections import Counter

BASE_URL = "https://data.police.uk/api/crimes-street/all-crime"

# Categories we highlight for commercial property
RELEVANT_CATEGORIES = {
    "burglary":              "Burglary",
    "criminal-damage-arson": "Criminal damage",
    "theft-from-the-person": "Theft",
    "vehicle-crime":         "Vehicle crime",
    "robbery":               "Robbery",
    "shoplifting":           "Shoplifting",
    "drugs":                 "Drug offences",
    "violent-crime":         "Violent crime",
    "other-crime":           "Other crime",
    "anti-social-behaviour": "Anti-social behaviour",
}


@st.cache_data(ttl=86400, show_spinner=False)
def get_crime_data(lat: float, lon: float) -> dict:
    """
    Returns crime profile for a location using the last available month.

    Returns:
        {
            "total_crimes": int,
            "top_categories": list,   # [(category_label, count), ...]
            "crime_score": int,       # 0-100 (100 = lowest crime)
            "risk_label": str,
            "summary": str,
            "period": str,
            "error": str | None,
        }
    """
    # Try the most recent complete month (police data is ~2 months behind)
    date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m")

    try:
        resp = requests.get(
            BASE_URL,
            params={"lat": round(lat, 4), "lng": round(lon, 4), "date": date},
            timeout=15,
        )
        resp.raise_for_status()
        crimes = resp.json()

        if not crimes:
            # Try previous month
            date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m")
            resp = requests.get(
                BASE_URL,
                params={"lat": round(lat, 4), "lng": round(lon, 4), "date": date},
                timeout=15,
            )
            crimes = resp.json() if resp.ok else []

        total = len(crimes)
        cats = Counter(c.get("category", "other-crime") for c in crimes)
        top = [(RELEVANT_CATEGORIES.get(k, k.replace("-", " ").title()), v)
               for k, v in cats.most_common(4)]

        # Score: based on absolute count within ~500m radius
        # Police API returns crimes within ~1 mile; typical commercial area:
        # <50 = low, 50-150 = average, 150-300 = elevated, >300 = high
        if total < 50:
            score, label = 90, "Low crime profile"
        elif total < 150:
            score, label = 70, "Average crime profile"
        elif total < 300:
            score, label = 45, "Elevated crime profile"
        else:
            score, label = 25, "High crime area"

        summary = f"{total} crimes recorded ({date}) · {label}"
        top_str = ", ".join(f"{c} ({n})" for c, n in top[:2])
        if top_str:
            summary += f" · Top: {top_str}"

        return {
            "total_crimes":    total,
            "top_categories":  top,
            "crime_score":     score,
            "risk_label":      label,
            "summary":         summary,
            "period":          date,
            "error":           None,
        }

    except requests.exceptions.Timeout:
        return _no_data("Police API timed out")
    except requests.exceptions.RequestException as e:
        return _no_data(f"Police API error: {e}")


def _no_data(error: str) -> dict:
    return {
        "total_crimes": 0, "top_categories": [],
        "crime_score": 60, "risk_label": "Data unavailable",
        "summary": "Crime data unavailable", "period": "",
        "error": error,
    }
