# scripts/generate_grid.py
# FINAL – AMFI FORMAT SAFE + PORTFOLIO SCHEMA LOCKED

import os
import re
import requests
import pandas as pd

DATA_DIR = "data"
MASTER_LIST = f"{DATA_DIR}/master_list.csv"
PORTFOLIO = f"{DATA_DIR}/my_portfolio.csv"
GRID_CSV = f"{DATA_DIR}/mf_direct_grid.csv"
GRID_XLSX = f"{DATA_DIR}/mf_direct_grid.xlsx"

AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"


# -------------------------------------------------
# Fetch & parse AMFI NAV data
# Handles ; and ;-; safely
# -------------------------------------------------
def fetch_amfi_nav():
    r = requests.get(AMFI_URL, timeout=60)
    r.raise_for_status()

    rows = []

    for raw_line in r.text.splitlines():
        if not raw_line or not raw_line[0].isdigit():
            continue

        # Normalize AMFI edge separator
        line = re.sub(r";-;", ";", raw_line)
        parts = line.split(";")

        if len(parts) < 6:
            continue

        rows.append([
            parts[0].strip(),  # Scheme Code
            parts[3].strip(),  # Scheme Name
            parts[4].strip(),  # NAV
            parts[5].strip(),  # Date
        ])

    if not rows:
        raise RuntimeError("AMFI NAV data parsed as empty")

    df = pd.DataFrame(
        rows,
        columns=["Scheme Code", "Scheme Name", "NAV", "NAV Date"]
    )

    df["Scheme Code"] = df["Scheme Code"].astype(str)
    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")
    df["NAV Date"] = pd.to_datetime(
        df["NAV Date"], format="%d-%b-%Y", errors="coerce"
    )

    return (
        df.sort_values("NAV Date")
          .groupby("Scheme Code", as_index=False)
          .last()
    )


# -------------------------------------------------
# Generate MF Direct Grid
# -------------------------------------------------
def generate_grid(nav_df):
    master = pd.read_csv(MASTER_LIST, dtype={"Scheme Code": str})

    grid = master.merge(
        nav_df[["Scheme Code", "NAV", "NAV Date"]],
        on="Scheme Code",
        how="left"
    )

    required_cols = [
        "Scheme Code",
        "Scheme Name",
        "Scheme Category",
        "Scheme Status",
        "NAV",
        "NAV Date",
    ]

    for col in required_cols:
        if col not in grid.columns:
            grid[col] = pd.NA

    return grid[required_cols]


# -------------------------------------------------
# Update Portfolio (EXACT HEADER MATCH)
# -------------------------------------------------
def update_portfolio(nav_df):
    if not os.path.exists(PORTFOLIO):
        return

    pf = pd.read_csv(PORTFOLIO, dtype={"Scheme Code": str})

    pf = pf.merge(
        nav_df[["Scheme Code", "NAV", "NAV Date"]],
        on="Scheme Code",
        how="left"
    )

    # Exact columns from your file
    pf["Current NAV"] = pf["NAV"]
    pf["Current Date"] = pf["NAV Date"]
    pf["Current Value"] = (pf["Units"] * pf["Current NAV"]).round(2)

    pf["% Deviation"] = (
        (pf["Current Value"] - pf["Total Purchase Value"])
        / pf["Total Purchase Value"] * 100
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
