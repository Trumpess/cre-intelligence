"""
api/flood_risk.py
Local SQLite lookup from Environment Agency postcode flood risk dataset.
No API call — fast and reliable.
Data: Postcodes_Risk_Assessment_All.csv from data.gov.uk
"""

import sqlite3
import os
import streamlit as st

DB_PATH = "data/flood.db"


@st.cache_data(ttl=86400, show_spinner=False)
def get_flood_risk(lat: float, lon: float, postcode: str = "") -> dict:
    """
    Look up flood risk by postcode from local database.
    lat/lon kept for API compatibility but not used.
    """
    return get_flood_risk_by_postcode(postcode)


@st.cache_data(ttl=86400, show_spinner=False)
def get_flood_risk_by_postcode(postcode: str) -> dict:
    pc = postcode.strip().upper()

    if not os.path.exists(DB_PATH):
        return _no_data("Flood risk database not found")

    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT HIGH_CNT, MED_CNT, LOW_CNT, GWTR_RISK FROM flood WHERE Postcode = ? LIMIT 1",
            (pc,)
        ).fetchone()
        conn.close()

        if row is None:
            return _zone_result(1, "Low", postcode=pc)

        high_cnt, med_cnt, low_cnt, gwtr_risk = row
        total = (high_cnt or 0) + (med_cnt or 0) + (low_cnt or 0)

        # Determine zone from counts
        if (high_cnt or 0) > 0:
            zone_num = 3
            risk     = "High"
        elif (med_cnt or 0) > 0:
            zone_num = 2
            risk     = "Medium"
        elif (low_cnt or 0) > 0:
            zone_num = 2
            risk     = "Low-Medium"
        else:
            zone_num = 1
            risk     = "Low"

        gwtr = gwtr_risk or "Unlikely"
        return _zone_result(zone_num, risk, gwtr=gwtr, postcode=pc,
                           high=high_cnt or 0, med=med_cnt or 0,
                           low=low_cnt or 0)

    except Exception as e:
        return _no_data(f"Flood DB error: {e}")


def _zone_result(zone_num, risk, gwtr="Unlikely", postcode="",
                 high=0, med=0, low=0):
    labels = {
        1: "Zone 1 — Low probability",
        2: "Zone 2 — Medium probability",
        3: "Zone 3 — High probability",
    }
    scores = {1: 100, 2: 60, 3: 20}
    summaries = {
        1: "Low flood probability from rivers and sea. No material insurance or lending risk.",
        2: "Medium probability flood zone. Relevant for insurance terms and business continuity planning.",
        3: "High probability flood zone. Significant insurance and resilience implications.",
    }
    detail = f"Rivers/sea risk: {risk}"
    if high or med or low:
        detail += f" ({high} high, {med} medium, {low} low risk properties at this postcode)"
    if gwtr and gwtr != "Unlikely":
        detail += f" · Groundwater risk: {gwtr}"

    return {
        "zone":        f"Zone {zone_num}",
        "zone_num":    zone_num,
        "risk_label":  labels[zone_num],
        "risk":        risk,
        "gwtr_risk":   gwtr,
        "flood_score": scores[zone_num],
        "summary":     summaries[zone_num],
        "detail":      detail,
        "error":       None,
    }


def _no_data(error: str) -> dict:
    return {
        "zone":        "Unknown",
        "zone_num":    1,
        "risk_label":  "Data unavailable",
        "risk":        "Unknown",
        "gwtr_risk":   "Unknown",
        "flood_score": 50,
        "summary":     "Flood risk data unavailable",
        "detail":      "",
        "error":       error,
    }