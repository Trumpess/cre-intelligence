"""
api/flood_risk.py
Environment Agency Flood Map for Planning — ArcGIS REST API.
No API key required. Checks Flood Zones 2 and 3 for a lat/lon point.
"""

import requests
import streamlit as st

# EA ArcGIS REST endpoints for flood zones
FZ3_URL = (
    "https://environment.data.gov.uk/arcgis/rest/services/EA/"
    "FloodMapForPlanningRiversAndSeaFloodZone3/MapServer/0/query"
)
FZ2_URL = (
    "https://environment.data.gov.uk/arcgis/rest/services/EA/"
    "FloodMapForPlanningRiversAndSeaFloodZone2/MapServer/0/query"
)


@st.cache_data(ttl=86400, show_spinner=False)
def get_flood_risk(lat: float, lon: float) -> dict:
    """
    Returns flood zone classification for a lat/lon point.

    Returns:
        {
            "zone": str,       # "Zone 1" | "Zone 2" | "Zone 3"
            "zone_num": int,   # 1, 2, or 3
            "risk_label": str,
            "flood_score": int, # 0-100 (100 = lowest risk)
            "summary": str,
            "error": str | None,
        }
    """
    params = {
        "geometry":     f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR":         "4326",
        "spatialRel":   "esriSpatialRelIntersects",
        "returnCountOnly": "true",
        "f":            "json",
    }

    try:
        # Check Zone 3 first (most restrictive)
        r3 = requests.get(FZ3_URL, params=params, timeout=10)
        r3.raise_for_status()
        in_fz3 = r3.json().get("count", 0) > 0

        if in_fz3:
            return _zone_result(3)

        # Check Zone 2
        r2 = requests.get(FZ2_URL, params=params, timeout=10)
        r2.raise_for_status()
        in_fz2 = r2.json().get("count", 0) > 0

        if in_fz2:
            return _zone_result(2)

        return _zone_result(1)

    except requests.exceptions.Timeout:
        return _no_data("EA Flood Risk API timed out")
    except requests.exceptions.RequestException as e:
        return _no_data(f"EA API error: {e}")


def _zone_result(zone: int) -> dict:
    labels = {
        1: ("Zone 1 — Low probability",    100, "Low flood probability. No material risk."),
        2: ("Zone 2 — Medium probability",  60, "Medium probability flood zone. Relevant for insurance and BCP planning."),
        3: ("Zone 3 — High probability",    20, "High probability flood zone. Significant insurance and resilience implications."),
    }
    label, score, summary = labels[zone]
    return {
        "zone":        f"Zone {zone}",
        "zone_num":    zone,
        "risk_label":  label,
        "flood_score": score,
        "summary":     summary,
        "error":       None,
    }


def _no_data(error: str) -> dict:
    return {
        "zone": "Unknown", "zone_num": 1, "risk_label": "Data unavailable",
        "flood_score": 50, "summary": "Flood risk data unavailable", "error": error,
    }
