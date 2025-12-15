#!/usr/bin/env python3

import pandas as pd
import numpy as np
import requests
from datetime import datetime

PORTFOLIO_FILE = "data/my_portfolio.csv"
OUTPUT_EXCEL = "data/my_portfolio_updated.xlsx"  # optional view-only file

# --------------------------------------------------
# Load latest NAV per scheme from AMFI
# --------------------------------------------------
def load_amfi_nav():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    records = []
    for line in r.text.splitlines():
        parts = line.split(";")
        if len(parts) >= 6 and parts[0].isdigit():
            records.append({
                "Scheme Code": int(parts[0]),
                "NAV": float(parts[4]),
                "NAV Date": datetime.strptime(parts[5], "%d-%b-%Y").date()
            })

    nav_df = pd.DataFrame(records)

    # 🔑 Keep latest NAV PER SCHEME (not global date)
    nav_df = (
        nav_df.sort_values(["Scheme Code", "NAV Date"])
              .groupby("Scheme Code", as_index=False)
              .tail(1)
    )

    return nav_df

# --------------------------------------------------
def main():
    df = pd.read_csv(PORTFOLIO_FILE)
    df.columns = df.columns.str.strip()

    nav_df = load_amfi_nav()

    # Ensure columns exist
    for col in ["Current NAV", "Current Date", "Current Value", "% Deviation"]:
        if col not in df.columns:
            df[col] = ""

    for i, row in df.iterrows():
        scheme_code = int(row["Scheme Code"])
        nav_row = nav_df[nav_df["Scheme Code"] == scheme_code]

        if nav_row.empty:
            continue

        nav = nav_row.iloc[0]["NAV"]
        nav_date = nav_row.iloc[0]["NAV Date"]

        units = float(row["Units"])
        invested = float(row["Total Purchase Value"])

        current_value = units * nav
	deviation = ((current_value - invested) / invested) * 100

	df.at[i, "Current NAV"] = round(nav, 4)
	df.at[i, "Current Date"] = nav_date.strftime("%d-%m-%Y")
	df.at[i, "Current Value"] = round(current_value, 2)
	df.at[i, "% Deviation"] = round(deviation, 2)


