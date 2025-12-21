# scripts/nav_history_builder.py

import pandas as pd
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# ---------------- CONFIG ----------------
DATA_DIR = "data"
MASTER_FILE = f"{DATA_DIR}/master_list.csv"
NAV_HISTORY_FILE = f"{DATA_DIR}/nav_history.csv"

AMFI_URL = "https://api.mfapi.in/mf/{}"
MAX_WORKERS = 5                 # Safe for AMFI
REQUEST_TIMEOUT = 20            # Seconds
DAYS_LOOKBACK = 730             # 2 years
# ----------------------------------------


def fetch_scheme_nav(scheme_code, scheme_name, cutoff_date):
    """Fetch NAV history for one scheme, trimmed to last 2 years"""
    rows = []
    try:
        r = requests.get(AMFI_URL.format(scheme_code), timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        data = r.json().get("data", [])

        for item in data:
            nav_date = pd.to_datetime(item["date"], dayfirst=True)
            if nav_date >= cutoff_date:
                rows.append({
                    "SchemeCode": scheme_code,
                    "SchemeName": scheme_name,
                    "NAV_Date": nav_date,
                    "NAV": float(item["nav"])
                })

        return rows

    except Exception as e:
        print(f"[WARN] {scheme_code} failed: {e}")
        return []


def main():
    if not os.path.exists(MASTER_FILE):
        raise FileNotFoundError("master_list.csv not found")

    master = pd.read_csv(MASTER_FILE)
    master.columns = master.columns.str.strip()

    if "SchemeCode" not in master.columns or "SchemeName" not in master.columns:
        raise ValueError("master_list.csv must contain SchemeCode and SchemeName")

    cutoff_date = datetime.today() - timedelta(days=DAYS_LOOKBACK)

    all_rows = []
    total = len(master)

    print(f"Starting NAV build for {total} schemes (last 2 years only)")
    print(f"Cutoff date: {cutoff_date.date()}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                fetch_scheme_nav,
                str(row["SchemeCode"]),
                row["SchemeName"],
                cutoff_date
            ): row["SchemeCode"]
            for _, row in master.iterrows()
        }

        completed = 0
        for future in as_completed(futures):
            scheme_code = futures[future]
            result = future.result()
            if result:
                all_rows.extend(result)

            completed += 1
            if completed % 25 == 0 or completed == total:
                print(f"Processed {completed}/{total} schemes")

    if not all_rows:
        raise RuntimeError("NAV history build failed — no data fetched")

    df = pd.DataFrame(all_rows)
    df = df.sort_values(["SchemeCode", "NAV_Date"])

    df.to_csv(NAV_HISTORY_FILE, index=False)

    print("nav_history.csv created successfully")
    print(f"Total rows written: {len(df)}")


if __name__ == "__main__":
    main()
