import requests
import pandas as pd
import time
from datetime import datetime
from pathlib import Path

# ---------------- CONFIG ----------------
AMFI_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
MFAPI_BASE = "https://api.mfapi.in/mf"
TIMEOUT = 7
BATCH_SIZE = 50

DATA_DIR = Path("data")
MASTER_FILE = DATA_DIR / "master_list.csv"
PORTFOLIO_FILE = DATA_DIR / "my_portfolio.csv"
GRID_FILE = DATA_DIR / "mf_direct_grid.csv"

# ----------------------------------------

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------- AMFI PARSER ----------
def load_amfi_master():
    log("Fetching AMFI master list")
    r = requests.get(AMFI_URL, timeout=TIMEOUT)
    r.raise_for_status()

    rows = []
    for line in r.text.splitlines():
        if not line or line.startswith("Scheme Code"):
            continue
        parts = line.replace(";-;", ";").split(";")
        if len(parts) < 6:
            continue
        rows.append({
            "Scheme Code": parts[0].strip(),
            "Scheme Name": parts[3].strip(),
            "Scheme Status": "Active"
        })

    df = pd.DataFrame(rows).drop_duplicates("Scheme Code")
    df.to_csv(MASTER_FILE, index=False)
    log(f"Loaded {len(df)} schemes from AMFI")
    return df

# ---------- MFAPI FETCH ----------
def fetch_mfapi_data(code):
    url = f"{MFAPI_BASE}/{code}"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# ---------- GRID BUILDER ----------
def build_grid(master_df):
    log("Building MF Direct Grid")

    results = []
    total = len(master_df)

    for i in range(0, total, BATCH_SIZE):
        batch = master_df.iloc[i:i+BATCH_SIZE]

        for idx, row in batch.iterrows():
            code = row["Scheme Code"]

            try:
                data = fetch_mfapi_data(code)
                meta = data["meta"]
                navs = pd.DataFrame(data["data"])
                navs["date"] = pd.to_datetime(navs["date"], dayfirst=True)
                navs["nav"] = navs["nav"].astype(float)
                navs = navs.sort_values("date")

                latest = navs.iloc[-1]
                def nav_at(days):
                    d = latest["date"] - pd.Timedelta(days=days)
                    past = navs[navs["date"] <= d]
                    return past.iloc[-1]["nav"] if not past.empty else None

                def ret(p):
                    return ((latest["nav"] / p) - 1) * 100 if p else None

                n1d = nav_at(1)
                n1w = nav_at(7)
                n1m = nav_at(30)
                n3m = nav_at(90)
                n6m = nav_at(180)
                n1y = nav_at(365)

                results.append({
                    "AMC": meta.get("fund_house"),
                    "Scheme Code": code,
                    "Scheme Name": meta.get("scheme_name"),
                    "Scheme Category": meta.get("scheme_category"),
                    "Sector Theme": meta.get("scheme_type"),
                    "Scheme Status": row["Scheme Status"],
                    "Name Changed (Yes/No)": "No",
                    "NAV Latest": latest["nav"],
                    "NAV 1D": n1d,
                    "NAV 1W": n1w,
                    "NAV 1M": n1m,
                    "NAV 3M": n3m,
                    "NAV 6M": n6m,
                    "NAV 1Y": n1y,
                    "%Return 1D": ret(n1d),
                    "%Return 1W": ret(n1w),
                    "%Return 1M": ret(n1m),
                    "%Return 3M": ret(n3m),
                    "%Return 6M": ret(n6m),
                    "%Return 1Y": ret(n1y),
                    "Category Rank (1Y)": None,
                    "Category Size": None,
                    "Quartile (1Y)": None,
                    "Performance Tag (1Y)": None,
                    "Category Avg Return (1Y)": None,
                    "Category Return Deviation (1Y)": None,
                    "Sector Avg Return (1Y)": None,
                    "Sector Rank (1Y)": None,
                    "Sector Return Deviation (1Y)": None,
                    "Sector Quartile (1Y)": None,
                    "Sector Performance Tag (1Y)": None
                })

            except Exception as e:
                log(f"⚠️ Skipped {code}: {e}")

        log(f"Processed {min(i+BATCH_SIZE, total)} / {total} schemes")

    df = pd.DataFrame(results)
    df.to_csv(GRID_FILE, index=False)
    log("MF Direct Grid written")

# ---------- PORTFOLIO UPDATE ----------
def update_portfolio(grid_df):
    if not PORTFOLIO_FILE.exists():
        return

    pf = pd.read_csv(PORTFOLIO_FILE)
    merged = pf.merge(
        grid_df[["Scheme Code", "NAV Latest"]],
        on="Scheme Code",
        how="left"
    )

    merged["Current NAV"] = merged["NAV Latest"]
    merged["Current Date"] = datetime.now().strftime("%d-%m-%Y")
    merged["Current Value"] = merged["Units"] * merged["Current NAV"]
    merged["% Deviation"] = (
        (merged["Current Value"] - merged["Total Purchase Value"])
        / merged["Total Purchase Value"] * 100
    )

    merged.drop(columns=["NAV Latest"], inplace=True)
    merged.to_csv(PORTFOLIO_FILE, index=False)
    log("Portfolio updated")

# ---------- MAIN ----------
def main():
    master = load_amfi_master()
    build_grid(master)
    grid = pd.read_csv(GRID_FILE)
    update_portfolio(grid)
    log("ALL DONE")

if __name__ == "__main__":
    main()
