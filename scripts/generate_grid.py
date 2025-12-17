import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import time

# ---------------- CONFIG ----------------
MFAPI_BASE = "https://api.mfapi.in/mf"
TIMEOUT = 8
SLEEP = 0.2

DATA_DIR = Path("data")
MASTER_FILE = DATA_DIR / "master_list.csv"
PORTFOLIO_FILE = DATA_DIR / "my_portfolio.csv"
GRID_FILE = DATA_DIR / "mf_direct_grid.csv"
# ---------------------------------------

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------- LOAD MASTER ----------
def load_master():
    if not MASTER_FILE.exists():
        raise FileNotFoundError("master_list.csv missing")

    df = pd.read_csv(MASTER_FILE, dtype=str)
    required = {"Scheme Code", "Scheme Name", "Scheme Status"}
    if not required.issubset(df.columns):
        raise ValueError("master_list.csv missing required columns")

    log(f"Loaded {len(df)} schemes from master_list.csv")
    return df

# ---------- MFAPI ----------
def fetch_mfapi(code):
    r = requests.get(f"{MFAPI_BASE}/{code}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

# ---------- GRID ----------
def build_grid(master):
    results = []
    total = len(master)

    for i, row in master.iterrows():
        code = row["Scheme Code"]

        try:
            data = fetch_mfapi(code)
            meta = data["meta"]
            navs = pd.DataFrame(data["data"])

            navs["date"] = pd.to_datetime(navs["date"], dayfirst=True)
            navs["nav"] = navs["nav"].astype(float)
            navs = navs.sort_values("date")

            latest = navs.iloc[-1]

            def nav_days(d):
                past = navs[navs["date"] <= latest["date"] - pd.Timedelta(days=d)]
                return past.iloc[-1]["nav"] if not past.empty else None

            def ret(p):
                return ((latest["nav"] / p) - 1) * 100 if p else None

            n1d, n1w, n1m, n3m, n6m, n1y = (
                nav_days(1), nav_days(7), nav_days(30),
                nav_days(90), nav_days(180), nav_days(365)
            )

            results.append({
                "AMC": meta.get("fund_house"),
                "Scheme Code": code,
                "Scheme Name": row["Scheme Name"],
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
            log(f"Skipped {code}: {e}")

        if (i + 1) % 50 == 0:
            log(f"Processed {i + 1} / {total}")

        time.sleep(SLEEP)

    df = pd.DataFrame(results)
    df.to_csv(GRID_FILE, index=False)
    log("mf_direct_grid.csv written")

    return df

# ---------- PORTFOLIO ----------
def update_portfolio(grid):
    if not PORTFOLIO_FILE.exists():
        log("my_portfolio.csv not found — skipping")
        return

    pf = pd.read_csv(PORTFOLIO_FILE)

    merged = pf.merge(
        grid[["Scheme Code", "NAV Latest"]],
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
    log("my_portfolio.csv updated")

# ---------- MAIN ----------
def main():
    master = load_master()
    grid = build_grid(master)
    update_portfolio(grid)
    log("ALL DONE")

if __name__ == "__main__":
    main()
