# sector_peer.py
"""
Sector-wise Peer Comparison Engine
----------------------------------
Enhances the dataframe with:
- Sector Avg Return (1Y)
- Sector Rank (1Y)
- Sector Quartile (1Y)
- Sector Performance Tag (1Y)
- Sector Return Deviation (1Y)

Ranking is based on 1Y return.
"""

import pandas as pd
import numpy as np

RETURN_COL = "%Return 1Y"

def compute_sector_peer_ranking(df):
    """
    Adds sector-level peer comparison fields.
    """

    df["Sector Avg Return (1Y)"] = np.nan
    df["Sector Rank (1Y)"] = np.nan
    df["Sector Return Deviation (1Y)"] = np.nan
    df["Sector Quartile (1Y)"] = ""
    df["Sector Performance Tag (1Y)"] = ""

    for sector, group in df.groupby("Sector Theme"):
        idx = group.index
        valid_returns = group[RETURN_COL].dropna()

        if valid_returns.empty:
            continue

        # Ranking: highest return = rank 1
        ranks = valid_returns.rank(ascending=False, method="min")
        df.loc[valid_returns.index, "Sector Rank (1Y)"] = ranks

        # Calculate sector average
        mean_ret = valid_returns.mean()
        df.loc[idx, "Sector Avg Return (1Y)"] = mean_ret

        # Deviation from sector mean
        df.loc[valid_returns.index, "Sector Return Deviation (1Y)"] = (
            valid_returns - mean_ret
        )

        # Quartiles
        q1 = valid_returns.quantile(0.25)
        q2 = valid_returns.quantile(0.50)
        q3 = valid_returns.quantile(0.75)

        for i, v in valid_returns.items():
            if v >= q3:
                df.loc[i, "Sector Quartile (1Y)"] = "Top Quartile"
                df.loc[i, "Sector Performance Tag (1Y)"] = "Sector Leader"
            elif v >= q2:
                df.loc[i, "Sector Quartile (1Y)"] = "Second Quartile"
                df.loc[i, "Sector Performance Tag (1Y)"] = "Above Sector Avg"
            elif v >= q1:
                df.loc[i, "Sector Quartile (1Y)"] = "Third Quartile"
                df.loc[i, "Sector Performance Tag (1Y)"] = "Below Sector Avg"
            else:
                df.loc[i, "Sector Quartile (1Y)"] = "Bottom Quartile"
                df.loc[i, "Sector Performance Tag (1Y)"] = "Sector Laggard"

    return df
