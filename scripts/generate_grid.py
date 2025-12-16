# scripts/generate_grid.py
# FINAL – AMFI FORMAT COMPLIANT, TYPE SAFE, ROBUST

import os
import requests
import pandas as pd
from io import StringIO

DATA_DIR = "data"
MASTER_LIST = f"{DATA_DIR}/master_list.csv"
PORTFOLIO = f"{DATA_DIR}/my_portfolio.csv"
GRID_CSV = f"{DATA_DIR}/mf_direct_grid.csv"
GRID_XLSX = f"{DATA_DIR}/mf_direct_grid.xlsx"

AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"


# -------------------------------------------------
# Fetch & parse AMFI NAV data (official format)
# -------------------------------------------------
def fetch_amfi_nav():
    r = requests.get(AMFI_URL, timeout=60)
    r.raise_for_status()

    rows = []
    for line in r.text.splitlines():
        if line and line[0].isdigit():
            parts = line.split(";")
            if len(parts) == 7:
                rows.append(parts)

    df = pd.DataFrame(
        rows,
        columns=[
            "Scheme Code",
            "ISIN Div Payout",
            "ISIN Growth",
            "ISIN Div Reinvestment",
            "Scheme Name",
            "NAV",
            "NAV Date",
        ],
    )

    df["Scheme Code"] = df["Scheme Code"].astype(str)
    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")
    df["NAV Date"] = pd.to_datetime(
        df["NAV Date"], format="%d-%b-%Y", errors="coerce"
    )

    # Latest NAV per scheme
    df = (
        df.sort_values("NAV Date")
        .groupby("Scheme Code", as_index=False)
        .last()
    )

    return df[["Scheme Code", "Scheme Name", "NAV", "NAV Date"]]


# -------------------------------------------------
# Generate MF Direct Grid
# -------------------------------------------------
def generate_grid(nav_df):
    master = pd.read_csv(MASTER_LIST, dtype={"Scheme Code": str})

    grid = master.merge(nav_df, on="Scheme Code", how="left")

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


# -------------------------------------------------
# Update Portfolio
# -------------------------------------------------
def update_portfolio(nav_df):
    if not os.path.exists(PORTFOLIO):
        return

    pf = pd.read_csv(PORTFOLIO, dtype={"Scheme Code": str})

    pf = pf.merge(
        nav_df[["Scheme Code", "NAV", "NAV Date"]],
        on="Scheme Code",
        how="left",
    )

    pf["Current NAV"] = pf["NAV"]
    pf["Current Date"] = pf["NAV Date"]
    pf["Current Value"] = (pf["Units"] * pf["Current NAV"]).round(2)
    pf["% Deviation"] = (
        ((pf["Current Value"] - pf["Total Purchase"]) / pf["Total Purchase"]) * 100
    ).round(2)

    pf.drop(columns=["NAV", "NAV Date"], inplace=True)
    pf.to_csv(PORTFOLIO, index=False)


# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    nav_df = fetch_amfi_nav()

    grid = generate_grid(nav_df)
    grid.to_csv(GRID_CSV, index=False)
    grid.to_excel(GRID_XLSX, index=False)

    update_portfolio(nav_df)


if __name__ == "__main__":
    main()
