import requests
import pandas as pd
from datetime import datetime
from pathlib import Path

MFAPI_BASE = "https://api.mfapi.in/mf"
TIMEOUT = 7
DATA_DIR = Path("data")

MASTER_FILE = DATA_DIR / "master_list.csv"
GRID_FILE = DATA_DIR / "mf_direct_grid.csv"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def fetch_mfapi(code):
    r = requests.get(f"{MFAPI_BASE}/{int(code)}", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def main():
    master = pd.read_csv(MASTER_FILE, dtype={"Scheme Code": str})
    results = []

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

            def nav_at(days):
                d = latest["date"] - pd.Timedelta(days=days)
                p = navs[navs["date"] <= d]
                return p.iloc[-1]["nav"] if not p.empty else None

            def ret(p):
                return ((latest["nav"] / p) - 1) * 100 if p else None

            n1d, n1w, n1m, n3m, n6m, n1y = (
                nav_at(1), nav_at(7), nav_at(30),
                nav_at(90), nav_at(180), nav_at(365)
            )

            results.append({
                "AMC": meta.get("fund_house"),
                "Scheme Code": code,
                "Scheme Name": row["Scheme Name"],
                "Scheme Category": meta.get("scheme_category"),
                "Sector Theme": meta.get("scheme_type"),
                "Scheme Status": row["Scheme Status"],
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
                "%Return 1Y": ret(n1y)
            })

        except Exception as e:
            log(f"Skipped {code}: {e}")

        if (i + 1) % 200 == 0:
            log(f"Processed {i+1}/{len(master)}")

    pd.DataFrame(results).to_csv(GRID_FILE, index=False)
    log("mf_direct_grid.csv written")

if __name__ == "__main__":
    main()
