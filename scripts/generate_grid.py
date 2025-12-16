# =========================================================
# FINAL UNIFIED MF GRID + PORTFOLIO ENGINE (PRODUCTION)
# Source: mfapi.in
# =========================================================

import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# ---------------- PATHS ----------------
DATA_DIR = "data"
MASTER_LIST = f"{DATA_DIR}/master_list.csv"
PORTFOLIO = f"{DATA_DIR}/my_portfolio.csv"
GRID_CSV = f"{DATA_DIR}/mf_direct_grid.csv"
GRID_XLSX = f"{DATA_DIR}/mf_direct_grid.xlsx"

MFAPI_URL = "https://api.mfapi.in/mf/{}"

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------- HELPERS ----------------
def pct_return(latest, past):
    if pd.isna(past) or past == 0:
        return None
    return round((latest - past) / past * 100, 4)

def get_nav_on_or_before(df, target_date):
    d = df[df["date"] <= target_date]
    return d.iloc[-1]["nav"] if not d.empty else None

# ---------------- FETCH MFAPI DATA ----------------
def fetch_mfapi_data(code):
    r = requests.get(MFAPI_URL.format(code), timeout=60)
    r.raise_for_status()
    js = r.json()

    nav_df = pd.DataFrame(js["data"])
    nav_df["date"] = pd.to_datetime(nav_df["date"], format="%d-%m-%Y")
    nav_df["nav"] = pd.to_numeric(nav_df["nav"], errors="coerce")
    nav_df = nav_df.sort_values("date")

    return js["meta"], nav_df

# ---------------- BUILD MF DIRECT GRID ----------------
def build_direct_grid(master):
    rows = []

    today = datetime.today()

    for _, row in master.iterrows():
        code = str(row["Scheme Code"])
        scheme_name_master = row["Scheme Name"]
        status = row["Scheme Status"]

        try:
            meta, nav_df = fetch_mfapi_data(code)
        except Exception:
            continue

        latest_nav = nav_df.iloc[-1]["nav"]
        latest_date = nav_df.iloc[-1]["date"]

        nav_1d = get_nav_on_or_before(nav_df, today - timedelta(days=1))
        nav_1w = get_nav_on_or_before(nav_df, today - timedelta(days=7))
        nav_1m = get_nav_on_or_before(nav_df, today - timedelta(days=30))
        nav_3m = get_nav_on_or_before(nav_df, today - timedelta(days=90))
        nav_6m = get_nav_on_or_before(nav_df, today - timedelta(days=180))
        nav_1y = get_nav_on_or_before(nav_df, today - timedelta(days=365))

        r1d = pct_return(latest_nav, nav_1d)
        r1w = pct_return(latest_nav, nav_1w)
        r1m = pct_return(latest_nav, nav_1m)
        r3m = pct_return(latest_nav, nav_3m)
        r6m = pct_return(latest_nav, nav_6m)
        r1y = pct_return(latest_nav, nav_1y)

        rows.append({
            "AMC": meta.get("fund_house"),
            "Scheme Code": code,
            "Scheme Name": scheme_name_master,
            "Scheme Category": meta.get("scheme_category"),
            "Sector Theme": meta.get("scheme_category"),
            "Scheme Status": status,
            "Name Changed (Yes/No)": "Yes" if meta.get("scheme_name") != scheme_name_master else "No",
            "NAV Latest": latest_nav,
            "NAV 1D": nav_1d,
            "NAV 1W": nav_1w,
            "NAV 1M": nav_1m,
            "NAV 3M": nav_3m,
            "NAV 6M": nav_6m,
            "NAV 1Y": nav_1y,
            "%Return 1D": r1d,
            "%Return 1W": r1w,
            "%Return 1M": r1m,
            "%Return 3M": r3m,
            "%Return 6M": r6m,
            "%Return 1Y": r1y,
        })

    df = pd.DataFrame(rows)

    # -------- CATEGORY METRICS --------
    df["Category Size"] = df.groupby("Scheme Category")["Scheme Code"].transform("count")
    df["Category Avg Return (1Y)"] = df.groupby("Scheme Category")["%Return 1Y"].transform("mean")
    df["Category Rank (1Y)"] = df.groupby("Scheme Category")["%Return 1Y"].rank(ascending=False, method="dense")
    df["Quartile (1Y)"] = pd.qcut(df["Category Rank (1Y)"], 4, labels=["Top", "Second", "Third", "Bottom"])

    df["Performance Tag (1Y)"] = df["Quartile (1Y)"].map({
        "Top": "Outperformer",
        "Second": "Above Average",
        "Third": "Below Average",
        "Bottom": "Underperformer"
    })

    df["Category Return Deviation (1Y)"] = df["%Return 1Y"] - df["Category Avg Return (1Y)"]

    # -------- SECTOR METRICS --------
    df["Sector Avg Return (1Y)"] = df.groupby("Sector Theme")["%Return 1Y"].transform("mean")
    df["Sector Rank (1Y)"] = df.groupby("Sector Theme")["%Return 1Y"].rank(ascending=False, method="dense")
    df["Sector Quartile (1Y)"] = pd.qcut(df["Sector Rank (1Y)"], 4, labels=["Top", "Second", "Third", "Bottom"])
    df["Sector Performance Tag (1Y)"] = df["Sector Quartile (1Y)"].map({
        "Top": "Sector Leader",
        "Second": "Above Sector Avg",
        "Third": "Below Sector Avg",
        "Bottom": "Sector Laggard"
    })
    df["Sector Return Deviation (1Y)"] = df["%Return 1Y"] - df["Sector Avg Return (1Y)"]

    return df

# ---------------- UPDATE PORTFOLIO ----------------
def update_portfolio(master):
    if not os.path.exists(PORTFOLIO):
        return

    pf = pd.read_csv(PORTFOLIO, dtype={"Scheme Code": str})

    nav_map = {}

    for code in pf["Scheme Code"].astype(str):
        try:
            _, nav_df = fetch_mfapi_data(code)
            nav_map[code] = nav_df.iloc[-1]
        except Exception:
            continue

    pf["Current NAV"] = pf["Scheme Code"].map(lambda x: nav_map.get(str(x), {}).get("nav"))
    pf["Current Date"] = pf["Scheme Code"].map(lambda x: nav_map.get(str(x), {}).get("date"))
    pf["Current Value"] = (pf["Units"] * pf["Current NAV"]).round(2)
    pf["% Deviation"] = ((pf["Current Value"] - pf["Total Purchase Value"]) /
                          pf["Total Purchase Value"] * 100).round(2)

    pf.to_csv(PORTFOLIO, index=False)

# ---------------- MAIN ----------------
def main():
    master = pd.read_csv(MASTER_LIST, dtype={"Scheme Code": str})
    grid = build_direct_grid(master)

    grid.to_csv(GRID_CSV, index=False)
    grid.to_excel(GRID_XLSX, index=False)

    update_portfolio(master)

if __name__ == "__main__":
    main()
