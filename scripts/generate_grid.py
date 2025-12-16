# scripts/generate_grid.py
# PURPOSE:
# 1) Build FULL MF master grid from data/master_list.csv  -> mf_direct_grid.csv / .xlsx
# 2) Update ONLY portfolio rows from data/my_portfolio.csv -> my_portfolio.csv (overwrite)
# 3) Handle per-scheme latest NAV date correctly (no forced global date)
# 4) No duplicate outputs, no cross-contamination, no indentation issues

import os
import sys
import csv
import requests
import pandas as pd
from datetime import datetime
from io import StringIO

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

MASTER_LIST = os.path.join(DATA_DIR, "master_list.csv")
PORTFOLIO = os.path.join(DATA_DIR, "my_portfolio.csv")

GRID_CSV = os.path.join(DATA_DIR, "mf_direct_grid.csv")
GRID_XLSX = os.path.join(DATA_DIR, "mf_direct_grid.xlsx")

AMFI_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?frmdt=&todt=&mf=0"

def fetch_amfi_nav():
    import requests
    import pandas as pd
    from io import StringIO

    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    # AMFI file uses ; delimiter and has header rows
    lines = resp.text.splitlines()

    data = []
    for line in lines:
        if ";" in line and line.count(";") >= 5 and line[0].isdigit():
            data.append(line)

    df = pd.read_csv(
        StringIO("\n".join(data)),
        sep=";",
        header=None,
        names=[
            "Scheme Code",
            "ISIN Div Payout",
            "ISIN Div Reinvestment",
            "Scheme Name",
            "NAV",
            "Date"
        ]
    )

    df["Scheme Code"] = df["Scheme Code"].astype(int)
    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce")

    return df

def build_master_grid(nav_df):
    master = pd.read_csv(MASTER_LIST)
    master["Scheme Code"] = pd.to_numeric(master["Scheme Code"], errors="coerce")
    out = master.merge(nav_df, on="Scheme Code", how="left")

    out.rename(columns={
        "NAV": "NAV Latest",
        "NAV Date": "NAV Date"
    }, inplace=True)

    out.to_csv(GRID_CSV, index=False)
    out.to_excel(GRID_XLSX, index=False)

def update_portfolio(nav_df):
    df = pd.read_csv(PORTFOLIO)
    df["Scheme Code"] = pd.to_numeric(df["Scheme Code"], errors="coerce")

    df = df.merge(
        nav_df[["Scheme Code", "NAV", "NAV Date"]],
        on="Scheme Code",
        how="left"
    )

    df.rename(columns={
        "Date": "NAV Date",
        "Net Asset Value": "NAV"
    }, inplace=True)

    df["Current Value"] = (df["Units"] * df["Current NAV"]).round(2)
    df["% Deviation"] = (
        (df["Current Value"] - df["Total Purchase"]) / df["Total Purchase"] * 100
    ).round(2)

    df["Current Date"] = pd.to_datetime(df["Current Date"]).dt.strftime("%d-%m-%Y")

    df.to_csv(PORTFOLIO, index=False)

def main():
    nav_df = fetch_amfi_nav()
    build_master_grid(nav_df)
    update_portfolio(nav_df)

if __name__ == "__main__":
    main()
