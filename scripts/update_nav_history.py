import pandas as pd
import requests
import os

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
NAV_HISTORY_FILE = "nav_history.csv"

def fetch_amfi_nav():
    r = requests.get(AMFI_URL, timeout=30)
    rows = []
    for line in r.text.splitlines():
        if ";" in line and line.count(";") >= 5:
            rows.append(line.split(";"))

    df = pd.DataFrame(rows, columns=[
        "SchemeCode", "ISIN1", "ISIN2",
        "SchemeName", "NAV", "NAV_Date"
    ])

    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")
    df["NAV_Date"] = pd.to_datetime(df["NAV_Date"], errors="coerce")

    return df.dropna(subset=["SchemeCode", "NAV", "NAV_Date"])[
        ["SchemeCode", "NAV", "NAV_Date"]
    ]

def update_nav_history():
    today_nav = fetch_amfi_nav()

    if os.path.exists(NAV_HISTORY_FILE):
        hist = pd.read_csv(NAV_HISTORY_FILE, parse_dates=["NAV_Date"])
        combined = pd.concat([hist, today_nav], ignore_index=True)
        combined.drop_duplicates(
            subset=["SchemeCode", "NAV_Date"],
            keep="last",
            inplace=True
        )
    else:
        combined = today_nav

    combined.sort_values(["SchemeCode", "NAV_Date"], inplace=True)
    combined.to_csv(NAV_HISTORY_FILE, index=False)

if __name__ == "__main__":
    update_nav_history()
