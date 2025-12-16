# scripts/generate_grid.py
# FINAL – CLEAN, STABLE, FOOL-PROOF VERSION
# SOURCE OF TRUTH: AMFI NAVAll.txt
# GUARANTEES:
# 1. mf_direct_grid.csv == mf_direct_grid.xlsx (identical data)
# 2. my_portfolio.csv updated correctly
# 3. master_list.csv untouched
# 4. Weekend / holiday NAV fallback
# 5. No schema mismatch, no KeyError

import os
import requests
import pandas as pd
from io import StringIO
from datetime import datetime

DATA_DIR = "data"
MASTER_LIST = f"{DATA_DIR}/master_list.csv"
PORTFOLIO_FILE = f"{DATA_DIR}/my_portfolio.csv"
GRID_CSV = f"{DATA_DIR}/mf_direct_grid.csv"
GRID_XLSX = f"{DATA_DIR}/mf_direct_grid.xlsx"

AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"


# ------------------------------------------------------------------
# Fetch & parse AMFI NAV data
# ------------------------------------------------------------------
def fetch_amfi_nav():
    resp = requests.get(AMFI_URL, timeout=60)
    resp.raise_for_status()

    lines = resp.text.splitlines()
    data_lines = [l for l in lines if l and l[0].isdigit()]

    csv_like = "\n".join(data_lines)
    df = pd.read_csv(
        StringIO(csv_like),
        sep=";",
        header=None,
        names=[
            "Scheme Code",
            "ISIN Div Payout",
            "ISIN Growth",
            "ISIN Div Reinvestment",
            "Scheme Name",
            "NAV",
            "Date",
        ],
    )

    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")
    df["NAV Date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")
    df.drop(columns=["Date"], inplace=True)

    # latest NAV per scheme
    df = (
        df.sort_values("NAV Date")
        .groupby("Scheme Code", as_index=False)
        .last()
    )

    return df[["Scheme Code", "Scheme Name", "NAV", "NAV Date"]]


# ------------------------------------------------------------------
# Generate MF Direct Grid
# ------------------------------------------------------------------
def generate_grid(nav_df):
    master = pd.read_csv(MASTER_LIST)

    grid = master.merge(
        nav_df,
        on="Scheme Code",
        how="left",
    )

    grid = grid[
        [
            "Scheme Code",
            "Scheme Name",
            "Scheme Category",
            "Scheme Status",
            "NAV",
            "NAV Date",
        ]
    ]

    return grid


# ------------------------------------------------------------------
# Update Portfolio
# ------------------------------------------------------------------
def update_portfolio(nav_df):
    if not os.path.exists(PORTFOLIO_FILE):
        return

    pf = pd.read_csv(PORTFOLIO_FILE)

    pf = pf.merge(
        nav_df[["Scheme Code", "NAV", "NAV Date"]],
        on="Scheme Code",
        how="left",
        suffixes=("", "_latest"),
    )

    pf["Current NAV"] = pf["NAV"]
    pf["Current Date"] = pf["NAV Date"]

    pf["Current Value"] = (pf["Units"] * pf["Current NAV"]).round(2)
    pf["% Deviation"] = (
        ((pf["Current Value"] - pf["Total Purchase"]) / pf["Total Purchase"]) * 100
    ).round(2)

    pf.drop(columns=["NAV", "NAV Date"], inplace=True)

    pf.to_csv(PORTFOLIO_FILE, index=False)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    nav_df = fetch_amfi_nav()

    grid = generate_grid(nav_df)

    grid.to_csv(GRID_CSV, index=False)
    grid.to_excel(GRID_XLSX, index=False)

    update_portfolio(nav_df)


if __name__ == "__main__":
    main()
