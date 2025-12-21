# scripts/nav_history_builder.py

import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os

DATA_DIR = "data"
MASTER_FILE = f"{DATA_DIR}/master_list.csv"
NAV_HISTORY_FILE = f"{DATA_DIR}/nav_history.csv"

AMFI_URL = "https://api.mfapi.in/mf/{}"
MAX_YEARS = 2
CUTOFF_DATE = datetime.today() - timedelta(days=365 * MAX_YEARS)


def fetch_nav_history(scheme_code):
    url = AMFI_URL.format(scheme_code)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def normalize_dates(df):
    """
    Ensures continuous calendar dates by forward-filling NAV
    (handles weekends / holidays cleanly)
    """
    all_days = pd.date_range(
        start=df["NAV_Date"].min(),
        end=df["NAV_Date"].max(),
        freq="D"
    )

    df = (
        df.set_index("NAV_Date")
          .reindex(all_days)
          .ffill()
          .reset_index()
          .rename(columns={"index": "NAV_Date"})
    )

    return df


def main():
    master = pd.read_csv(MASTER_FILE)
    master.columns = master.columns.str.strip()

    required_cols = {"SchemeCode", "SchemeName", "Scheme_Status"}
    missing = required_cols - set(master.columns)
    if missing:
        raise ValueError(f"Missing columns in master_list.csv: {missing}")

    master = master[master["Scheme_Status"] == "Active"].copy()

    all_rows = []
    total = len(master)

    print(f"Building NAV history for {total} active direct schemes (last {MAX_YEARS} years)")

    for i, row in master.iterrows():
        scheme_code = str(row["SchemeCode"]).strip()
        scheme_name = row["SchemeName"]

        try:    
            data = fetch_nav_history(scheme_code)
            nav_data = data.get("data", [])

            rows = []
            for item in nav_data:
                nav_date = datetime.strptime(item["date"], "%d-%m-%Y")
                if nav_date < CUTOFF_DATE:
                    break

                rows.append({
                    "NAV_Date": nav_date.date(),
                    "NAV": float(item["nav"])
                })

            if rows:
                df_scheme = pd.DataFrame(rows)
                df_scheme = normalize_dates(df_scheme)

                df_scheme["SchemeCode"] = scheme_code
                df_scheme["SchemeName"] = scheme_name

                all_rows.append(df_scheme)

        except Exception as e:
            print(f"Failed for {scheme_code}: {e}")

        if (i + 1) % 200 == 0:
            print(f"Processed {i + 1}/{total} schemes")

        time.sleep(0.05)  # polite throttle

    final_df = pd.concat(all_rows, ignore_index=True)

    if final_df.empty:
        raise RuntimeError("nav_history build failed – no data created")

    final_df = final_df.sort_values(["SchemeCode", "NAV_Date"])
    final_df.to_csv(NAV_HISTORY_FILE, index=False)

    size_mb = os.path.getsize(NAV_HISTORY_FILE) / (1024 * 1024)
    print(f"nav_history.csv created | rows: {len(final_df)} | size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
