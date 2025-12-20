# scripts/mf_tactical_engine.py

import pandas as pd

DATA_DIR = "data"
CORE_FILE = f"{DATA_DIR}/mf_core_direct_openended.csv"
OUTPUT_FILE = f"{DATA_DIR}/mf_tactical_watchlist.csv"


def main():
    df = pd.read_csv(CORE_FILE)

    # Tactical list = full universe (ranking / filtering later)
    df.to_csv(OUTPUT_FILE, index=False)
    print("mf_tactical_watchlist.csv created")


if __name__ == "__main__":
    main()
