import pandas as pd
import requests
from datetime import datetime

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

MASTER_FILE = "data/master_list.csv"
NAV_HISTORY_FILE = "data/nav_history.csv"
OUTPUT_FILE = "data/mf_core_direct_openended.csv"


def fetch_latest_nav():
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
    return df[["SchemeCode", "NAV", "NAV_Date"]].dropna()


def classify_category(name):
    n = name.lower()
    if "bank" in n or "psu" in n or "financial" in n:
        return "Equity - Sectoral (Banking)"
    if "large cap" in n or "bluechip" in n:
        return "Equity - Large Cap"
    if "flexi" in n:
        return "Equity - Flexi Cap"
    if "focused" in n:
        return "Equity - Focused"
    if "balanced advantage" in n:
        return "Hybrid - Balanced Advantage"
    if "equity & debt" in n or "aggressive hybrid" in n:
        return "Hybrid - Aggressive Hybrid"
    if "debt" in n or "bond" in n:
        return "Debt"
    if "elss" in n or "tax saver" in n:
        return "Solution Oriented - Equity"
    return "Equity - Diversified"


def risk_meter(cat):
    if "Sectoral" in cat or "Focused" in cat:
        return "Very High"
    if cat.startswith("Equity"):
        return "High"
    if cat.startswith("Hybrid"):
        return "Moderate"
    return "Low"


def build_core():
    master = pd.read_csv(MASTER_FILE)
    master["SchemeCode"] = master["Scheme Code"].astype(str)
    master["SchemeName"] = master["Scheme Name"]

    # Hard exclusions
    name = master["SchemeName"].str.lower()
    master = master[
        ~name.str.contains("etf|fof|close|interval|idf|fmp")
    ]

    nav = fetch_latest_nav()
    df = master.merge(nav, on="SchemeCode", how="left")

    df = df.dropna(subset=["NAV", "NAV_Date"])

    df["Scheme_Category"] = df["SchemeName"].apply(classify_category)
    df["Risk_Level"] = df["Scheme_Category"].apply(risk_meter)
    df["NAV_As_Of_Date"] = df["NAV_Date"]
    df["Valuation_Date"] = datetime.today().date()

    df = df[[
        "SchemeCode",
        "SchemeName",
        "Scheme_Category",
        "Risk_Level",
        "NAV",
        "NAV_As_Of_Date",
        "Valuation_Date"
    ]]

    df.sort_values(["Scheme_Category", "SchemeName"], inplace=True)
    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    build_core()
