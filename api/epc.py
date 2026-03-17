"""
api/epc.py
EPC Open Data Communities API.
Fetches non-domestic (commercial) energy performance certificates by postcode.
Free API — register at epc.opendatacommunities.org
"""

import requests
import streamlit as st
from datetime import datetime

BASE_URL = "https://epc.opendatacommunities.org/api/v1/non-domestic/search"


@st.cache_data(ttl=86400, show_spinner=False)
def get_epc_data(postcode: str) -> dict:
    """
    Returns the most recent non-domestic EPC for the postcode area.

    Returns:
        {
            "rating": str,          # "A"-"G" or "Unknown"
            "score": int,           # current energy efficiency score
            "potential_rating": str,
            "potential_score": int,
            "expiry_date": str,     # ISO date string or ""
            "expires_soon": bool,   # expires within 12 months
            "below_2027": bool,     # below proposed C minimum
            "address": str,
            "lodged": str,
            "cert_count": int,      # number of certs found
            "epc_score": int,       # 0-100 score for our model
            "summary": str,
            "error": str | None,
        }
    """
    email   = st.secrets["api_keys"]["epc_email"]
    api_key = st.secrets["api_keys"]["epc_key"]

    try:
        resp = requests.get(
            BASE_URL,
            params={"postcode": postcode.strip(), "size": 5},
            auth=(email, api_key),
            headers={"Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("rows", [])

        if not rows:
            return _no_data("No EPC certificates found for this postcode")

        # Sort by lodgement date descending, take most recent
        def _date(r):
            d = r.get("lodgement-date") or r.get("lodgement_date") or ""
            try:
                return datetime.strptime(d, "%Y-%m-%d")
            except Exception:
                return datetime.min

        rows_sorted = sorted(rows, key=_date, reverse=True)
        r = rows_sorted[0]

        # Field names vary slightly between API versions
        def _get(r, *keys, default=""):
            for k in keys:
                if k in r and r[k] not in (None, ""):
                    return r[k]
            return default

        rating           = _get(r, "current-energy-rating", "energy-rating-current").upper()
        score_raw        = _get(r, "current-energy-efficiency", "energy-efficiency-current", default=0)
        pot_rating       = _get(r, "potential-energy-rating", "energy-rating-potential").upper()
        pot_score_raw    = _get(r, "potential-energy-efficiency", "energy-efficiency-potential", default=0)
        address          = _get(r, "address1", "address", "property-name")
        lodged           = _get(r, "lodgement-date", "lodgement_date")
        expiry           = _get(r, "nominated-date", "valid-until", default="")

        try:
            score     = int(score_raw)
            pot_score = int(pot_score_raw)
        except (TypeError, ValueError):
            score = pot_score = 0

        # Check expiry
        expires_soon = False
        if expiry:
            try:
                exp_dt = datetime.strptime(expiry, "%Y-%m-%d")
                days_left = (exp_dt - datetime.now()).days
                expires_soon = days_left < 365
            except Exception:
                pass

        # Below proposed 2027 minimum of C
        below_2027 = rating not in ("A", "B", "C") and rating != ""

        # EPC model score
        epc_model_score = {
            "A": 100, "B": 90, "C": 75, "D": 50, "E": 30, "F": 15, "G": 5
        }.get(rating, 50)

        summary = f"EPC {rating} (score {score})"
        if below_2027:
            summary += " — below proposed 2027 minimum (C)"
        if expires_soon:
            summary += " — certificate expires soon"

        return {
            "rating": rating or "Unknown",
            "score": score,
            "potential_rating": pot_rating or "Unknown",
            "potential_score": pot_score,
            "expiry_date": expiry,
            "expires_soon": expires_soon,
            "below_2027": below_2027,
            "address": address,
            "lodged": lodged,
            "cert_count": len(rows),
            "epc_score": epc_model_score,
            "summary": summary,
            "error": None,
        }

    except requests.exceptions.Timeout:
        return _no_data("EPC API timed out")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            return _no_data("EPC API: authentication failed — check email and API key in secrets.toml")
        return _no_data(f"EPC API HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        return _no_data(f"EPC API error: {e}")


def _no_data(error: str) -> dict:
    return {
        "rating": "Unknown", "score": 0,
        "potential_rating": "Unknown", "potential_score": 0,
        "expiry_date": "", "expires_soon": False, "below_2027": False,
        "address": "", "lodged": "", "cert_count": 0,
        "epc_score": 50, "summary": "EPC data unavailable",
        "error": error,
    }
