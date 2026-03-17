"""
api/os_names.py
OS Names API — resolves a UK postcode to latitude/longitude.
Free tier, 250,000 calls/month.
"""

import requests
import streamlit as st

BASE_URL = "https://api.os.uk/search/names/v1/find"


@st.cache_data(ttl=86400, show_spinner=False)
def get_coordinates(postcode: str) -> dict:
    """
    Query OS Names API for a postcode and return lat/lon + display name.

    Returns:
        {
            "lat": float,
            "lon": float,
            "display_name": str,
            "local_type": str,   # e.g. "Postcode"
            "county": str,
            "error": str | None
        }
    """
    api_key = st.secrets["api_keys"]["os_names"]
    pc = postcode.replace(" ", "").upper()

    try:
        resp = requests.get(
            BASE_URL,
            params={"query": pc, "key": api_key, "maxresults": 1},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return {"lat": None, "lon": None, "display_name": pc,
                    "local_type": "", "county": "", "error": "Postcode not found"}

        r = results[0].get("GAZETTEER_ENTRY", {})
        lat = r.get("GEOMETRY_Y")  # WGS84 latitude
        lon = r.get("GEOMETRY_X")  # WGS84 longitude
        name = r.get("NAME1", pc)
        local_type = r.get("LOCAL_TYPE", "")
        county = r.get("COUNTY_UNITARY", r.get("REGION", ""))

        if lat is None or lon is None:
            return {"lat": None, "lon": None, "display_name": name,
                    "local_type": local_type, "county": county,
                    "error": "Coordinates not returned"}

        return {
            "lat": float(lat),
            "lon": float(lon),
            "display_name": name,
            "local_type": local_type,
            "county": county,
            "error": None,
        }

    except requests.exceptions.Timeout:
        return {"lat": None, "lon": None, "display_name": pc,
                "local_type": "", "county": "", "error": "OS Names API timed out"}
    except requests.exceptions.RequestException as e:
        return {"lat": None, "lon": None, "display_name": pc,
                "local_type": "", "county": "", "error": f"OS Names API error: {e}"}
