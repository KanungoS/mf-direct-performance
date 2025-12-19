import pandas as pd
import sys

def fail(msg):
    print(f"❌ VALIDATION FAILED: {msg}")
    sys.exit(1)


def validate_core():
    df = pd.read_csv("data/mf_core_direct_openended.csv")
    if df.empty:
        fail("Core MF file empty")

    forbidden = ["etf", "fof", "close", "interval", "idf", "fmp"]
    for f in forbidden:
        if df["SchemeName"].str.lower().str.contains(f).any():
            fail(f"Forbidden scheme found in core: {f}")


def validate_returns():
    df = pd.read_csv("data/mf_core_with_returns.csv")
    if not any(c.startswith("Return_") for c in df.columns):
        fail("Return columns missing")


def validate_portfolio():
    df = pd.read_csv("data/my_portfolio.csv")
    if "Current_Value" not in df.columns:
        fail("Portfolio valuation missing")


def run():
    validate_core()
    validate_returns()
    validate_portfolio()
    print("✅ ALL VALIDATIONS PASSED")


if __name__ == "__main__":
    run()
