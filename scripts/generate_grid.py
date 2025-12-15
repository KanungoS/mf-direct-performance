#!/usr/bin/env python3
import pandas as pd
import numpy as np
import requests
import datetime as dt

PORTFOLIO_FILE = "data/my_portfolio.csv"


# ------------------------------
# NAV Loader (weekend safe)
# ------------------------------
def load_latest_nav(scheme_code):
    url = f"https://api.mfapi.in/mf/{int(scheme_code)}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()

    data = r.json()["data"]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna().sort_values("date")

    latest = df.iloc[-1]
    return latest["nav"], latest["date"].date()


# ------------------------------
# MAIN
# ------------------------------
def main():
    df = pd.read_csv(PORTFOLIO_FILE)

    # Ensure numeric safety
    df["Units"] = pd.to_numeric(df["Units"], errors="coerce")
    df["Total Purchase Value"] = pd.to_numeric(df["Total Purchase Value"], errors="coerce")

    current_nav_list = []
    nav_date_list = []
    current_value_list = []
    deviation_list = []

    for _, row in df.iterrows():
        try:
            nav, nav_date = load_latest_nav(row["Scheme Code"])
            current_value = row["Units"] * nav
            deviation = ((current_value - row["Total Purchase Value"])
                         / row["Total Purchase Value"]) * 100

            current_nav_list.append(round(nav, 4))
            nav_date_list.append(nav_date)
            current_value_list.append(round(current_value, 2))
            deviation_list.append(round(deviation, 2))

        except Exception as e:
            current_nav_list.append(np.nan)
            nav_date_list.append("")
            current_value_list.append(np.nan)
            deviation_list.append(np.nan)

    # Write back ONLY required columns
    df["Current NAV"] = current_nav_list
    df["Current Date"] = nav_date_list
    df["Current Value"] = current_value_list
    df["% Deviation"] = deviation_list

    df.to_csv(PORTFOLIO_FILE, index=False)
    print("✅ Portfolio updated successfully")


if __name__ == "__main__":
    main()
