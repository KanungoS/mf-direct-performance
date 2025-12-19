import pandas as pd
import numpy as np
from datetime import datetime

PORTFOLIO_INPUT = "data/my_portfolio_input.csv"
PORTFOLIO_OUTPUT = "data/my_portfolio.csv"
RETURNS_FILE = "data/mf_core_with_returns.csv"

def xirr(cashflows):
    days = np.array([(d - cashflows[0][0]).days for d, _ in cashflows])
    amounts = np.array([v for _, v in cashflows])
    try:
        return np.irr(amounts) * 365 / np.mean(days)
    except:
        return np.nan

def main():
    # 1. Load portfolio
    pf = pd.read_csv(PORTFOLIO_INPUT, parse_dates=["Date of Purchase"])
    pf.columns = pf.columns.str.strip()
	
    # 2. Load returns
    ret = pd.read_csv(RETURNS_FILE)

    ret = ret[[
        "SchemeCode",
        "Return_1M",
        "Return_3M",
        "Return_6M"
    ]]

    pf = pf.merge(ret, on="SchemeCode", how="left")

    # 3. Current Value
    pf["Current Value"] = pf["Units"] * pf["Current NAV"]

    # ------------------------------------------------------------
# 4. Exit Load Impact (correct & safe)
# ------------------------------------------------------------

# Ensure required columns exist (avoid KeyError)
pf.columns = pf.columns.str.strip()

# Parse dates
pf["Date of Purchase"] = pd.to_datetime(pf["Date of Purchase"], errors="coerce")
today = pd.Timestamp.today().normalize()

# Holding period in days
pf["Holding_Days"] = (today - pf["Date of Purchase"]).dt.days

# Exit load % (default 0)
pf["Exit_Load_Impact_%"] = 0.0

mask_exit = pf["Will Exit Load Apply"].str.upper() == "Y"

pf.loc[mask_exit, "Exit_Load_Impact_%"] = np.where(
    pf.loc[mask_exit, "Holding_Days"] <
    pf.loc[mask_exit, "Exit Load Period - 1"].str.extract(r"(\d+)").astype(float)[0],
    pf.loc[mask_exit, "Exit Load % - 1"],
    0
)

# Exit load amount (₹ impact)
pf["Exit_Load_Amount"] = (
    pf["Current Value"] * pf["Exit_Load_Impact_%"] / 100
).round(2)

    pf["Exit_Load_Impact_Value"] = pf["Current Value"] * pf["Exit_Load_Impact_%"] / 100

    # 5. SIP / IRR (simple cashflow)
    pf["IRR"] = pf.apply(
        lambda r: xirr([
            (r["Date of Purchase"], -r["Total Purchase Value"]),
            (datetime.today(), r["Current Value"])
        ]),
        axis=1
    )

    # 6. ALERTS — Positive Momentum → Invest More
    pf["ALERT"] = np.where(
        (pf["Return_1M"] > 0) &
        (pf["Return_3M"] > 0) &
        (pf["Return_6M"] > 0),
        "POSITIVE MOMENTUM – CONSIDER INVEST MORE",
        ""
    )

    pf.to_csv(PORTFOLIO_OUTPUT, index=False)

if __name__ == "__main__":
    main()
