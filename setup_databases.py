"""
setup_databases.py
------------------
Run this ONCE before starting the app to load your downloaded CSV files
into SQLite databases that the app queries at runtime.

Usage:
    python setup_databases.py

Point the OFCOM_CSV and UPRN_CSV variables below at your downloaded files,
or pass them as arguments:
    python setup_databases.py --ofcom path/to/ofcom.csv --uprn path/to/uprn.csv
"""

import sqlite3
import pandas as pd
import argparse
import sys
import os
import time

OFCOM_DB = "data/ofcom.db"
UPRN_DB  = "data/uprn.db"

# ── Column name mappings ──────────────────────────────────────────────────────
# Ofcom changes column names between releases. We detect which names are present
# and normalise them into our own consistent names.

OFCOM_COLUMN_CANDIDATES = {
    "postcode": ["postcode", "POSTCODE", "Postcode"],
    "sfbb":     ["sfbb_availability", "sfbb_avail_pct", "Superfast availability"],
    "ufbb":     ["ufbb_availability", "ufbb_avail_pct", "Ultrafast availability"],
    "fttp":     ["fttp_availability", "fttp_avail_pct", "Full Fibre availability",
                 "fttp_coverage", "FTTP availability"],
    "gigabit":  ["gigabit_capable", "gigabit_availability", "Gigabit availability",
                 "gigabit_capable_pct"],
    "4g_ee":    ["4g_geo_coverage_ee", "4g_availability_ee", "EE 4G indoor",
                 "ee_4g_coverage"],
    "4g_o2":    ["4g_geo_coverage_o2", "4g_availability_o2", "O2 4G indoor",
                 "o2_4g_coverage"],
    "4g_three": ["4g_geo_coverage_three", "4g_availability_three", "Three 4G indoor",
                 "three_4g_coverage"],
    "4g_voda":  ["4g_geo_coverage_vodafone", "4g_availability_vodafone",
                 "Vodafone 4G indoor", "vodafone_4g_coverage"],
    "5g_ee":    ["5g_geo_coverage_ee", "5g_availability_ee", "EE 5G indoor",
                 "ee_5g_coverage"],
    "5g_voda":  ["5g_geo_coverage_vodafone", "5g_availability_vodafone",
                 "Vodafone 5G indoor", "vodafone_5g_coverage"],
}


def detect_column(df_cols, candidates):
    for c in candidates:
        if c in df_cols:
            return c
    return None


def setup_ofcom(csv_path: str):
    print(f"\n[Ofcom] Loading {csv_path} …")
    t0 = time.time()

    # Read with low_memory=False to avoid dtype warnings on large file
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  Loaded {len(df):,} rows — columns: {list(df.columns)[:8]} …")

    cols = list(df.columns)

    # Detect and rename columns
    rename = {}
    missing = []
    for target, candidates in OFCOM_COLUMN_CANDIDATES.items():
        found = detect_column(cols, candidates)
        if found:
            rename[found] = target
        else:
            missing.append(target)

    if "postcode" not in [rename.get(c, c) for c in cols] and "postcode" not in rename.values():
        print("  ERROR: Cannot find a postcode column. Columns found:")
        print("        ", cols)
        sys.exit(1)

    if missing:
        print(f"  Warning: Could not find columns for: {missing}")
        print("  The app will handle missing columns gracefully.")

    df = df.rename(columns=rename)
    keep = ["postcode"] + [c for c in OFCOM_COLUMN_CANDIDATES.keys() if c in df.columns and c != "postcode"]
    df = df[keep].copy()

    # Normalise postcode: uppercase, strip spaces
    df["postcode"] = df["postcode"].astype(str).str.upper().str.strip()

    # Convert numeric columns, coerce errors to NaN
    for c in keep:
        if c != "postcode":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    print(f"  Writing to {OFCOM_DB} …")
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(OFCOM_DB)
    df.to_sql("ofcom", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_postcode ON ofcom (postcode)")
    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    print(f"  ✓ Done in {elapsed:.1f}s — {len(df):,} postcodes indexed")


def setup_uprn(csv_path: str):
    print(f"\n[UPRN] Loading {csv_path} …")
    print("  This file is large — may take a few minutes.")
    t0 = time.time()

    # OS Open UPRN columns: UPRN, X_COORDINATE, Y_COORDINATE, LATITUDE, LONGITUDE
    # Read only the columns we need
    try:
        df = pd.read_csv(
            csv_path,
            usecols=lambda c: c.upper() in ["UPRN", "LATITUDE", "LONGITUDE",
                                              "X_COORDINATE", "Y_COORDINATE"],
            low_memory=False,
        )
    except ValueError:
        # Fallback: read all columns
        df = pd.read_csv(csv_path, low_memory=False)

    print(f"  Loaded {len(df):,} rows — columns: {list(df.columns)}")

    # Normalise column names to lowercase
    df.columns = [c.upper() for c in df.columns]

    required = {"UPRN", "LATITUDE", "LONGITUDE"}
    missing = required - set(df.columns)
    if missing:
        print(f"  ERROR: Missing columns: {missing}")
        print(f"  Found: {list(df.columns)}")
        sys.exit(1)

    df = df[["UPRN", "LATITUDE", "LONGITUDE"]].copy()
    df["UPRN"] = df["UPRN"].astype(str)
    df["LATITUDE"] = pd.to_numeric(df["LATITUDE"], errors="coerce")
    df["LONGITUDE"] = pd.to_numeric(df["LONGITUDE"], errors="coerce")
    df = df.dropna(subset=["LATITUDE", "LONGITUDE"])

    print(f"  Writing to {UPRN_DB} …")
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(UPRN_DB)
    df.to_sql("uprn", conn, if_exists="replace", index=False)
    # Index on lat/long for proximity queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lat ON uprn (LATITUDE)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_lon ON uprn (LONGITUDE)")
    conn.commit()
    conn.close()

    elapsed = time.time() - t0
    print(f"  ✓ Done in {elapsed:.1f}s — {len(df):,} UPRNs indexed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up MN Intelligence Platform databases")
    parser.add_argument("--ofcom", default="data/ofcom_connected_nations.csv",
                        help="Path to Ofcom Connected Nations postcode CSV")
    parser.add_argument("--uprn",  default="data/osopenuprn_202405.csv",
                        help="Path to OS Open UPRN CSV")
    parser.add_argument("--skip-uprn", action="store_true",
                        help="Skip UPRN database (faster setup, UPRN lookup disabled)")
    args = parser.parse_args()

    print("=" * 60)
    print("MN Intelligence Platform — Database Setup")
    print("=" * 60)

    if not os.path.exists(args.ofcom):
        print(f"\nERROR: Ofcom CSV not found at: {args.ofcom}")
        print("Edit the --ofcom path or move the file and retry.")
        sys.exit(1)

    setup_ofcom(args.ofcom)

    if not args.skip_uprn:
        if not os.path.exists(args.uprn):
            print(f"\nWARNING: UPRN CSV not found at: {args.uprn}")
            print("Skipping UPRN setup. Run again with --uprn path/to/file.csv")
        else:
            setup_uprn(args.uprn)

    print("\n" + "=" * 60)
    print("Setup complete. You can now run: streamlit run app.py")
    print("=" * 60)
