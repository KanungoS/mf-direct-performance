import pandas as pd
import requests
from datetime import datetime

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
OUTPUT_FILE = "data/mf_tactical_watchlist.csv"


def fetch_nav():
    r = requests.get(AMFI_URL, timeout=30)
    rows = []
    for line in r.text.splitlines():
        if ";" in line and line.count(";") >= 5:
            rows.append(line.split(";"))

    df = pd.DataFrame(rows, columns=[
        "SchemeCode", "ISIN1", "ISIN2", "SchemeName", "NAV", "NAV_Date"
    ])
    df["SchemeCode"] = df["SchemeCode"].astype(str)
    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")
    df["NAV_Date"] = pd.to_datetime(df["NAV_Date"], errors="coerce")
    return df.dropna(subset=["NAV", "NAV_Date"])


def classify(name):
    n = name.lower()
    if "silver" in n:
        return "Commodity - Silver"
    if "gold" in n:
        return "Commodity - Gold"
    if "international" in n or "overseas" in n:
        return "Equity - International"
    return "ETF / FoF"


def build_tactical():
    df = fetch_nav()
    name = df["SchemeName"].str.lower()

    df = df[name.str.contains("gold|silver|etf|fof|international|overseas")]

    df["Category"] = df["SchemeName"].apply(classify)
    df["Risk_Level"] = "High"
    df["NAV_As_Of_Date"] = df["NAV_Date"]
    df["Valuation_Date"] = datetime.today().date()

    df = df[[
        "SchemeCode",
        "SchemeName",
        "Category",
        "Risk_Level",
        "NAV",
        "NAV_As_Of_Date",
        "Valuation_Date"
    ]]

    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    build_tactical()
