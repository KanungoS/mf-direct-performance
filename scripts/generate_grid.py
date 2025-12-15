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
GRID_OUTPUT_FILE = f"{DATA_DIR}/mf_direct_grid.xlsx"
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
# Weekend / holiday NAV fallback
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
# Load portfolio
# -----------------------------------------------------------
def load_portfolio():
    return pd.read_csv(PORTFOLIO_FILE)


# -----------------------------------------------------------
# Build NAV grid (only what portfolio needs)
# -----------------------------------------------------------
def build_nav_grid(portfolio_df):
    rows = []

    for _, row in portfolio_df.iterrows():
        code = row["Scheme Code"]
        name = row["Scheme Name"]

        history = load_nav_history(code)
        if history.empty:
            continue

        nav_date, latest_nav = get_latest_available_nav(history)

        rows.append({
            "Scheme Code": code,
            "Scheme Name": name,
            "NAV Date (Effective)": nav_date,
            "Latest NAV": latest_nav
        })

    return pd.DataFrame(rows).drop_duplicates(subset=["Scheme Code"])


# -----------------------------------------------------------
# Save MF Grid (market reference)
# -----------------------------------------------------------
def save_grid_excel(grid_df):
    grid_df.to_excel(GRID_OUTPUT_FILE, index=False)
    print(f"✅ MF Grid saved: {GRID_OUTPUT_FILE}")


# -----------------------------------------------------------
# Save Portfolio (FINAL, CLEAN VERSION)
# -----------------------------------------------------------
def save_portfolio_excel(grid_df, portfolio_df):

    # Aggregate portfolio safely (multiple buys handled)
    pf = (
        portfolio_df
        .groupby(
            [
                "Scheme Code",
                "Scheme Name",
                "Will Exit Load Apply",
                "Exit Load Period",
                "Exit Load %"
            ],
            as_index=False
        )
        .agg({
            "Units": "sum",
            "Purchase NAV": "mean"
        })
    )

    pf["Total Purchase Value"] = pf["Units"] * pf["Purchase NAV"]

    # Merge with latest NAV
    pf = pd.merge(
        pf,
        grid_df,
        on=["Scheme Code", "Scheme Name"],
        how="left"
    )

    # Current metrics
    pf["Current Value"] = pf["Units"] * pf["Latest NAV"]
    pf["% Deviation"] = (
        (pf["Current Value"] - pf["Total Purchase Value"])
        / pf["Total Purchase Value"]
    ) * 100

    # Final column order (EXACTLY as requested)
    pf = pf[[
        "Scheme Code",
        "Scheme Name",
        "Units",
        "Purchase NAV",
        "Total Purchase Value",
        "NAV Date (Effective)",
        "Latest NAV",
        "Current Value",
        "% Deviation",
        "Will Exit Load Apply",
        "Exit Load Period",
        "Exit Load %"
    ]]

    pf.to_excel(PORTFOLIO_OUTPUT_FILE, index=False)
    print(f"✅ Portfolio updated (final): {PORTFOLIO_OUTPUT_FILE}")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def main():
    print("=== Loading Portfolio ===")
    portfolio = load_portfolio()

    if portfolio.empty:
        print("⚠ Portfolio empty. Nothing to process.")
        return

    print("=== Building NAV Grid ===")
    grid = build_nav_grid(portfolio)

    print("=== Saving Outputs ===")
    save_grid_excel(grid)
    save_portfolio_excel(grid, portfolio)

    print("🎉 DONE — Portfolio updated cleanly")


if __name__ == "__main__":
    main()
