# scripts/generate_grid.py
# FINAL – AMFI FORMAT COMPLIANT, TYPE SAFE, GITHUB-ACTIONS SAFE

import os
import requests
import pandas as pd

DATA_DIR = "data"
MASTER_LIST = os.path.join(DATA_DIR, "master_list.csv")
PORTFOLIO = os.path.join(DATA_DIR, "my_portfolio.csv")
GRID_CSV = os.path.join(DATA_DIR, "mf_direct_grid.csv")
GRID_XLSX = os.path.join(DATA_DIR, "mf_direct_grid.xlsx")

AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "text/plain",
}


# -------------------------------------------------
# Fetch & parse AMFI NAV data (official format)
# -------------------------------------------------
def fetch_amfi_nav():
    resp = requests.get(AMFI_URL, headers=HEADERS, timeout=60)
    resp.raise_for_status()

    records = []

    for line in resp.text.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue

        parts = line.split(";")
        if len(parts) != 7:
            continue

        scheme_code, _, _, _, scheme_name, nav, nav_date = parts

        records.append(
            {
                "Scheme Code": scheme_code.strip(),
                "Scheme Name": scheme_name.strip(),
                "NAV": pd.to_numeric(nav, errors="coerce"),
                "NAV Date": pd.to_datetime(
                    nav_date, format="%d-%b-%Y", errors="coerce"
                ),
            }
        )

    if not records:
        raise RuntimeError("AMFI NAV data parsed as empty")

    df = pd.DataFrame(records)
    df["Scheme Code"] = df["Scheme Code"].astype(str)

    df = (
        df.sort_values("NAV Date")
        .groupby("Scheme Code", as_index=False)
        .last()
    )

    return df


# -------------------------------------------------
# Generate MF Direct Grid
# -------------------------------------------------
def generate_grid(nav_df):
    master = pd.read_csv(
        MASTER_LIST,
        dtype={"Scheme Code": str},
        usecols=["Scheme Code", "Scheme Name", "Scheme Category", "Scheme Status"],
    )

    grid = master.merge(nav_df, on="Scheme Code", how="left")

    return grid[
        [
            "Scheme Code",
            "Scheme Name",
            "Scheme Category",
            "Scheme Status",
            "NAV",
            "NAV Date",
        ]
    ]


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

    pf["Current Value"] = (
        pf["Units"].astype(float) * pf["Current NAV"].astype(float)
    ).round(2)

    pf["% Deviation"] = (
        (pf["Current Value"] - pf["Total Purchase"])
        / pf["Total Purchase"]
        * 100
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
