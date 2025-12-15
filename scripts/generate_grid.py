#!/usr/bin/env python3
import pandas as pd
import requests
import datetime as dt

PORTFOLIO_FILE = "data/my_portfolio.csv"
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"


# -------------------------------------------------
# Load AMFI NAV master (authoritative)
# -------------------------------------------------
def load_amfi_nav():
    r = requests.get(AMFI_URL, timeout=20)
    r.raise_for_status()

    lines = r.text.splitlines()

    records = []
    for line in lines:
        if ";" in line and line.count(";") >= 5:
            parts = line.split(";")
            try:
                records.append({
                    "Scheme Code": int(parts[0]),
                    "NAV": float(parts[4]),
                    "NAV Date": pd.to_datetime(parts[5], dayfirst=True).date()
                })
            except:
                continue

    df = pd.DataFrame(records)
    return df.set_index("Scheme Code")


# -------------------------------------------------
# MAIN
# -------------------------------------------------
def main():
    portfolio = pd.read_csv(PORTFOLIO_FILE)

    portfolio["Units"] = pd.to_numeric(portfolio["Units"], errors="coerce")
    portfolio["Total Purchase Value"] = pd.to_numeric(
        portfolio["Total Purchase Value"], errors="coerce"
    )

    nav_master = load_amfi_nav()

    current_nav = []
    nav_dates = []
    current_values = []
    deviations = []

    for _, row in portfolio.iterrows():
        code = int(row["Scheme Code"])

        if code in nav_master.index:
            nav = nav_master.loc[code, "NAV"]
            nav_date = nav_master.loc[code, "NAV Date"]
            value = row["Units"] * nav
            deviation = ((value - row["Total Purchase Value"])
                         / row["Total Purchase Value"]) * 100

            current_nav.append(round(nav, 4))
            nav_dates.append(nav_date)
            current_values.append(round(value, 2))
            deviations.append(round(deviation, 2))
        else:
            current_nav.append("")
            nav_dates.append("")
            current_values.append("")
            deviations.append("")

    # Update ONLY required columns
    portfolio["Current NAV"] = current_nav
    portfolio["Current Date"] = nav_dates
    portfolio["Current Value"] = current_values
    portfolio["% Deviation"] = deviations

    portfolio.to_csv(PORTFOLIO_FILE, index=False)
    print("✅ Portfolio updated using AMFI official NAV (latest available)")


if __name__ == "__main__":
    main()
