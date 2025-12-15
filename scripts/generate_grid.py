import pandas as pd
import requests
from datetime import datetime
from io import StringIO

PORTFOLIO_FILE = "data/my_portfolio.csv"


def fetch_amfi_nav():
    """
    Fetch AMFI NAV data and return a dict:
    { scheme_code: (nav, nav_date) }
    """
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    nav_map = {}

    for line in response.text.splitlines():
        if ";" not in line:
            continue

        parts = line.split(";")
        if len(parts) < 6:
            continue

        try:
            scheme_code = int(parts[0])
            nav = float(parts[4])
            nav_date = datetime.strptime(parts[5], "%d-%b-%Y").date()
            nav_map[scheme_code] = (nav, nav_date)
        except Exception:
            continue

    return nav_map


def main():
    # Load portfolio
    df = pd.read_csv(PORTFOLIO_FILE)

    # Normalize column names (safety)
    df.columns = [c.strip() for c in df.columns]

    # Fetch NAV master
    nav_map = fetch_amfi_nav()

    # Ensure required columns exist
    for col in ["Current NAV", "Current Date", "Current Value", "% Deviation"]:
        if col not in df.columns:
            df[col] = ""

    # Update row by row
    for i, row in df.iterrows():
        try:
            scheme_code = int(row["Scheme Code"])
        except Exception:
            continue

        if scheme_code not in nav_map:
            continue

        nav, nav_date = nav_map[scheme_code]

        try:
            units = float(row["Units"])
            invested = float(row["Total Purchase Value"])
        except Exception:
            continue

        current_value = units * nav
        deviation = ((current_value - invested) / invested) * 100

        df.at[i, "Current NAV"] = round(nav, 4)
        df.at[i, "Current Date"] = nav_date.strftime("%d-%m-%Y")
        df.at[i, "Current Value"] = round(current_value, 2)
        df.at[i, "% Deviation"] = round(deviation, 2)

    # Save back to SAME file (no duplicate file)
    df.to_csv(PORTFOLIO_FILE, index=False)
    print("Portfolio updated successfully")


if __name__ == "__main__":
    main()
