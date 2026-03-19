import sqlite3
import pandas as pd
import os
import time

UPRN_DB = "data/uprn.db"
csv_path = "data/uprn_extracted/osopenuprn_202602.csv"
CHUNK_SIZE = 500000

print(f"\n[UPRN] Loading {csv_path} in chunks …")
t0 = time.time()

os.makedirs("data", exist_ok=True)
conn = sqlite3.connect(UPRN_DB)

first_chunk = True
total_rows = 0

for i, chunk in enumerate(pd.read_csv(csv_path, chunksize=CHUNK_SIZE, low_memory=False)):
    chunk.columns = [c.upper() for c in chunk.columns]
    chunk = chunk[["UPRN","LATITUDE","LONGITUDE"]].copy()
    chunk["UPRN"] = chunk["UPRN"].astype(str)
    chunk["LATITUDE"]  = pd.to_numeric(chunk["LATITUDE"],  errors="coerce")
    chunk["LONGITUDE"] = pd.to_numeric(chunk["LONGITUDE"], errors="coerce")
    chunk = chunk.dropna(subset=["LATITUDE","LONGITUDE"])
    chunk.to_sql("uprn", conn, if_exists="replace" if first_chunk else "append", index=False)
    first_chunk = False
    total_rows += len(chunk)
    print(f"  Chunk {i+1} done — {total_rows:,} rows so far")

conn.execute("CREATE INDEX IF NOT EXISTS idx_lat ON uprn (LATITUDE)")
conn.execute("CREATE INDEX IF NOT EXISTS idx_lon ON uprn (LONGITUDE)")
conn.commit()
conn.close()

print(f"\n  Done in {time.time()-t0:.1f}s — {total_rows:,} UPRNs indexed")
