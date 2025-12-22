# scripts/portfolio_engine.py

import pandas as pd
from datetime import datetime

DATA_DIR = "data"
PORTFOLIO_INPUT = f"{DATA_DIR}/my_portfolio_input.csv"
NAV_HISTORY = f"{DATA_DIR}/nav_history.csv"
PORTFOLIO_OUTPUT = f"{DATA_DIR}/my_portfolio.csv"


def main():
    pf = pd.read_csv(PORTFOLIO_INPUT)
    nav = pd.read_csv(NAV_HISTORY)

    nav["NAV_Date"] = pd.to_datetime(nav["NAV_Date"])
    pf["Date_of_Purchase"] = pd.to_datetime(pf["Date_of_Purchase"])

    latest_nav = (
        nav.sort_values("NAV_Date")
           .groupby("SchemeCode")
           .tail(1)
           .set_index("SchemeCode")
    )

    pf["Current_NAV"] = pf["SchemeCode"].map(latest_nav["NAV"])
    pf["Current_Date"] = pf["SchemeCode"].map(latest_nav["NAV_Date"])

    pf["Current_Value"] = pf["Units"] * pf["Current_NAV"]

    pf["Pct_Deviation"] = (
        (pf["Current_Value"] - pf["Total_Purchase_Value"])
        / pf["Total_Purchase_Value"] * 100
    ).round(2)

    pf.to_csv(PORTFOLIO_OUTPUT, index=False)
    print("my_portfolio.csv generated successfully")


if __name__ == "__main__":
    main()
