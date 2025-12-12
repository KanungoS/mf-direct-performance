# ============================================================
#   MUTUAL FUND PERFORMANCE ENGINE (FINAL FULL VERSION)
#   Includes:
#   - NAV Processing
#   - Returns (1D, 1W, 1M, 3M, 6M, 1Y, 3Y)
#   - Rolling Returns (1Y, 3Y)
#   - StdDev Volatility
#   - Max Drawdown
#   - Peer Ranking (Category & Sector)
#   - AI Fund Score (Option A – Aggressive Momentum)
#   - Risk Score
#   - Exit Load Logic
#   - Excel export + Dashboard + Top 10 lists
# ============================================================

import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime, timedelta
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils.dataframe import dataframe_to_rows

DATA_DIR = "data"
CACHE_DIR = f"{DATA_DIR}/cache"
MASTER_CSV = f"{DATA_DIR}/master_list.csv"
DISCONTINUED_CSV = f"{DATA_DIR}/discontinued_schemes.csv"
FINAL_CSV = f"{DATA_DIR}/mf_direct_grid.csv"
FINAL_XLSX = f"{DATA_DIR}/mf_direct_grid.xlsx"

# ============================================================
#   UTILITIES
# ============================================================

def load_master_list():
    return pd.read_csv(MASTER_CSV)

def save_master_list(df):
    df.to_csv(MASTER_CSV, index=False)

def load_discontinued():
    return pd.read_csv(DISCONTINUED_CSV)

def save_discontinued(df):
    df.to_csv(DISCONTINUED_CSV, index=False)

def fetch_direct_scheme_list():
    url = "https://api.mfapi.in/mf"
    data = requests.get(url).json()
    return [x for x in data if "Direct" in x["schemeName"]]

def load_nav_history(code):
    cache_file = f"{CACHE_DIR}/{code}.json"
    url = f"https://api.mfapi.in/mf/{code}"

    if os.path.exists(cache_file):
        js = pd.read_json(cache_file)
    else:
        js = requests.get(url).json()
        pd.DataFrame(js).to_json(cache_file)

    df = pd.DataFrame(js["data"])
    df["nav"] = df["nav"].astype(float)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    return df, js

def normalize_category(cat):
    if "Equity" in cat: return "Equity"
    if "Debt" in cat: return "Debt"
    if "Hybrid" in cat: return "Hybrid"
    if "Index" in cat: return "Index"
    return cat

def detect_sector_theme(name):
    sectors = ["IT", "Pharma", "Infra", "Banking", "Consumption", "Energy"]
    for s in sectors:
        if s.lower() in name.lower():
            return s
    return "Diversified"

# ============================================================
#   RETURN CALCULATIONS
# ============================================================

def compute_returns(df):
    d = {}

    try:
        latest = df.iloc[-1]["nav"]
    except:
        return {}

    def pct(days):
        try:
            past = df.iloc[-days]["nav"]
            return round((latest - past) * 100 / past, 4)
        except:
            return None

    d["NAV Latest"] = latest
    d["NAV 1D"] = pct(1)
    d["NAV 1W"] = pct(7)
    d["NAV 1M"] = pct(30)
    d["NAV 3M"] = pct(90)
    d["NAV 6M"] = pct(180)
    d["NAV 1Y"] = pct(365)
    d["NAV 3Y"] = pct(365 * 3)

    # StdDev volatility
    d["Volatility (StdDev 1Y)"] = df.tail(365)["nav"].pct_change().std()

    # Max Drawdown
    roll_max = df["nav"].cummax()
    drawdown = (df["nav"] - roll_max) / roll_max
    d["Max Drawdown"] = drawdown.min()

    # Rolling returns
    try:
        d["Rolling Return 1Y"] = (
            df["nav"].pct_change(365).dropna().mean()
        )
        d["Rolling Return 3Y"] = (
            df["nav"].pct_change(365 * 3).dropna().mean()
        )
    except:
        d["Rolling Return 1Y"] = None
        d["Rolling Return 3Y"] = None

    return d


# ============================================================
#   PEER RANKING
# ============================================================

def compute_category_peer_ranking(df):
    df["Category Rank (1Y)"] = df.groupby("Scheme Category")["NAV 1Y"] \
                                 .rank(ascending=False)

    df["Quartile (1Y)"] = df["Category Rank (1Y)"].apply(
        lambda r: (
            "Top Quartile" if r <= 25 else
            "Second Quartile" if r <= 50 else
            "Third Quartile" if r <= 75 else
            "Bottom Quartile"
        )
    )
    return df


def compute_sector_peer_ranking(df):
    df["Sector Rank (1Y)"] = df.groupby("Sector Theme")["NAV 1Y"] \
                               .rank(ascending=False)
    df["Sector Performance Tag (1Y)"] = df["Sector Rank (1Y)"].apply(
        lambda r: "Sector Leader" if r <= 3 else "Sector Laggard" if r > 10 else ""
    )
    return df


# ============================================================
#   AI FUND SCORE (OPTION A – AGGRESSIVE MOMENTUM)
# ============================================================

def compute_ai_score(r):
    score = 0

    # Momentum weights
    w = {
        "NAV 1M": 25,
        "NAV 3M": 25,
        "NAV 1Y": 20,
        "NAV 3Y": 20
    }

    for k, wt in w.items():
        try:
            score += (r[k] if r[k] else 0) * (wt / 100)
        except:
            pass

    # Volatility penalty
    if r["Volatility (StdDev 1Y)"]:
        score -= r["Volatility (StdDev 1Y)"] * 80

    # Peer quartile bonus
    if r["Quartile (1Y)"] == "Top Quartile":
        score += 5

    # Rolling consistency
    try:
        rr = (r["Rolling Return 1Y"] + r["Rolling Return 3Y"]) / 2
        score += rr * 10
    except:
        pass

    return round(score, 2)


# ============================================================
#   RISK SCORE
# ============================================================

def compute_risk_score(row):
    vol = row["Volatility (StdDev 1Y)"]
    dd = row["Max Drawdown"]

    if vol is None: return "Medium"

    if vol < 0.01 and dd > -0.10:
        return "Low"
    if vol < 0.03 and dd > -0.20:
        return "Medium"
    return "High"


# ============================================================
#   EXIT LOAD LOGIC (RULE-BASED)
# ============================================================

def compute_exit_load(cat):
    cat = cat.lower()

    if "equity" in cat:
        return "1% if redeemed before 1 year"
    if "hybrid" in cat:
        return "1% before 90 days"
    if "debt" in cat:
        return "0.25% before 30 days"
    if "liquid" in cat:
        return "Graded load decreasing to zero in 7 days"
    if "elss" in cat:
        return "Locked for 3 years"
    return ""


# ============================================================
#   EXCEL EXPORT WITH DASHBOARD + TOP 10
# ============================================================

def save_excel(df):
    wb = Workbook()
    ws = wb.active
    ws.title = "Direct MF Grid"

    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    # Bold headers
    for col in ws.iter_cols(1, ws.max_column):
        col[0].font = Font(bold=True)

    # ===========================
    # Dashboard Sheet
    # ===========================
    dash = wb.create_sheet("Dashboard")
    dash.append(["Metric", "Value"])
    dash.append(["Total Schemes", len(df)])
    dash.append(["Average AI Score", df["AI Fund Score"].mean()])
    dash.append(["Low Risk Funds", (df["Risk Score"] == "Low").sum()])
    dash.append(["Top Quartile Funds", (df["Quartile (1Y)"] == "Top Quartile").sum()])

    # ===========================
    # TOP 10 Sheet
    # ===========================
    top = wb.create_sheet("Top 10 Summary")

    def add_block(title, data):
        top.append([title])
        for r in dataframe_to_rows(data, index=False, header=True):
            top.append(r)
        top.append([""])

    add_block("Top 10 — 1M Performers", df.nlargest(10, "NAV 1M"))
    add_block("Top 10 — 3M Performers", df.nlargest(10, "NAV 3M"))
    add_block("Top 10 — 1Y Performers", df.nlargest(10, "NAV 1Y"))
    add_block("Top 10 — Low Volatility", df.nsmallest(10, "Volatility (StdDev 1Y)"))
    add_block("Top 10 — Category Leaders", df[df["Quartile (1Y)"] == "Top Quartile"].head(10))

    wb.save(FINAL_XLSX)


# ============================================================
#   MAIN
# ============================================================

def main():
    print("Loading master list...")
    master = load_master_list()
    discontinued = load_discontinued()

    print("Fetching schemes...")
    curr = pd.DataFrame(fetch_direct_scheme_list())

    prev = set(master["Scheme Code"])
    now = set(curr["schemeCode"])

    removed = prev - now
    added = now - prev

    # Mark discontinued
    for c in removed:
        old = master.loc[master["Scheme Code"] == c, "Scheme Name"].iloc[0]
        discontinued = pd.concat([
            discontinued,
            pd.DataFrame([{
                "Scheme Code": c,
                "Scheme Name": old,
                "Date Discontinued": datetime.today().strftime("%Y-%m-%d")
            }])
        ])

    # Add new ones
    for c in added:
        nm = curr[curr["schemeCode"] == c]["schemeName"].iloc[0]
        master = pd.concat([
            master,
            pd.DataFrame([{
                "Scheme Code": c,
                "Scheme Name": nm,
                "Scheme Category": "",
                "Scheme Status": "Active"
            }])
        ])

    master["Scheme Status"] = master["Scheme Code"].apply(
        lambda c: "Discontinued" if c in removed else "Active"
    )

    # Now process NAV + metrics
    rows = []

    for i, r in master.iterrows():
        code = r["Scheme Code"]
        oldname = r["Scheme Name"]

        print(f"→ {i+1}/{len(master)}: {oldname} ({code})")

        df, js = load_nav_history(code)
        meta = js.get("meta", {})

        cat = normalize_category(meta.get("category", ""))
        amc = meta.get("fund_house", "")
        sector = detect_sector_theme(oldname)

        ret = compute_returns(df)
        name_changed = "Yes" if oldname != meta.get("scheme_name", oldname) else "No"

        rows.append({
            "AMC": amc,
            "Scheme Code": code,
            "Scheme Name": oldname,
            "Scheme Category": cat,
            "Sector Theme": sector,
            "Scheme Status": r["Scheme Status"],
            "Name Changed (Yes/No)": name_changed,
            **ret
        })

    df = pd.DataFrame(rows)

    # Rankings
    df = compute_category_peer_ranking(df)
    df = compute_sector_peer_ranking(df)

    # AI Score
    df["AI Fund Score"] = df.apply(compute_ai_score, axis=1)

    # Risk Score
    df["Risk Score"] = df.apply(compute_risk_score, axis=1)

    # Exit Load
    df["Exit Load"] = df["Scheme Category"].apply(compute_exit_load)

    # Sort final
    df = df.sort_values(["AMC", "Scheme Name"])

    df.to_csv(FINAL_CSV, index=False)
    save_excel(df)
    save_master_list(master)
    save_discontinued(discontinued)

    print("\nDONE ✓ All outputs generated.")


if __name__ == "__main__":
    main()
