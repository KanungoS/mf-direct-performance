#!/usr/bin/env python3

import pandas as pd
import numpy as np
import requests
import datetime as dt
import os

# -----------------------------------------------------------
# File paths
# -----------------------------------------------------------
DATA_DIR = "data"

MASTER_FILE = f"{DATA_DIR}/master_fund_list.csv"
PORTFOLIO_FILE = f"{DATA_DIR}/my_portfolio.csv"

GRID_OUTPUT_FILE = f"{DATA_DIR}/mf_direct_grid.xlsx"
PORTFOLIO_OUTPUT_FILE = f"{DATA_DIR}/my_portfolio_updated.xlsx"


# -----------------------------------------------------------
# Load Mutual Fund NAV history from MFAPI
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
# Weekend / Holiday NAV fallback
# -----------------------------------------------------------
def get_latest_available_nav(history, target_date=None):
    if history.empty:
        return None, np.nan

    if target_date is None:
        target_date = dt.datetime.today()

    eligible = history[history["date"] <= target_date]
    if eligible.empty:
        return None, np.nan

    row = eligible.iloc[-1]
    return row["date"], row["nav"]


# -----------------------------------------------------------
# Load master & portfolio
# -----------------------------------------------------------
def load_master():
    try:
        return pd.read_csv(MASTER_FILE).drop_duplicates(subset=["Scheme Code"])
    except Exception:
        return pd.DataFrame(columns=["Scheme Code", "Scheme Name"])


def load_portfolio():
    try:
        return pd.read_csv(PORTFOLIO_FILE)
    except Exception:
        return pd.DataFrame(columns=["Scheme Code", "Scheme Name", "Units", "Purchase NAV"])


# -----------------------------------------------------------
# Compute returns
# -----------------------------------------------------------
def compute_returns(history):
    if history.empty or len(history) < 5:
        return {
            "1W": np.nan, "1M": np.nan, "3M": np.nan,
            "6M": np.nan, "1Y": np.nan, "3Y": np.nan, "5Y": np.nan
        }

    history = history.sort_values("date")
    latest_nav = history["nav"].iloc[-1]
    latest_date = history["date"].iloc[-1]

    def calc(days):
        cutoff = latest_date - dt.timedelta(days=days)
        past = history[history["date"] <= cutoff]
        if past.empty:
            return np.nan
        old_nav = past["nav"].iloc[-1]
        return ((latest_nav - old_nav) / old_nav) * 100

    return {
        "1W": calc(7),
        "1M": calc(30),
        "3M": calc(90),
        "6M": calc(180),
        "1Y": calc(365),
        "3Y": calc(1095),
        "5Y": calc(1825)
    }


# -----------------------------------------------------------
# Build MF Grid (market data for portfolio schemes)
# -----------------------------------------------------------
def build_grid(portfolio):
    rows = []

    for _, row in portfolio.iterrows():
        code = row["Scheme Code"]
        name = row["Scheme Name"]

        history = load_nav_history(code)
        if history.empty:
            continue

        nav_date, latest_nav = get_latest_available_nav(history)
        returns = compute_returns(history)

        rows.append({
            "Scheme Code": code,
            "Scheme Name": name,
            "NAV Date (Effective)": nav_date.date() if nav_date is not None else None,
            "Latest NAV": latest_nav,
            **returns
        })

    return pd.DataFrame(rows)


# -----------------------------------------------------------
# Save MF Grid
# -----------------------------------------------------------
def save_grid_excel(grid_df):
    grid_df.to_excel(GRID_OUTPUT_FILE, index=False)
    print(f"✅ MF Grid saved: {GRID_OUTPUT_FILE}")


# -----------------------------------------------------------
# Save Portfolio Update (SEPARATE FILE – FOOL-PROOF)
# -----------------------------------------------------------
def save_portfolio_excel(grid_df, portfolio_df):
    pf = pd.merge(
        portfolio_df,
        grid_df,
        on=["Scheme Code", "Scheme Name"],
        how="left"
    )

    pf["Total Purchase Value"] = pf["Units"] * pf["Purchase NAV"]
    pf["Current Value"] = pf["Units"] * pf["Latest NAV"]
    pf["% Deviation"] = (
        (pf["Current Value"] - pf["Total Purchase Value"])
        / pf["Total Purchase Value"]
    ) * 100

    pf.to_excel(PORTFOLIO_OUTPUT_FILE, index=False)
    print(f"✅ Portfolio updated: {PORTFOLIO_OUTPUT_FILE}")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def main():
    print("=== Loading Portfolio ===")
    portfolio = load_portfolio()

    if portfolio.empty:
        print("⚠ Portfolio empty. Nothing to process.")
        return

    print("=== Building MF Grid ===")
    grid = build_grid(portfolio)

    print("=== Saving Outputs ===")
    save_grid_excel(grid)
    save_portfolio_excel(grid, portfolio)

    print("🎉 DONE — Grid + Portfolio update complete")


if __name__ == "__main__":
    main()
