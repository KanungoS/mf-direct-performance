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

    # ------------------------------------------------------------
    # 1. Load portfolio
    # ------------------------------------------------------------
    pf = pd.read_csv(PORTFOLIO_INPUT, parse_dates=["Date of Purchase"])
    pf.columns = pf.columns.str.strip()

    # ------------------------------------------------------------
    # 2. Load returns
    # ------------------------------------------------------------
    ret = pd.read_csv(RETURNS_FILE)
    ret.columns = ret.columns.str.strip()

    ret = ret[[
        "SchemeCode",
        "Return_1M",
        "Return_3M",
        "Return_6M"
    ]]

    pf = pf.merge(ret, on="SchemeCode", how="left")

    # ------------------------------------------------------------
    # 3. Current Value
    # ------------------------------------------------------------
    pf["Current Value"] = (pf["Units"] * pf["Current NAV"]).round(2)

    # ------------------------------------------------------------
    # 4. Exit Load Impact (supports 1 or 2 slabs)
    # ------------------------------------------------------------
    today = pd.Timestamp.today().normalize()
    pf["Date of Purchase"] = pd.to_datetime(pf["Date of Purchase"], errors="coerce")

    pf["Holding_Days"] = (today - pf["Date of Purchase"]).dt.days

    # Normalize headers
    pf.columns = pf.columns.str.strip()

    # Defaults
    pf["Exit_Load_Impact_%"] = 0.0

    mask_exit = pf["Will Exit Load Apply"].astype(str).str.upper() == "Y"

    # ---------- Exit Load Period 1 ----------
    p1_days = (
    pf.loc[mask_exit, "Exit Load Period -1"]
    .astype(str)
    .str.extract(r"(\d+)")[0]
    .astype(float)
    )
    p1_pct = pf.loc[mask_exit, "Exit Load %-1"].fillna(0)

    # ---------- Exit Load Period 2 (optional) ----------
    if "Exit Load Period -2" in pf.columns and "Exit Load %-2" in pf.columns:
    p2_days = (
        pf.loc[mask_exit, "Exit Load Period -2"]
        .astype(str)
        .str.extract(r"(\d+)")[0]
        .astype(float)
    )
    p2_pct = pf.loc[mask_exit, "Exit Load %-2"].fillna(0)
else:
    p2_days = None
    p2_pct = None

    # ---------- Apply slab logic ----------
    for idx in pf.loc[mask_exit].index:
    hd = pf.at[idx, "Holding_Days"]

    if hd <= p1_days.loc[idx]:
        pf.at[idx, "Exit_Load_Impact_%"] = p1_pct.loc[idx]

    elif p2_days is not None and pd.notna(p2_days.loc[idx]) and hd <= p2_days.loc[idx]:
        pf.at[idx, "Exit_Load_Impact_%"] = p2_pct.loc[idx]

    else:
        pf.at[idx, "Exit_Load_Impact_%"] = 0.0

    # ---------- Exit Load Amount ----------
    pf["Exit_Load_Amount"] = (
    pf["Current Value"] * pf["Exit_Load_Impact_%"] / 100
    ).round(2)


    # ------------------------------------------------------------
    # 5. IRR (Lump-sum approximation)
    # ------------------------------------------------------------
    pf["IRR"] = pf.apply(
        lambda r: xirr([
            (r["Date of Purchase"], -r["Total Purchase Value"]),
            (datetime.today(), r["Current Value"])
        ]),
        axis=1
    )

    # ------------------------------------------------------------
    # 6. ALERT — Positive Momentum
    # ------------------------------------------------------------
    pf["ALERT"] = np.where(
        (pf["Return_1M"] > 0) &
        (pf["Return_3M"] > 0) &
        (pf["Return_6M"] > 0),
        "POSITIVE MOMENTUM – CONSIDER INVEST MORE",
        ""
    )

    # ------------------------------------------------------------
    # 7. Save output
    # ------------------------------------------------------------
    pf.to_csv(PORTFOLIO_OUTPUT, index=False)


if __name__ == "__main__":
    main()
