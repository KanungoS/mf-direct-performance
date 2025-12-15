#!/usr/bin/env python3

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import pytz
import os

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
DATA_DIR = "data"
PORTFOLIO_FILE = f"{DATA_DIR}/my_portfolio.csv"
OUTPUT_EXCEL = f"{DATA_DIR}/my_portfolio_updated.xlsx"

IST = pytz.timezone("Asia/Kolkata")

# --------------------------------------------------
# NAV HISTORY (MFAPI)
# --------------------------------------------------
def load_nav_history(code):
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return pd.DataFrame(columns=["date", "nav"])

        data = r.json().get("data", [])
        if not data:
            return pd.DataFrame(columns=["date", "nav"])

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df = df.dropna().sort_values("date")

        return df[["date", "nav"]]

    except Exception:
        return pd.DataFrame(columns=["date", "nav"])

# --------------------------------------------------
# GET LATEST AVAILABLE NAV (WEEKEND SAFE)
# --------------------------------------------------
def get_latest_nav(history):
    if history.empty:
        return np.nan, None

    today_ist = datetime.now(IST).date()
    eligible = history[history["date"].dt.date <= today_ist]

    if eligible.empty:
        return np.nan, None

    last = eligible.iloc[-1]
    return float(last["nav"]), last["date"].date()

# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    df = pd.read_csv(PORTFOLIO_FILE)

    # 🔒 HARDEN COLUMN NAMES (CRITICAL)
    df.columns = (
        df.columns
        .str.strip()
        .str.replace("\u00a0", " ", regex=False)
    )

    # Ensure required columns exist
    required = [
        "Scheme Code",
        "Units",
        "Total Purchase Value"
    ]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # Prepare output columns (do NOT touch exit load columns)
    df["Current NAV"] = np.nan
    df["Current Date"] = ""
    df["Current Value"] = np.nan
    df["% Deviation"] = np.nan

    for i, row in df.iterrows():
        try:
            code = int(float(row["Scheme Code"]))
        except Exception:
            continue

        history = load_nav_history(code)
        nav, nav_date = get_latest_nav(history)

        if pd.isna(nav):
            continue

        units = row["Units"]
        invested = row["Total Purchase Value"]
        current_value = units * nav

        df.at[i, "Current NAV"] = round(nav, 4)
        df.at[i, "Current Date"] = nav_date.strftime("%d-%m-%Y")
        df.at[i, "Current Value"] = round(current_value, 2)
        df.at[i, "% Deviation"] = round(
            ((current_value - invested) / invested) * 100, 2
        )

    # SAVE CSV (overwrite – as agreed)
    df.to_csv(PORTFOLIO_FILE, index=False)

    # SAVE EXCEL COPY
    df.to_excel(OUTPUT_EXCEL, index=False)

    print("✅ Portfolio updated successfully")
    print(f"📄 CSV  : {PORTFOLIO_FILE}")
    print(f"📊 Excel: {OUTPUT_EXCEL}")

# --------------------------------------------------
if __name__ == "__main__":
    main()
