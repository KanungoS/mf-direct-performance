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
    r = requests.get(AMFI_URL, timeout=60)
    r.raise_for_status()
    lines = r.text.splitlines()
    rows = []
    for line in lines:
        if ";" in line and line[:1].isdigit():
            parts = line.split(";")
            if len(parts) >= 6:
                rows.append({
                    "Scheme Code": parts[0].strip(),
                    "Scheme Name": parts[3].strip(),
                    "NAV": parts[4].strip(),
                    "NAV Date": parts[5].strip()
                })
    df = pd.DataFrame(rows)
    df["Scheme Code"] = pd.to_numeric(df["Scheme Code"], errors="coerce")
    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")
    df["NAV Date"] = pd.to_datetime(df["NAV Date"], errors="coerce", dayfirst=True)
    df = df.dropna(subset=["Scheme Code", "NAV", "NAV Date"])
    df = df.sort_values(["Scheme Code", "NAV Date"]).groupby("Scheme Code").tail(1)
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
        "NAV": "Current NAV",
        "NAV Date": "Current Date"
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
