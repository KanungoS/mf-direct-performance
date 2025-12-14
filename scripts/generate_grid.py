#!/usr/bin/env python3
import pandas as pd
import numpy as np
import requests
import datetime as dt
import os

DATA_DIR = "data"
MASTER_FILE = f"{DATA_DIR}/master_fund_list.csv"
PORTFOLIO_FILE = f"{DATA_DIR}/my_portfolio.csv"
OUTPUT_GRID_FILE = f"{DATA_DIR}/mf_direct_grid.xlsx"


# -----------------------------------------------------------
# Load Mutual Fund NAV history from MFAPI
# -----------------------------------------------------------
def load_nav_history(code):
    """
    Safe loader: returns a DataFrame with columns ['date','nav']
    Always returns valid structure (even empty).
    """
    url = f"https://api.mfapi.in/mf/{code}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            print(f"⚠ API error for {code}: Status {r.status_code}")
            return pd.DataFrame(columns=["date", "nav"])

        data = r.json()
        if "data" not in data:
            return pd.DataFrame(columns=["date", "nav"])

        raw = data["data"]
        if not raw:
            return pd.DataFrame(columns=["date", "nav"])

        df = pd.DataFrame(raw)

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

        df = df.dropna(subset=["date", "nav"])
        df = df.sort_values("date")

        return df[["date", "nav"]]

    except Exception as e:
        print(f"⚠ Exception while loading NAV for {code}: {e}")
        return pd.DataFrame(columns=["date", "nav"])


# -----------------------------------------------------------
# ADD-ON: Get closest available NAV (weekend / holiday safe)
# -----------------------------------------------------------
def get_latest_available_nav(history, target_date=None):
    """
    Returns (nav_date, nav) for the closest previous available NAV
    """
    if history.empty:
        return None, np.nan

    if target_date is None:
        target_date = dt.datetime.today()

    eligible = history[history["date"] <= target_date]
    if eligible.empty:
        return None, np.nan

    row = eligible.iloc[-1]
    return row["date"], row["nav"]


# -----------------------------------------------------------
# Load Master Fund List
# -----------------------------------------------------------
def load_master():
    try:
        df = pd.read_csv(MASTER_FILE)
        df = df.drop_duplicates(subset=["Scheme Code"])
        return df
    except Exception as e:
        print(f"❌ Cannot load master list: {e}")
        return pd.DataFrame(columns=["Scheme Code", "Scheme Name", "Scheme Category"])


# -----------------------------------------------------------
# Load Portfolio
# -----------------------------------------------------------
def load_portfolio():
    try:
        df = pd.read_csv(PORTFOLIO_FILE)
        return df
    except Exception as e:
        print(f"❌ Cannot load portfolio: {e}")
        return pd.DataFrame(columns=["Scheme Code", "Scheme Name", "Units"])


# -----------------------------------------------------------
# Evaluate returns for 1W–5Y (already weekend-safe)
# -----------------------------------------------------------
def compute_returns(history):
    if history.empty or len(history) < 5:
        return {"1W": np.nan, "1M": np.nan, "3M": np.nan,
                "6M": np.nan, "1Y": np.nan, "3Y": np.nan, "5Y": np.nan}

    history = history.sort_values("date")
    latest_nav = history["nav"].iloc[-1]
    latest_date = history["date"].iloc[-1]

    def get_return(days):
        cutoff = latest_date - dt.timedelta(days=days)
        df_cut = history[history["date"] <= cutoff]
        if df_cut.empty:
            return np.nan
        old_nav = df_cut["nav"].iloc[-1]
        return ((latest_nav - old_nav) / old_nav) * 100 if old_nav > 0 else np.nan

    return {
        "1W": get_return(7),
        "1M": get_return(30),
        "3M": get_return(90),
        "6M": get_return(180),
        "1Y": get_return(365),
        "3Y": get_return(1095),
        "5Y": get_return(1825)
    }


# -----------------------------------------------------------
# Build MF Grid for all Direct Funds in portfolio
# -----------------------------------------------------------
def build_grid(master, portfolio):
    output = []

    for _, row in portfolio.iterrows():
        code = row["Scheme Code"]
        name = row["Scheme Name"]

        print(f"→ Processing {name} [{code}]")

        history = load_nav_history(code)
        if history.empty:
            print(f"⚠ No NAV data found for {code}")
            continue

        nav_date, latest_nav = get_latest_available_nav(history)
        returns = compute_returns(history)

        output.append({
            "Scheme Code": code,
            "Scheme Name": name,
            "NAV Date (Effective)": nav_date.date() if nav_date is not None else None,
            "Latest NAV": latest_nav,
            **returns
        })

    return pd.DataFrame(output)

def build_portfolio_view(grid_df, portfolio_df):
    pf = pd.merge(
        portfolio_df,
        grid_df,
        on=["Scheme Code", "Scheme Name"],
        how="left"
    )

    # Compute purchase value safely
    pf["Total Purchase Value"] = pf["Units"] * pf["Purchase NAV"]

    pf["Current Value"] = pf["Units"] * pf["Latest NAV"]

    pf["% Deviation"] = (
        (pf["Current Value"] - pf["Total Purchase Value"])
        / pf["Total Purchase Value"]
    ) * 100

    return pf

# -----------------------------------------------------------
# Save Excel
# -----------------------------------------------------------
def save_grid(grid_df, portfolio_df):
    print("### generate_grid.py save_grid() CALLED ###")
    try:
        portfolio_view = build_portfolio_view(grid_df, portfolio_df)

        with pd.ExcelWriter(OUTPUT_GRID_FILE, engine="xlsxwriter") as writer:
            grid_df.to_excel(writer, index=False, sheet_name="MF Grid")
            portfolio_view.to_excel(writer, index=False, sheet_name="My Portfolio")

        print(f"✅ Grid saved to {OUTPUT_GRID_FILE}")
    except Exception as e:
        print(f"❌ Error saving Excel: {e}")
# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def main():
    print("\n=== Loading Master Fund List ===")
    master = load_master()
    print(f"Master list loaded: {len(master)} funds")

    print("\n=== Loading My Portfolio ===")
    portfolio = load_portfolio()
    print(f"Portfolio loaded: {len(portfolio)} schemes")

    if portfolio.empty:
        print("⚠ Portfolio empty. Nothing to process.")
        return

    print("\n=== Building Grid ===")
    grid = build_grid(master, portfolio)

    print("\n=== Saving Output ===")
    save_grid(grid, portfolio)

    print("\n🎉 DONE — MF Grid + Portfolio processing complete!")


if __name__ == "__main__":
    main()
