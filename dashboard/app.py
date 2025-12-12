import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import base64

st.set_page_config(page_title="MF Direct Performance Dashboard", layout="wide")

RAW_CSV_URL = "https://raw.githubusercontent.com/KanungoS/mf-direct-performance/main/data/mf_direct_grid.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(RAW_CSV_URL)
    return df

df = load_data()

# ---------------------------
# Sidebar
# ---------------------------
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/Bar_chart_icon.svg/1024px-Bar_chart_icon.svg.png",
    width=80
)

st.sidebar.title("🔍 Dashboard Filters")

amc_filter = st.sidebar.multiselect("AMC", sorted(df["AMC"].unique()))
cat_filter = st.sidebar.multiselect("Category", sorted(df["Scheme Category"].unique()))
sector_filter = st.sidebar.multiselect("Sector Theme", sorted(df["Sector Theme"].unique()))

filtered = df.copy()

if amc_filter:
    filtered = filtered[filtered["AMC"].isin(amc_filter)]
if cat_filter:
    filtered = filtered[filtered["Scheme Category"].isin(cat_filter)]
if sector_filter:
    filtered = filtered[filtered["Sector Theme"].isin(sector_filter)]

# ---------------------------
# Navigation Tabs
# ---------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 MF Grid",
    "🔥 Top 10",
    "📈 Rolling Returns",
    "🏆 Benchmark Comparison",
    "📚 Category Explorer",
    "💰 SIP Calculator"
])

# ===========================================================
# TAB 1 — COMPLETE GRID
# ===========================================================
with tab1:
    st.header("📊 Complete Mutual Fund Grid")
    st.write("Auto-updated daily at 8:30 AM IST")

    st.dataframe(filtered, use_container_width=True)

    # Download button
    csv_bytes = filtered.to_csv(index=False).encode()
    st.download_button("⬇️ Download Filtered CSV", data=csv_bytes, file_name="filtered_mf.csv")

# ===========================================================
# TAB 2 — TOP 10s
# ===========================================================
with tab2:
    st.header("🔥 Top 10 Fund Views")

    cols = st.columns(2)

    # 1M
    with cols[0]:
        top_1m = df.sort_values("Return 1M", ascending=False).head(10)
        st.subheader("📈 Best 1M Performers")
        st.dataframe(top_1m)

    # 3M
    with cols[1]:
        top_3m = df.sort_values("Return 3M", ascending=False).head(10)
        st.subheader("📈 Best 3M Performers")
        st.dataframe(top_3m)

    # 1Y consistency
    st.subheader("🏆 Best 1Y Performers")
    st.dataframe(df.sort_values("Return 1Y", ascending=False).head(10))

    # Low volatility (using StdDev)
    st.subheader("🧊 Low Volatility Schemes")
    low_vol = df.sort_values("StdDev 1Y", ascending=True).head(10)
    st.dataframe(low_vol)

    # Category Leaders
    st.subheader("🌟 Category Leaders (Top Quartile)")
    cat_leaders = df[df["Quartile (1Y)"] == "Top Quartile"]
    st.dataframe(cat_leaders.head(20))

# ===========================================================
# TAB 3 — ROLLING RETURNS
# ===========================================================
with tab3:
    st.header("📈 Rolling Return Charts")

    scheme = st.selectbox("Select Scheme", df["Scheme Name"].unique())

    # Load NAV history dynamically
    @st.cache_data
    def get_nav_history(code):
        url = f"https://api.mfapi.in/mf/{code}"
        js = requests.get(url).json()
        data = js.get("data", [])
        hist = pd.DataFrame(data)
        hist["date"] = pd.to_datetime(hist["date"])
        hist["nav"] = hist["nav"].astype(float)
        return hist.sort_values("date")

    code = df[df["Scheme Name"] == scheme]["Scheme Code"].iloc[0]
    nav = get_nav_history(code)

    nav["RR_1Y"] = nav["nav"].pct_change(365) * 100
    nav["RR_3Y"] = nav["nav"].pct_change(365 * 3) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=nav["date"], y=nav["RR_1Y"], name="1Y Rolling Return", mode="lines"))
    fig.add_trace(go.Scatter(x=nav["date"], y=nav["RR_3Y"], name="3Y Rolling Return", mode="lines"))

    fig.update_layout(height=450, title="Rolling Returns")
    st.plotly_chart(fig, use_container_width=True)

# ===========================================================
# TAB 4 — BENCHMARK
# ===========================================================
with tab4:
    st.header("🏆 Performance vs Benchmark")

    scheme = st.selectbox("Select Scheme for Benchmark Compare", df["Scheme Name"].unique(), key="bench")

    code = df[df["Scheme Name"] == scheme]["Scheme Code"].iloc[0]
    nav = get_nav_history(code)

    # Load NIFTY50 index from Yahoo Finance API (public)
    @st.cache_data
    def get_index(symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
        js = requests.get(url).json()
        timestamps = js["chart"]["result"][0]["timestamp"]
        prices = js["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        df_idx = pd.DataFrame({"date": pd.to_datetime(timestamps, unit="s"), "close": prices})
        return df_idx

    nifty = get_index("^NSEI")

    # Plot
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=nav["date"], y=nav["nav"], name=scheme, mode="lines"))
    fig2.add_trace(go.Scatter(x=nifty["date"], y=nifty["close"], name="NIFTY 50", mode="lines"))
    fig2.update_layout(height=450, title="Performance vs Benchmark")
    st.plotly_chart(fig2, use_container_width=True)

# ===========================================================
# TAB 5 — CATEGORY EXPLORER
# ===========================================================
with tab5:
    st.header("📚 Interactive Category Explorer")

    cat_choice = st.selectbox("Select Category", sorted(df["Scheme Category"].unique()))

    sub = df[df["Scheme Category"] == cat_choice]

    fig3 = px.scatter(
        sub,
        x="StdDev 1Y",
        y="Return 1Y",
        color="AMC",
        hover_name="Scheme Name",
        title="Risk vs Return (1Y)",
        size="Return 1Y",
    )
    st.plotly_chart(fig3, use_container_width=True)

# ===========================================================
# TAB 6 — SIP CALCULATOR
# ===========================================================
with tab6:
    st.header("💰 SIP Calculator & Return Simulator")

    sip_monthly = st.number_input("Monthly SIP Amount", value=5000)
    sip_years = st.slider("Duration (Years)", 1, 30, 10)
    exp_return = st.slider("Expected CAGR (%)", 5, 20, 12)

    months = sip_years * 12
    monthly_rate = exp_return / 12 / 100

    fv = 0
    for i in range(months):
        fv = (fv + sip_monthly) * (1 + monthly_rate)

    st.subheader(f"Future Value: ₹ {fv:,.0f}")

    st.info("This uses monthly compounding of expected CAGR.")

# -----------------------------
# Screenshot Button
# -----------------------------
st.markdown("""
### 📸 Screenshot
You may use the Streamlit built-in "Save Screenshot" option in the menu (top-right). 
""")
