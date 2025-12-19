import pandas as pd
from datetime import timedelta

CORE_FILE = "data/mf_core_direct_openended.csv"
NAV_HISTORY_FILE = "data/nav_history.csv"
OUTPUT_FILE = "data/mf_core_with_returns.csv"

WINDOWS = {
    "1W": 7,
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "3Y": 1095,
    "5Y": 1825
}


def closest_nav(hist, scheme, target_date):
    df = hist[(hist["SchemeCode"] == scheme) &
              (hist["NAV_Date"] <= target_date)]
    if df.empty:
        return None
    return df.sort_values("NAV_Date", ascending=False).iloc[0]["NAV"]


def build_returns():
    core = pd.read_csv(CORE_FILE, parse_dates=["NAV_As_Of_Date"])
    hist = pd.read_csv(NAV_HISTORY_FILE, parse_dates=["NAV_Date"])

    for label, days in WINDOWS.items():
        vals = []
        for _, r in core.iterrows():
            past_nav = closest_nav(
                hist,
                r["SchemeCode"],
                r["NAV_As_Of_Date"] - timedelta(days=days)
            )
            if past_nav:
                vals.append(round((r["NAV"] / past_nav - 1) * 100, 2))
            else:
                vals.append(None)
        core[f"Return_{label}_%"] = vals

    core.to_csv(OUTPUT_FILE, index=False)


if __name__ == "__main__":
    build_returns()
