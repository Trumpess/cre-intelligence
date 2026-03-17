"""
api/ofcom.py
Queries the local SQLite database built from the Ofcom Connected Nations
postcode-level CSV. No API call — all local.
"""

import sqlite3
import streamlit as st

DB_PATH = "data/ofcom.db"

# Operators we report on
OPERATORS = ["ee", "o2", "three", "voda"]
OP_LABELS = {"ee": "EE", "o2": "O2", "three": "Three", "voda": "Vodafone"}


@st.cache_data(ttl=3600, show_spinner=False)
def get_connectivity_data(postcode: str) -> dict:
    """
    Returns connectivity data for a postcode from the local Ofcom SQLite DB.

    Returns:
        {
            "fttp": bool,
            "ufbb": bool,
            "sfbb": bool,
            "gigabit": bool,
            "tier": str,          # "Gigabit" | "Ultrafast" | "Superfast" | "Basic"
            "4g_operators": int,  # count of operators with good indoor 4G
            "5g_operators": int,
            "4g_detail": dict,    # {ee: bool, o2: bool, three: bool, voda: bool}
            "5g_detail": dict,
            "score": int,         # 0-100 connectivity score
            "summary": str,
            "error": str | None,
            "raw": dict,
        }
    """
    pc_norm = postcode.replace(" ", "").upper()

    # Also try with space (sector unit format)
    pc_spaced = postcode.strip().upper()

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT * FROM ofcom WHERE postcode = ? OR postcode = ? LIMIT 1",
            (pc_norm, pc_spaced)
        ).fetchone()
        conn.close()

        if row is None:
            return _no_data_result("Postcode not in Ofcom dataset")

        r = dict(row)

        def _bool(key):
            v = r.get(key)
            if v is None:
                return False
            try:
                return float(v) >= 50  # ≥50% coverage = treat as available
            except (TypeError, ValueError):
                return bool(v)

        fttp    = _bool("fttp")
        ufbb    = _bool("ufbb")
        sfbb    = _bool("sfbb")
        gigabit = _bool("gigabit")

        # Connectivity tier
        if fttp or gigabit:
            tier = "Gigabit (FTTP)"
        elif ufbb:
            tier = "Ultrafast"
        elif sfbb:
            tier = "Superfast (FTTC)"
        else:
            tier = "Basic / Sub-superfast"

        # Mobile coverage
        def _mob(prefix, op):
            return _bool(f"{prefix}_{op}")

        g4 = {op: _mob("4g", op) for op in OPERATORS}
        g5 = {op: _mob("5g", op) for op in OPERATORS}
        g4_count = sum(1 for v in g4.values() if v)
        g5_count = sum(1 for v in g5.values() if v)

        # Connectivity score
        if fttp or gigabit:
            conn_score = 95
        elif ufbb:
            conn_score = 78
        elif sfbb:
            conn_score = 58
        else:
            conn_score = 30

        # Mobile modifier
        mob_score = round((g4_count / 4) * 100)

        # 4G operator summary text
        g4_names = [OP_LABELS[op] for op in OPERATORS if g4[op]]
        g5_names = [OP_LABELS[op] for op in OPERATORS if g5[op]]
        summary = f"{tier} · {g4_count}/4 operators indoor 4G"
        if g5_names:
            summary += f" · {', '.join(g5_names)} indoor 5G"

        return {
            "fttp": fttp,
            "ufbb": ufbb,
            "sfbb": sfbb,
            "gigabit": gigabit,
            "tier": tier,
            "4g_operators": g4_count,
            "5g_operators": g5_count,
            "4g_detail": {OP_LABELS[op]: g4[op] for op in OPERATORS},
            "5g_detail": {OP_LABELS[op]: g5[op] for op in OPERATORS},
            "4g_good": g4_names,
            "5g_good": g5_names,
            "conn_score": conn_score,
            "mob_score": mob_score,
            "summary": summary,
            "error": None,
            "raw": r,
        }

    except Exception as e:
        return _no_data_result(f"Ofcom DB error: {e}")


def _no_data_result(error_msg: str) -> dict:
    return {
        "fttp": False, "ufbb": False, "sfbb": False, "gigabit": False,
        "tier": "Unknown", "4g_operators": 0, "5g_operators": 0,
        "4g_detail": {}, "5g_detail": {}, "4g_good": [], "5g_good": [],
        "conn_score": 50, "mob_score": 50,
        "summary": "Data unavailable",
        "error": error_msg,
        "raw": {},
    }
