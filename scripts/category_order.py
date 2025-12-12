# category_order.py
"""
Strict AMFI Category Ordering
-----------------------------
This file provides:
1. A globally consistent investor-friendly category order.
2. A ranking function to sort schemes accordingly.
"""

CATEGORY_ORDER = [
    # ------------------ EQUITY ------------------ #
    "Large Cap",
    "Large & Mid Cap",
    "Mid Cap",
    "Small Cap",
    "Multi Cap",
    "Flexi Cap",
    "Focused Fund",
    "Value Fund",
    "Contra Fund",
    "Dividend Yield",
    "ELSS",
    "Sectoral/Thematic",
    "Other Equity",

    # ------------------ HYBRID ------------------ #
    "Aggressive Hybrid",
    "Conservative Hybrid",
    "Balanced Advantage",
    "Dynamic Asset Allocation",
    "Multi Asset Allocation",
    "Equity Savings",
    "Arbitrage Fund",

    # ------------------ DEBT ------------------ #
    "Overnight Fund",
    "Liquid Fund",
    "Ultra Short Duration Fund",
    "Low Duration Fund",
    "Money Market Fund",
    "Short Duration Fund",
    "Medium Duration Fund",
    "Medium to Long Duration Fund",
    "Long Duration Fund",
    "Corporate Bond Fund",
    "Credit Risk Fund",
    "Floater Fund",
    "Banking & PSU Fund",
    "Gilt Fund",
    "Gilt Fund with 10 year Constant Duration",
    "Dynamic Bond Fund",
    "Other Debt",

    # ---------------- SOLUTION ORIENTED ---------------- #
    "Retirement Fund",
    "Children's Fund",

    # ---------------- OTHER SCHEMES ---------------- #
    "FoF Domestic",
    "FoF International",
    "Commodities",
    "Index Fund",
]

def category_rank(cat: str):
    """
    Returns the category's rank index for ordering.
    Unrecognized categories float to bottom.
    """
    if cat in CATEGORY_ORDER:
        return CATEGORY_ORDER.index(cat)
    return len(CATEGORY_ORDER) + 1
