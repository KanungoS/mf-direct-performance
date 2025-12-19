# --- ADD AFTER RETURNS ARE CALCULATED ---

# Momentum helpers
pf["Momentum_Positive"] = (
    (pf["Return_1M"] > 0) &
    (pf["Return_3M"] > 0) &
    (pf["Return_6M"] > 0)
)

pf["Momentum_Improving"] = pf["Return_1M"] > (pf["Return_3M"] / 3)

# Alerts
pf["ALERT"] = np.select(
    [
        pf["Momentum_Positive"] & pf["Momentum_Improving"],
        (pf["Exit_Load_%_Applied"] > 0) & (pf["Return_%"] < 0),
        pf["Return_%"] < 5
    ],
    [
        "INVEST MORE (if budget available)",
        "SELL",
        "WATCH"
    ],
    default="HOLD"
)
