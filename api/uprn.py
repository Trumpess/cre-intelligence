"""
api/uprn.py
Finds the nearest UPRN to a given lat/lon using the local OS Open UPRN database.
"""

import sqlite3
import math
import streamlit as st

DB_PATH = "data/uprn.db"


@st.cache_data(ttl=86400, show_spinner=False)
def get_uprn(lat: float, lon: float, radius_deg: float = 0.001) -> dict:
    """
    Find nearest UPRN to coordinates using a bounding box query.
    radius_deg ≈ 100m in the UK.

    Returns:
        {"uprn": str, "error": str | None}
    """
    try:
        conn = sqlite3.connect(DB_PATH)

        lat_min = lat - radius_deg
        lat_max = lat + radius_deg
        lon_min = lon - radius_deg
        lon_max = lon + radius_deg

        rows = conn.execute(
            """SELECT UPRN, LATITUDE, LONGITUDE FROM uprn
               WHERE LATITUDE BETWEEN ? AND ?
               AND LONGITUDE BETWEEN ? AND ?
               LIMIT 50""",
            (lat_min, lat_max, lon_min, lon_max)
        ).fetchall()
        conn.close()

        if not rows:
            # Widen search
            return get_uprn(lat, lon, radius_deg * 5) if radius_deg < 0.01 else {
                "uprn": "N/A", "error": "No UPRN found near this postcode"
            }

        # Find closest by Euclidean distance (sufficient at this scale)
        closest = min(rows, key=lambda r: (r[1] - lat) ** 2 + (r[2] - lon) ** 2)
        return {"uprn": str(closest[0]), "error": None}

    except Exception as e:
        return {"uprn": "N/A", "error": f"UPRN DB error: {e}"}
