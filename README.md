# Modern Networks Building Intelligence Platform

Internal sales intelligence tool. Not for external distribution.

## Setup

### 1. Install dependencies
```
pip install -r requirements.txt
```

### 2. Add your API keys
Copy `.streamlit/secrets.toml` and fill in your keys:
- `os_names` — OS Data Hub Names API key
- `epc_email` + `epc_key` — EPC Open Data Communities credentials
- `companies_house` — Companies House API key

Environment Agency and Police APIs are open — no keys needed.

### 3. Add your downloaded data files
Place in the `data/` folder:
- `ofcom_connected_nations.csv` — Ofcom Connected Nations postcode CSV (quarterly download)
- `osopenuprn_202405.csv` — OS Open UPRN CSV (or rename to match your version)

### 4. Build the databases (one-time)
```
python setup_databases.py
```

If your files are named differently:
```
python setup_databases.py --ofcom data/your_ofcom_file.csv --uprn data/your_uprn_file.csv
```

If you want to skip UPRN (faster setup):
```
python setup_databases.py --skip-uprn
```

### 5. Run the app
```
streamlit run app.py
```

---

## Deployment (Streamlit Community Cloud)

1. Push this repo to GitHub (without `secrets.toml` and without the `data/` CSVs — both are in `.gitignore`)
2. Connect the repo at share.streamlit.io
3. Add your secrets in the Streamlit Cloud dashboard under Settings → Secrets
4. For the data files: the SQLite `.db` files need to be in the repo or generated on deploy.
   **Recommended:** commit the pre-built `.db` files to the repo (they are smaller than the source CSVs). Remove them from `.gitignore` once built.

---

## Data Sources

| Source | Method | Refresh |
|--------|--------|---------|
| OS Names API | Live API call | Real-time |
| Ofcom Connected Nations | Local SQLite (from CSV) | Quarterly |
| OS Open UPRN | Local SQLite (from CSV) | ~6 monthly |
| EPC Register | Live API call | Real-time |
| Companies House | Live API call | Real-time |
| Environment Agency | Live API call | Real-time |
| data.police.uk | Live API call | Monthly |
| WiredScore | Manual entry | Per assessment |

---

## File Structure

```
mn-intelligence/
├── app.py                  Main Streamlit application
├── scoring.py              Scoring engine and gap/positive generators
├── pdf_export.py           ReportLab PDF generation
├── setup_databases.py      One-time CSV → SQLite loader
├── requirements.txt
├── .gitignore
├── .streamlit/
│   └── secrets.toml        API keys (not committed to git)
├── api/
│   ├── os_names.py         OS Names API
│   ├── ofcom.py            Ofcom SQLite query
│   ├── uprn.py             UPRN proximity lookup
│   ├── epc.py              EPC Register API
│   ├── companies_house.py  Companies House API
│   ├── flood_risk.py       EA Flood Risk API
│   └── police.py           Police API
└── data/
    ├── ofcom.db            Built by setup_databases.py
    └── uprn.db             Built by setup_databases.py
```
