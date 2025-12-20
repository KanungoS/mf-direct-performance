# scripts/nav_history_builder.py

import pandas as pd
import requests
from datetime import datetime, timedelta
import os

DATA_DIR = "data"
MASTER_FILE = f"{DATA_DIR}/master_list.csv"
NAV_HISTORY_FILE = f"{DATA_DIR}/nav_history.csv"

AMFI_URL = "https://api.mfapi.in/mf/{}"


def fetch_nav_history(scheme_code):
    url = AMFI_URL.format(scheme_code)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    master = pd.read_csv(MASTER_FILE)

    # Enforce Active schemes only
    master = master[master["Scheme_Status"] == "Active"].copy()

    all_rows = []

    for _, row in master.iterrows():
        scheme_code = str(row["SchemeCode"])
        scheme_name = row["SchemeName"]

        try:
            data = fetch_nav_history(scheme_code)
            nav_data = data.get("data", [])

            for item in nav_data:
                all_rows.append({
                    "SchemeCode": scheme_code,
                    "SchemeName": scheme_name,
                    "NAV": float(item["nav"]),
                    "NAV_Date": pd.to_datetime(item["date"], dayfirst=True)
                })

        except Exception as e:
            print(f"Failed for {scheme_code}: {e}")

    df = pd.DataFrame(all_rows)

    if df.empty:
        raise RuntimeError("nav_history build failed – no data fetched")

    df = df.sort_values(["SchemeCode", "NAV_Date"])
    df.to_csv(NAV_HISTORY_FILE, index=False)

    print("nav_history.csv updated successfully")


if __name__ == "__main__":
    main()
