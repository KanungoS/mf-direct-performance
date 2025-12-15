#!/usr/bin/env python3

import pandas as pd
import numpy as np
import requests
import datetime as dt

# -----------------------------------------------------------
# File paths
# -----------------------------------------------------------
DATA_DIR = "data"
PORTFOLIO_FILE = f"{DATA_DIR}/my_portfolio.csv"
PORTFOLIO_OUTPUT_FILE = f"{DATA_DIR}/my_portfolio_updated.xlsx"


# -----------------------------------------------------------
# Load Mutual Fund NAV history (MFAPI)
# -----------------------------------------------------------
def load_nav_history(code):
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return pd.DataFrame(columns=["date", "nav"])

        data = r.json()
        if "data" not in data or not data["data"]:
            return pd.DataFrame(columns=["date", "nav"])

        df = pd.DataFrame(data["data"])
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
        df = df.dropna(subset=["date", "nav"]).sort_values("date")

        return df[["date", "nav"]]

    except Exception:
        return pd.DataFrame(columns=["date", "nav"])


# -----------------------------------------------------------
# Weekend / holiday safe NAV
# -----------------------------------------------------------
def get_latest_available_nav(history):
    if history.empty:
        return None, np.nan

    today = dt.datetime.today()
    eligible = history[history["date"] <= today]

    if eligible.empty:
        return None, np.nan

    row = eligible.iloc[-1]
    return row["date"].date(), row["nav"]


# -----------------------------------------------------------
# Load portfolio (no assumptions, no modification)
# -----------------------------------------------------------
def load_portfolio():
    return pd.read_csv(PORTFOLIO_FILE)


# -----------------------------------------------------------
# Update portfolio row-by-row (multi-level exit load safe)
# -----------------------------------------------------------
def update_portfolio(portfolio_df):

    current_navs = []
    current_dates = []
    deviations = []

    for _, row in portfolio_df.iterrows():
        scheme_code = row["Scheme Code"]
        units = row["Units"]
        total_purchase_value = row["Total Purchase Value"]

        history = load_nav_history(scheme_code)
        nav_date, latest_nav = get_latest_available_nav(history)

        if latest_nav is not None and not np.isnan(latest_nav):
            current_value = units * latest_nav
            deviation = ((current_value - total_purchase_value)
                         / total_purchase_value) * 100
        else:
            deviation = np.nan

        current_navs.append(latest_nav)
        current_dates.append(nav_date)
        deviations.append(deviation)

    portfolio_df["Current NAV"] = current_navs
    portfolio_df["Current Date"] = current_dates
    portfolio_df["% Deviation"] = deviations

    return portfolio_df


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def main():
    print("=== Loading Portfolio ===")
    portfolio = load_portfolio()

    if portfolio.empty:
        print("⚠ Portfolio empty. Nothing to process.")
        return

    print("=== Updating Portfolio with Latest NAV ===")
    portfolio = update_portfolio(portfolio)

    portfolio.to_excel(PORTFOLIO_OUTPUT_FILE, index=False)
    print(f"✅ Portfolio updated successfully: {PORTFOLIO_OUTPUT_FILE}")

    print("🎉 DONE — Portfolio update complete")


if __name__ == "__main__":
    main()
