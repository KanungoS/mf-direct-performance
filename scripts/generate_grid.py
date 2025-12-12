import os
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# -------------------------------------------------------------
# CONFIG
# -------------------------------------------------------------
MF_MASTER_URL = (
    "https://api.mfapi.in/mf"   # Master list of all funds
)

PORTFOLIO_FILE = "data/my_portfolio.csv"
GRID_OUTPUT_FILE = "data/mf_direct_grid.xlsx"
GRID_CSV_FILE = "data/mf_direct_grid.csv"

# -------------------------------------------------------------
# LOAD MASTER FUND LIST
# -------------------------------------------------------------
def load_master_list():
    r = requests.get(MF_MASTER_URL)
    if r.status_code != 200:
        raise Exception("Failed to fetch MF master list")

    df = pd.DataFrame(r.json())
    df.rename(columns={"schemeCode": "Scheme Code", "schemeName": "Scheme Name"}, inplace=True)

    # Clean formats
    df["Scheme Code"] = df["Scheme Code"].astype(str).str.strip()
    df["Scheme Name"] = df["Scheme Name"].astype(str).str.strip()
    
    return df


# -------------------------------------------------------------
# LOAD NAV HISTORY FOR EACH FUND
# -------------------------------------------------------------
def load_nav_history(code):
    url = f"https://api.mfapi.in/mf/{code}"
    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()
    if "data" not in data:
        return None

    df = pd.DataFrame(data["data"])
    df.rename(columns={"nav": "NAV"}, inplace=True)

    # Clean date / NAV
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["NAV"] = pd.to_numeric(df["NAV"], errors="coerce")

    df = df.dropna(subset=["date", "NAV"])
    df = df.sort_values("date").reset_index(drop=True)

    return df


# -------------------------------------------------------------
# DERIVE CATEGORY (safe fallback)
# -------------------------------------------------------------
def safe_category_lookup(master_df, code):
    code = str(code).strip()

    subset = master_df.loc[master_df["Scheme Code"] == code]

    if subset.empty:
        return "Unknown"

    # Priority if category exists:
    if "schemeCategory" in subset.columns:
        cat = subset["schemeCategory"].astype(str).str.strip().iloc[0]
        return cat if cat not in ["", "nan", "None"] else "Unknown"

    return "Unknown"


# -------------------------------------------------------------
# MAIN PROCESSING ENGINE
# -------------------------------------------------------------
def main():
    print("\n=== Loading Master Fund List ===")
    master_df = load_master_list()

    print("Master list loaded:", len(master_df), "funds")

    print("\n=== Loading My Portfolio ===")
    pf = pd.read_csv(PORTFOLIO_FILE)

    # Clean user portfolio
    pf["Scheme Code"] = pf["Scheme Code"].astype(str).str.strip()
    pf["Scheme Name"] = pf["Scheme Name"].astype(str).str.strip()

    results = []

    # PROCESS EACH FUND
    for idx, row in pf.iterrows():
        code = str(row["Scheme Code"]).strip()
        print(f"\n→ Processing {row['Scheme Name']}  [{code}]")

        # Get category safely
        category = safe_category_lookup(master_df, code)

        # Load NAV history
        history = load_nav_history(code)
        if history is None or history.empty:
            print("⚠ NAV history missing. Skipping.")
            results.append({
                "Scheme Code": code,
                "Scheme Name": row["Scheme Name"],
                "Category": category,
                "Latest NAV": np.nan,
                "% Deviation": np.nan
            })
            continue

        # Latest NAV
        latest_nav = history["NAV"].iloc[-1]

        # One-month-ago NAV (30 days)
        history["date"] = pd.to_datetime(history["date"])
        cutoff = history["date"].max() - pd.Timedelta(days=30)

        past_df = history.loc[history["date"] <= cutoff]
        if not past_df.empty:
            past_nav = past_df["NAV"].iloc[-1]
        else:
            past_nav = np.nan

        # % Deviation
        deviation = np.nan
        if pd.notna(past_nav):
            deviation = ((latest_nav - past_nav) / past_nav) * 100

        results.append({
            "Scheme Code": code,
            "Scheme Name": row["Scheme Name"],
            "Category": category,
            "Latest NAV": round(latest_nav, 2),
            "NAV (30 days ago)": round(past_nav, 2) if pd.notna(past_nav) else np.nan,
            "% Deviation": round(deviation, 2) if pd.notna(deviation) else np.nan
        })

    # Convert to dataframe
    grid = pd.DataFrame(results)

    print("\n=== Saving Output Files ===")

    grid.to_csv(GRID_CSV_FILE, index=False)
    grid.to_excel(GRID_OUTPUT_FILE, index=False)

    print("✔ Grid saved to:", GRID_OUTPUT_FILE)
    print("✔ CSV saved to:", GRID_CSV_FILE)
    print("\n=== Completed Successfully ===")


# -------------------------------------------------------------
if __name__ == "__main__":
    main()
