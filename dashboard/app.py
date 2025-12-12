import streamlit as st
import pandas as pd

# =====================================================
# LOAD MF GRID FROM GITHUB (always latest version)
# =====================================================
@st.cache_data(ttl=3600)   # cache for 1 hour → faster
def load_data():
    url = "https://raw.githubusercontent.com/KanungoS/mf-direct-performance/main/data/mf_direct_grid.csv"
    df = pd.read_csv(url)

    # Ensure numeric columns stay numeric
    numeric_cols = [c for c in df.columns if "Return" in c or "Stdev" in c or "NAV" in c]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df

df = load_data()

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Mutual Fund Performance Dashboard",
    layout="wide",
)

st.title("📊 Mutual Fund Performance Dashboard")
st.caption("Auto-updated daily at 8:30 AM IST from GitHub Actions")

st.divider()

# =====================================================
# SECTION 1 — FULL GRID DISPLAY
# =====================================================
st.header("📘 Complete Mutual Fund Grid")

st.dataframe(df, use_container_width=True)

st.divider()

# =====================================================
# SECTION 2 — TOP 10 INSIGHTS
# =====================================================
st.header("🏆 Top 10 Fund Insights")

col1, col2 = st.columns(2)

# ---------- 1 MONTH MOVERS ----------
with col1:
    st.subheader("🚀 Best 1-Month Movers")
    t1 = df.sort_values("Return 1M", ascending=False).head(10)
    st.dataframe(t1, use_container_width=True)

# ---------- CONSISTENCY (3M) ----------
with col2:
    st.subheader("📈 Most Consistent (3M)")
    # “Consistency Score” = return minus volatility
    df["Consistency Score"] = df["Return 3M"] - df["Stdev 3M"]
    t2 = df.sort_values("Consistency Score", ascending=False).head(10)
    st.dataframe(t2, use_container_width=True)

# ---------- LOW VOLATILITY ----------
st.subheader("🧩 Top 10 Low-Volatility Funds")
t3 = df.sort_values("Stdev 3M", ascending=True).head(10)
st.dataframe(t3, use_container_width=True)

# ---------- CATEGORY LEADERS ----------
st.subheader("🏅 Category Leaders (Top Quartile Only)")
leaders = df[df["Quartile (1Y)"] == "Top Quartile"]
leaders = leaders.sort_values("Return 1Y", ascending=False).head(10)
st.dataframe(leaders, use_container_width=True)

st.divider()

# =====================================================
# SECTION 3 — EXPLORER (FILTER-BASED)
# =====================================================
st.header("🔍 Explore by AMC / Category / Sector")

colA, colB, colC = st.columns(3)

amc = colA.selectbox("Select AMC", ["All"] + sorted(df["AMC"].unique()))
cat = colB.selectbox("Select Category", ["All"] + sorted(df["Scheme Category"].unique()))
sector = colC.selectbox("Select Sector Theme", ["All"] + sorted(df["Sector Theme"].unique()))

filtered = df.copy()

if amc != "All":
    filtered = filtered[filtered["AMC"] == amc]

if cat != "All":
    filtered = filtered[filtered["Scheme Category"] == cat]

if sector != "All":
    filtered = filtered[filtered["Sector Theme"] == sector]

st.dataframe(filtered, use_container_width=True)

st.divider()

# =====================================================
# SECTION 4 — SCHEME LOOKUP + DETAIL VIEW
# =====================================================
st.header("📌 Scheme Lookup")

selected_scheme = st.selectbox("Select Scheme", df["Scheme Name"])

selected_row = df[df["Scheme Name"] == selected_scheme].iloc[0]

st.subheader("🔎 Scheme Details")
st.json(selected_row.to_dict())

st.success("Dashboard loaded successfully. Data auto-refreshes daily!")
