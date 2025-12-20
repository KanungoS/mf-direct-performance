# scripts/mf_core_engine.py

import pandas as pd
from datetime import timedelta

DATA_DIR = "data"
MASTER_FILE = f"{DATA_DIR}/master_list.csv"
NAV_HISTORY = f"{DATA_DIR}/nav_history.csv"
OUTPUT_FILE = f"{DATA_DIR}/mf_core_direct_openended.csv"


def pct_return(latest, past):
    return ((latest - past) / past * 100) if past else None


def main():
    master = pd.read_csv(MASTER_FILE)    
    nav = pd.read_csv(NAV_HISTORY)

    nav["NAV_Date"] = pd.to_datetime(nav["NAV_Date"])

    master = master[master["Scheme_Status"] == "Active"]

    rows = []

    for _, row in master.iterrows():
        sc = row["SchemeCode"]
        scheme_nav = nav[nav["SchemeCode"] == sc].sort_values("NAV_Date")

        if scheme_nav.empty:
            continue

        latest = scheme_nav.iloc[-1]
        latest_date = latest["NAV_Date"]

        def nav_before(days):
            past = scheme_nav[scheme_nav["NAV_Date"] <= latest_date - timedelta(days=days)]
            return past.iloc[-1]["NAV"] if not past.empty else None

        rows.append({
            "SchemeCode": sc,
            "SchemeName": row["SchemeName"],
            "Scheme_Category": row["Scheme_Category"],
            "Risk_Level": "NA",
            "Latest_NAV": latest["NAV"],
            "NAV_As_Of_Date": latest_date.date(),
            "Valuation_Date": datetime.today().date(),
            "% Return_1D": pct_return(latest["NAV"], nav_before(1)),
            "% Return_1W": pct_return(latest["NAV"], nav_before(7)),
            "% Return_1M": pct_return(latest["NAV"], nav_before(30)),
            "% Return_3M": pct_return(latest["NAV"], nav_before(90)),
            "% Return_6M": pct_return(latest["NAV"], nav_before(180)),
            "% Return_1Y": pct_return(latest["NAV"], nav_before(365)),
        })

    pd.DataFrame(rows).to_csv(OUTPUT_FILE, index=False)
    print("mf_core_direct_openended.csv created")


if __name__ == "__main__":
    main()
