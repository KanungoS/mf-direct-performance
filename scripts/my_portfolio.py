import pandas as pd
import requests
from datetime import datetime

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

PORTFOLIO_INPUT = "data/my_portfolio_input.csv"
OUTPUT_FILE = "data/my_portfolio.csv"


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
    return df[["SchemeCode", "NAV", "NAV_Date"]].dropna()


def build_portfolio():
    pf = pd.read_csv(PORTFOLIO_INPUT)
    pf["SchemeCode"] = pf["SchemeCode"].astype(str)

    nav = fetch_nav()
    df = pf.merge(nav, on="SchemeCode", how="left")

    df["Current_Value"] = df["Units"] * df["NAV"]
    df["Deviation_%"] = round(
        (df["Current_Value"] - df["Total_Purchase_Value"])
        / df["Total_Purchase_Value"] * 100, 2
    )

    df["NAV_As_Of_Date"] = df["NAV_Date"]
    df["Valuation_Date"] = datetime.today().date()

    df.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    build_portfolio()
