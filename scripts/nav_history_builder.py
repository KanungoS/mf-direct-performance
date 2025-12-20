# scripts/nav_history_builder.py

import pandas as pd
import requests
from datetime import datetime, timedelta
import os

DATA_DIR = "data"
MASTER_FILE = f"{DATA_DIR}/master_list.csv"
NAV_HISTORY_FILE = f"{DATA_DIR}/nav_history.csv"

AMFI_URL = "https://api.mfapi.in/mf/{}"

# ---------------- CONFIG ----------------
MAX_YEARS_HISTORY = 2
HTTP_TIMEOUT = 20
# ----------------------------------------


def fetch_nav_history(scheme_code):
    url = AMFI_URL.format(scheme_code)
    response = requests.get(url, timeout=HTTP_TIMEOUT)
    response.raise_for_status()
    return response.json()


def main():
    if not os.path.exists(MASTER_FILE):
        raise FileNotFoundError("master_list.csv not found")

    master = pd.read_csv(MASTER_FILE)
    master.columns = master.columns.str.strip()

    # Safety: enforce Active only (even if master is already clean)
    master = master[master["Scheme_Status"] == "Active"].copy()

    if master.empty:
        raise RuntimeError("No active schemes found in master_list.csv")

    cutoff_date = datetime.today() - timedelta(days=365 * MAX_YEARS_HISTORY)
    all_rows = []

    print(f"Building NAV history (last {MAX_YEARS_HISTORY} years only)")
    print(f"Cutoff date: {cutoff_date.date()}")
    print(f"Total schemes: {len(master)}")

    for idx, row in master.iterrows():
        scheme_code = str(row["SchemeCode"]).strip()
        scheme_name = row["SchemeName"]

        try:
            data = fetch_nav_history(scheme_code)
            nav_data = data.get("data", [])

            for item in nav_data:
                nav_date = pd.to_datetime(item["date"], dayfirst=True, errors="coerce")

                if nav_date < cutoff_date:
                    # HARD STOP — older data ignored
                    continue

                all_rows.append({
                    "SchemeCode": scheme_code,
                    "SchemeName": scheme_name,
                    "NAV": float(item["nav"]),
                    "NAV_Date": nav_date
                })

        except Exception as e:
            print(f"[WARN] Failed for {scheme_code}: {e}")

        # Progress heartbeat every 25 schemes
        if (idx + 1) % 25 == 0:
            print(f"Processed {idx + 1} schemes")

    df = pd.DataFrame(all_rows)

    if df.empty:
        raise RuntimeError("NAV history build failed – no data within cutoff window")

    df = df.sort_values(["SchemeCode", "NAV_Date"])
    df.to_csv(NAV_HISTORY_FILE, index=False)

    print(f"nav_history.csv created successfully")
    print(f"Total NAV rows: {len(df)}")


if __name__ == "__main__":
    main()
