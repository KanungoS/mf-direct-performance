import pandas as pd

NAV_HISTORY = "data/nav_history.csv"
CORE_FILE = "data/mf_core_direct_openended.csv"
OUTPUT = "data/mf_core_with_returns.csv"

WINDOWS = {
    "Return_1M": 30,
    "Return_3M": 90,
    "Return_6M": 180,
}

def compute_returns():
    nav = pd.read_csv(NAV_HISTORY, parse_dates=["NAV_Date"])
    core = pd.read_csv(CORE_FILE)

    today = nav["NAV_Date"].max()
    out = core.copy()

    for col, days in WINDOWS.items():
        past = today - pd.Timedelta(days=days)

        now = nav[nav["NAV_Date"] == today][["SchemeCode", "NAV"]]
        old = nav[nav["NAV_Date"] <= past].groupby("SchemeCode").last().reset_index()

        m = now.merge(old, on="SchemeCode", suffixes=("_now", "_old"))
        m[col] = ((m["NAV_now"] / m["NAV_old"]) - 1) * 100
        out = out.merge(m[["SchemeCode", col]], on="SchemeCode", how="left")

    # Tactical Rank Score
    out["Rank_Score"] = (
        out["Return_1M"] * 0.4 +
        out["Return_3M"] * 0.3 +
        out["Return_6M"] * 0.3
    )

    out["Rank"] = out["Rank_Score"].rank(ascending=False, method="dense")
    out.to_csv(OUTPUT, index=False)

if __name__ == "__main__":
    compute_returns()
