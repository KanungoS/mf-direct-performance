import requests
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------- CONFIG ----------------
MFAPI_BASE = "https://api.mfapi.in/mf"
TIMEOUT = 8
MAX_WORKERS = 12
RETRIES = 2

DATA_DIR = Path("data")
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

MASTER_FILE = DATA_DIR / "master_list.csv"      # Direct + Active only
GRID_FILE = DATA_DIR / "mf_direct_grid.csv"

# --------------------------------------

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ---------- MFAPI FETCH (cached + retry) ----------
def fetch_mfapi(code):
    cache_file = CACHE_DIR / f"{code}.json"

    if cache_file.exists():
        with open(cache_file, "r") as f:
            return json.load(f)

    for _ in range(RETRIES):
        try:
            r = requests.get(f"{MFAPI_BASE}/{code}", timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            with open(cache_file, "w") as f:
                json.dump(data, f)
            return data
        except:
            time.sleep(1)

    return None

# ---------- NAV HELPERS ----------
def compute_navs(df):
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    df["nav"] = df["nav"].astype(float)
    df = df.sort_values("date")

    latest = df.iloc[-1]
    def nav_at(days):
        past = df[df["date"] <= latest["date"] - timedelta(days=days)]
        return past.iloc[-1]["nav"] if not past.empty else None

    navs = {
        "NAV Latest": latest["nav"],
        "NAV 1D": nav_at(1),
        "NAV 1W": nav_at(7),
        "NAV 1M": nav_at(30),
        "NAV 3M": nav_at(90),
        "NAV 6M": nav_at(180),
        "NAV 1Y": nav_at(365),
    }

    for k, v in navs.items():
        if v is None:
            navs[k] = None

    return navs

def returns(latest, past):
    return ((latest / past) - 1) * 100 if past else None

# ---------- MAIN GRID BUILDER ----------
def build_grid():
    master = pd.read_csv(MASTER_FILE)
    results = []
    total = len(master)

    log(f"Processing {total} Direct + Active schemes")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_mfapi, row["Scheme Code"]): row
            for _, row in master.iterrows()
        }

        done = 0
        for future in as_completed(futures):
            row = futures[future]
            code = row["Scheme Code"]
            done += 1

            try:
                data = future.result()
                if not data or "data" not in data:
                    raise Exception("No MFAPI data")

                nav_df = pd.DataFrame(data["data"])
                navs = compute_navs(nav_df)

                audit = "OK" if navs["NAV Latest"] else "NAV_MISSING"

                results.append({
                    "AMC": data["meta"].get("fund_house"),
                    "Scheme Code": code,
                    "Scheme Name": data["meta"].get("scheme_name"),
                    "Scheme Category": data["meta"].get("scheme_category"),
                    "Sector Theme": data["meta"].get("scheme_type"),

                    **navs,

                    "%Return 1D": returns(navs["NAV Latest"], navs["NAV 1D"]),
                    "%Return 1W": returns(navs["NAV Latest"], navs["NAV 1W"]),
                    "%Return 1M": returns(navs["NAV Latest"], navs["NAV 1M"]),
                    "%Return 3M": returns(navs["NAV Latest"], navs["NAV 3M"]),
                    "%Return 6M": returns(navs["NAV Latest"], navs["NAV 6M"]),
                    "%Return 1Y": returns(navs["NAV Latest"], navs["NAV 1Y"]),

                    "Data Audit Status": audit,
                    "Last Updated": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

            except Exception as e:
                results.append({
                    "Scheme Code": code,
                    "Scheme Name": row["Scheme Name"],
                    "Data Audit Status": "FAILED"
                })

            if done % 500 == 0:
                log(f"Processed {done}/{total}")

    pd.DataFrame(results).to_csv(GRID_FILE, index=False)
    log("MF Direct Grid written")

if __name__ == "__main__":
    build_grid()
