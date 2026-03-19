"""
api/ofcom.py
Queries the local SQLite Ofcom database.
Falls back to postcode sector average if exact match not found.
"""

import sqlite3
import streamlit as st

DB_PATH = "data/ofcom.db"


@st.cache_data(ttl=3600, show_spinner=False)
def get_connectivity_data(postcode: str) -> dict:
    pc = postcode.replace(" ", "").upper().strip()
    sector = pc[:-2]  # e.g. EC3V1AB -> EC3V1

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        # Try exact match first
        row = conn.execute(
            "SELECT * FROM ofcom WHERE postcode = ? LIMIT 1", (pc,)
        ).fetchone()

        matched = "exact"

        # Fall back to sector average
        if row is None:
            rows = conn.execute(
                "SELECT * FROM ofcom WHERE postcode LIKE ? LIMIT 20",
                (sector + "%",)
            ).fetchall()
            if rows:
                matched = "sector"
                # Average the numeric columns
                sfbb    = _avg(rows, "sfbb")
                ufbb    = _avg(rows, "ufbb")
                gigabit = _avg(rows, "gigabit")
                row = {"sfbb": sfbb, "ufbb": ufbb, "gigabit": gigabit}
            else:
                # Fall back to district (e.g. EC3V)
                district = pc[:4] if len(pc) >= 4 else pc[:3]
                rows = conn.execute(
                    "SELECT * FROM ofcom WHERE postcode LIKE ? LIMIT 50",
                    (district + "%",)
                ).fetchall()
                if rows:
                    matched = "district"
                    sfbb    = _avg(rows, "sfbb")
                    ufbb    = _avg(rows, "ufbb")
                    gigabit = _avg(rows, "gigabit")
                    row = {"sfbb": sfbb, "ufbb": ufbb, "gigabit": gigabit}

        conn.close()

        if row is None:
            return _no_data("Postcode not found in Ofcom dataset")

        def _val(key):
            try:
                v = row[key]
                return float(v) if v is not None else 0.0
            except (TypeError, KeyError):
                return 0.0

        sfbb_pct    = _val("sfbb")
        ufbb_pct    = _val("ufbb")
        gigabit_pct = _val("gigabit")

        # Determine tier based on availability percentages
        fttp    = gigabit_pct >= 50
        gigabit = gigabit_pct >= 50
        ufbb    = ufbb_pct    >= 50
        sfbb    = sfbb_pct    >= 50

        if gigabit:
            tier = "Gigabit / Full Fibre"
        elif ufbb:
            tier = "Ultrafast (300Mbps+)"
        elif sfbb:
            tier = "Superfast (30Mbps+)"
        else:
            tier = "Sub-superfast"

        # Connectivity score
        if gigabit:
            conn_score = 95
        elif ufbb:
            conn_score = 78
        elif sfbb:
            conn_score = 55
        else:
            conn_score = 25

        # Build detail string
        coverage_note = f"Based on {matched} postcode data"
        detail = (
            f"{'✓ Gigabit/FTTP available' if gigabit else '✗ No full fibre confirmed'}\n"
            f"Superfast: {sfbb_pct:.0f}%  ·  Ultrafast: {ufbb_pct:.0f}%  ·  "
            f"Gigabit: {gigabit_pct:.0f}%\n{coverage_note}"
        )

        return {
            "fttp":          fttp,
            "ufbb":          ufbb,
            "sfbb":          sfbb,
            "gigabit":       gigabit,
            "tier":          tier,
            "sfbb_pct":      sfbb_pct,
            "ufbb_pct":      ufbb_pct,
            "gigabit_pct":   gigabit_pct,
            "4g_operators":  0,
            "5g_operators":  0,
            "4g_detail":     {},
            "5g_detail":     {},
            "4g_good":       [],
            "5g_good":       [],
            "conn_score":    conn_score,
            "mob_score":     50,
            "detail":        detail,
            "summary":       f"{tier} · {gigabit_pct:.0f}% gigabit coverage",
            "matched":       matched,
            "error":         None,
            "raw":           dict(row),
        }

    except Exception as e:
        return _no_data(f"Ofcom DB error: {e}")


def _avg(rows, key):
    vals = []
    for r in rows:
        try:
            v = r[key]
            if v is not None:
                vals.append(float(v))
        except (TypeError, KeyError):
            pass
    return sum(vals) / len(vals) if vals else 0.0


def _no_data(error: str) -> dict:
    return {
        "fttp": False, "ufbb": False, "sfbb": False, "gigabit": False,
        "tier": "Unknown", "sfbb_pct": 0, "ufbb_pct": 0, "gigabit_pct": 0,
        "4g_operators": 0, "5g_operators": 0,
        "4g_detail": {}, "5g_detail": {}, "4g_good": [], "5g_good": [],
        "conn_score": 50, "mob_score": 50,
        "detail": "Connectivity data unavailable",
        "summary": "Data unavailable",
        "matched": "none",
        "error": error,
        "raw": {},
    }