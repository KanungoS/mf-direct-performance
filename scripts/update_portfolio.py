import pandas as pd
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("data")
GRID_FILE = DATA_DIR / "mf_direct_grid.csv"
PORTFOLIO_FILE = DATA_DIR / "my_portfolio.csv"

def main():
    grid = pd.read_csv(GRID_FILE, dtype={"Scheme Code": str})
    pf = pd.read_csv(PORTFOLIO_FILE, dtype={"Scheme Code": str})

    merged = pf.merge(
        grid[["Scheme Code", "NAV Latest"]],
        on="Scheme Code",
        how="left"
    )

    merged["Current NAV"] = merged["NAV Latest"]
    merged["Current Date"] = datetime.now().strftime("%d-%m-%Y")
    merged["Current Value"] = merged["Units"] * merged["Current NAV"]
    merged["% Deviation"] = (
        (merged["Current Value"] - merged["Total Purchase Value"])
        / merged["Total Purchase Value"] * 100
    )

    merged.drop(columns=["NAV Latest"], inplace=True)
    merged.to_csv(PORTFOLIO_FILE, index=False)

    print("Portfolio updated")

if __name__ == "__main__":
    main()
