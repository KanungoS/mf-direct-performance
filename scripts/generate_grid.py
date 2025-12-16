# scripts/generate_grid.py

import os
import io
import requests
import pandas as pd
from datetime import datetime

DATA_DIR = "data"

MASTER_LIST_FILE = os.path.join(DATA_DIR, "master_list.csv")
GRID_CSV = os.path.join(DATA_DIR, "mf_direct_grid.csv")
GRID_XLSX = os.path.join(DATA_DIR, "mf_direct_grid.xlsx")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "my_portfolio.csv")

AMFI_NAV_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"


# ------------------------------------------------------------
# Fetch & prepare AMFI NAV data
# ------------------------------------------------------------
def fetch_amfi_nav():
    resp = requests.get(AMFI_NAV_URL, timeout=60)
    resp.raise_for_status()

    raw = resp.text
    lines = raw.splitlines()

    data_lines = []
    for line in lines:
        if ";" in line and line[0].isdigit():
            data_lines.append(line)

    df = pd.read_csv(
        io.StringIO("\n".join(data_lines)),
        sep=";",
        header=None,
        names=[
            "Scheme Code",
            "ISIN Div Payout",
            "ISIN Div Reinvestment",
            "ISIN Growth",
            "Scheme Name",
            "Net Asset Value",
            "Date",
        ],
    )

    df["Scheme Code"] = df["Scheme Code"].astype(str)
    df["Net Asset Value"] = pd.to_numeric(df["Net Asset Value"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")

    # ✅ CRITICAL FIX — normalize column names ONCE, HERE
    df.rename(
        columns={
            "Net Asset Value": "NAV",
            "Date": "NAV Date",
        },
        inplace=True,
    )

    return df


# ------------------------------------------------------------
# Build full MF direct grid (from master_list.csv)
# ------------------------------------------------------------
def build_grid(nav_df):
    master = pd.read_csv(MASTER_LIST_FILE, dtype=str)

    master["Scheme Code"] = master["Scheme Code"].astype(str)

    grid = master.merge(
        nav_df[["Scheme Code", "NAV", "NAV Date"]],
        on="Scheme Code",
        how="left",
    )

    return grid


# ------------------------------------------------------------
# Update portfolio file
# ------------------------------------------------------------
def update_portfolio(nav_df):
    if not os.path.exists(PORTFOLIO_FILE):
        return

    pf = pd.read_csv(PORTFOLIO_FILE, dtype=str)

    pf["Scheme Code"] = pf["Scheme Code"].astype(str)

    nav_map = nav_df[["Scheme Code", "NAV", "NAV Date"]]

    pf = pf.merge(nav_map, on="Scheme Code", how="left")

    pf["NAV"] = pd.to_numeric(pf["NAV"], errors="coerce")
    pf["Units"] = pd.to_numeric(pf["Units"], errors="coerce")

    pf["Current Value"] = pf["NAV"] * pf["Units"]

    pf.to_csv(PORTFOLIO_FILE, index=False)


# ------------------------------------------------------------
# Export helpers
# ------------------------------------------------------------
def export_outputs(grid_df):
    grid_df.to_csv(GRID_CSV, index=False)

    with pd.ExcelWriter(GRID_XLSX, engine="openpyxl") as writer:
        grid_df.to_excel(writer, index=False, sheet_name="mf_direct_grid")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    nav_df = fetch_amfi_nav()

    grid_df = build_grid(nav_df)
    export_outputs(grid_df)

    update_portfolio(nav_df)


if __name__ == "__main__":
    main()
