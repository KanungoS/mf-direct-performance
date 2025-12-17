import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
GRID_FILE = DATA_DIR / "mf_direct_grid.csv"
PORTFOLIO_FILE = DATA_DIR / "my_portfolio.csv"

def log(msg):
    print(msg, flush=True)

def update_portfolio():
    grid = pd.read_csv(GRID_FILE, usecols=["Scheme Code", "NAV Latest"])
    pf = pd.read_csv(PORTFOLIO_FILE)

    grid["Scheme Code"] = grid["Scheme Code"].astype(str)
    pf["Scheme Code"] = pf["Scheme Code"].astype(str)

    merged = pf.merge(grid, on="Scheme Code", how="left")

    merged["Current NAV"] = merged["NAV Latest"]
    merged["Current Date"] = datetime.now().strftime("%d-%m-%Y")
    merged["Current Value"] = merged["Units"] * merged["Current NAV"]
    merged["% Deviation"] = (
        (merged["Current Value"] - merged["Total Purchase Value"])
        / merged["Total Purchase Value"] * 100
    )

    merged["Data Audit Status"] = merged["Current NAV"].apply(
        lambda x: "OK" if pd.notna(x) else "NAV_MISSING"
    )

    merged.drop(columns=["NAV Latest"], inplace=True)
    merged.to_csv(PORTFOLIO_FILE, index=False)

    log("Portfolio updated")

if __name__ == "__main__":
    update_portfolio()
