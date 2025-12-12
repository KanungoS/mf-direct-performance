# peer_ranking.py
"""
Category-wise Peer Ranking Engine
---------------------------------
Adds:
- Category Rank (1Y)
- Category Size
- Quartile (1Y)
- Performance Tag (1Y)
- Category Avg Return (1Y)
- Category Return Deviation (1Y)

Ranking is based strictly on 1Y return (industry standard).
"""

import pandas as pd
import numpy as np

RETURN_COL = "%Return 1Y"

def compute_category_peer_ranking(df):
    """
    Input: df_final BEFORE sorting
    Output: df_final with peer ranking columns added
    """

    # Initialize columns
    df["Category Rank (1Y)"] = np.nan
    df["Category Size"] = np.nan
    df["Quartile (1Y)"] = ""
    df["Performance Tag (1Y)"] = ""
    df["Category Avg Return (1Y)"] = np.nan
    df["Category Return Deviation (1Y)"] = np.nan

    # Group funds by category
    for cat, group in df.groupby("Scheme Category"):
        idx = group.index
        valid_returns = group[RETURN_COL].dropna()

        if valid_returns.empty:
            continue

        # Ranking: highest return = rank 1
        ranks = valid_returns.rank(ascending=False, method="min")
        df.loc[valid_returns.index, "Category Rank (1Y)"] = ranks
        df.loc[idx, "Category Size"] = len(group)

        # Quartiles
        q1 = valid_returns.quantile(0.25)
        q2 = valid_returns.quantile(0.50)
        q3 = valid_returns.quantile(0.75)

        for i, val in valid_returns.items():
            if val >= q3:
                df.loc[i, "Quartile (1Y)"] = "Top Quartile"
                df.loc[i, "Performance Tag (1Y)"] = "Outperformer"
            elif val >= q2:
                df.loc[i, "Quartile (1Y)"] = "Second Quartile"
                df.loc[i, "Performance Tag (1Y)"] = "Above Average"
            elif val >= q1:
                df.loc[i, "Quartile (1Y)"] = "Third Quartile"
                df.loc[i, "Performance Tag (1Y)"] = "Below Average"
            else:
                df.loc[i, "Quartile (1Y)"] = "Bottom Quartile"
                df.loc[i, "Performance Tag (1Y)"] = "Underperformer"

        # Category average
        mean_ret = valid_returns.mean()
        df.loc[idx, "Category Avg Return (1Y)"] = mean_ret

        # Deviation from category mean
        df.loc[valid_returns.index, "Category Return Deviation (1Y)"] = (
            valid_returns - mean_ret
        )

    return df
