"""
api/epc.py
Get Energy Performance Data API — new MHCLG service
https://api.get-energy-performance-data.communities.gov.uk
Authentication: Bearer token via GOV.UK One Login
"""

import requests
import streamlit as st
from datetime import datetime

BASE_URL = "https://api.get-energy-performance-data.communities.gov.uk/api/non-domestic/search"


@st.cache_data(ttl=86400, show_spinner=False)
def get_epc_data(postcode: str) -> dict:
    token = st.secrets["api_keys"]["epc_bearer_token"]

    try:
        resp = requests.get(
            BASE_URL,
            params={"postcode": postcode.strip()},
            headers={
                "Accept":        "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data", [])

        if not rows:
            return _no_data("No non-domestic EPC certificates found for this postcode")

        # Sort by registration date descending — most recent first
        def _date(r):
            d = r.get("registrationDate", "")
            try:
                return datetime.fromisoformat(d.replace("Z", "+00:00"))
            except Exception:
                return datetime.min

        rows_sorted = sorted(rows, key=_date, reverse=True)
        r = rows_sorted[0]

        rating     = (r.get("currentEnergyEfficiencyBand") or "").upper()
        address    = " ".join(filter(None, [
            r.get("addressLine1",""),
            r.get("addressLine2",""),
            r.get("postTown",""),
        ]))
        reg_date   = r.get("registrationDate","")
        cert_num   = r.get("certificateNumber","")

        # We don't get numeric score or expiry from this API
        # so derive what we can from the band
        score_map  = {"A":100,"B":90,"C":75,"D":50,"E":30,"F":15,"G":5}
        epc_score  = score_map.get(rating, 50)
        below_2027 = rating not in ("A","B","C") and rating != ""

        summary = f"EPC {rating}" if rating else "EPC rating unknown"
        if below_2027:
            summary += " — below proposed 2027 minimum (C)"

        return {
            "rating":           rating or "Unknown",
            "score":            epc_score,
            "potential_rating": "",
            "potential_score":  0,
            "expiry_date":      "",
            "expires_soon":     False,
            "below_2027":       below_2027,
            "address":          address,
            "lodged":           reg_date[:10] if reg_date else "",
            "cert_count":       len(rows),
            "epc_score":        epc_score,
            "summary":          summary,
            "cert_number":      cert_num,
            "error":            None,
        }

    except requests.exceptions.Timeout:
        return _no_data("EPC API timed out")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            return _no_data("EPC API: authentication failed — check Bearer token in secrets")
        if e.response is not None and e.response.status_code == 404:
            return _no_data("No EPC certificates found for this postcode")
        return _no_data(f"EPC API HTTP error: {e}")
    except requests.exceptions.RequestException as e:
        return _no_data(f"EPC API error: {e}")


def _no_data(error: str) -> dict:
    return {
        "rating": "Unknown", "score": 0,
        "potential_rating": "", "potential_score": 0,
        "expiry_date": "", "expires_soon": False, "below_2027": False,
        "address": "", "lodged": "", "cert_count": 0,
        "epc_score": 50, "summary": "EPC data unavailable",
        "cert_number": "", "error": error,
    }