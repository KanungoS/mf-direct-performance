import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------- CONFIG ----------------
MFAPI_BASE = "https://api.mfapi.in/mf"
TIMEOUT = 7
MAX_WORKERS = 8   # SAFE parallelism

DATA_DIR = Path("data")
MASTER_FILE = DATA_DIR / "master_list.csv"
PORTFOLIO_FILE = DATA_DIR / "my_portfolio.csv"
GRID_FILE = DATA_DIR / "mf_direct_grid.csv"

# ----------------------------------------

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------- MFAPI ----------
def fetch_one_scheme(row):
    code = row["Scheme Code"]
    try:
        r = requests.get(f"{MFAPI_BASE}/{code}", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()

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

        n1d, n1w, n1m, n3m, n6m, n1y = (
            nav_at(1), nav_at(7), nav_at(30),
            nav_at(90), nav_at(180), nav_at(365)
        )

        meta = data["meta"]

        return {
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
        }

    except Exception as e:
        log(f"⚠️ {code} skipped: {e}")
        return None

# ---------- MAIN ----------
def main():
    log("Loading master_list.csv")
    master = pd.read_csv(MASTER_FILE, dtype={"Scheme Code": str})
    total = len(master)
    log(f"Total schemes: {total}")

    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_one_scheme, row): i
                   for i, row in master.iterrows()}

        for i, future in enumerate(as_completed(futures), 1):
            r = future.result()
            if r:
                results.append(r)
            if i % 250 == 0:
                log(f"Processed {i} / {total}")

    grid = pd.DataFrame(results)
    grid.to_csv(GRID_FILE, index=False)
    log("mf_direct_grid.csv written")

    # ---------- Portfolio update ----------
    if PORTFOLIO_FILE.exists():
        pf = pd.read_csv(PORTFOLIO_FILE, dtype={"Scheme Code": str})
        pf = pf.merge(
            grid[["Scheme Code", "NAV Latest"]],
            on="Scheme Code",
            how="left"
        )

        pf["Current NAV"] = pf["NAV Latest"]
        pf["Current Date"] = datetime.now().strftime("%d-%m-%Y")
        pf["Current Value"] = pf["Units"] * pf["Current NAV"]
        pf["% Deviation"] = (
            (pf["Current Value"] - pf["Total Purchase Value"])
            / pf["Total Purchase Value"] * 100
        )

        pf.drop(columns=["NAV Latest"], inplace=True)
        pf.to_csv(PORTFOLIO_FILE, index=False)
        log("my_portfolio.csv updated")

    log("ALL DONE")

if __name__ == "__main__":
    main()
