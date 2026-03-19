"""
api/uprn.py
Finds the nearest UPRN to a given lat/lon.
Builds the SQLite database from uprn.csv.gz on first run.
"""

import sqlite3
import os
import pandas as pd
import streamlit as st

DB_PATH  = "data/uprn.db"
CSV_PATH = "data/uprn.csv.gz"


def _ensure_db():
    if os.path.exists(DB_PATH):
        return
    if not os.path.exists(CSV_PATH):
        return
    print("Building UPRN database from CSV — one-time setup...")
    df = pd.read_csv(CSV_PATH, compression="gzip", low_memory=False)
    df.columns = [c.upper() for c in df.columns]
    df = df[["UPRN","LATITUDE","LONGITUDE"]].copy()
    df["LATITUDE"]  = pd.to_numeric(df["LATITUDE"],  errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
    df = df.dropna(subset=["LATITUDE","LONGITUDE"])
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("uprn", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lat ON uprn (LATITUDE)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lon ON uprn (LONGITUDE)")
    conn.commit()
    conn.close()
    print(f"UPRN database built — {len(df):,} rows")


@st.cache_data(ttl=86400, show_spinner=False)
def get_uprn(lat: float, lon: float, radius_deg: float = 0.001) -> dict:
    _ensure_db()
    if not os.path.exists(DB_PATH):
        return {"uprn": "N/A", "error": "UPRN database not available"}
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            """SELECT UPRN, LATITUDE, LONGITUDE FROM uprn
               WHERE LATITUDE BETWEEN ? AND ?
               AND LONGITUDE BETWEEN ? AND ?
               LIMIT 50""",
            (lat-radius_deg, lat+radius_deg, lon-radius_deg, lon+radius_deg)
        ).fetchall()
        conn.close()

        if not rows:
            return get_uprn(lat, lon, radius_deg*5) if radius_deg < 0.01 else {
                "uprn": "N/A", "error": "No UPRN found near this postcode"
            }

        closest = min(rows, key=lambda r: (r[1]-lat)**2 + (r[2]-lon)**2)
        return {"uprn": str(closest[0]), "error": None}

    except Exception as e:
        return {"uprn": "N/A", "error": f"UPRN DB error: {e}"}
