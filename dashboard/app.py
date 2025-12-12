import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import base64

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="MF Performance Dashboard",
    layout="wide"
)

RAW_MF_URL = "https://raw.githubusercontent.com/KanungoS/mf-direct-performance/main/data/mf_direct_grid.csv"
RAW_PORT_URL = "https://raw.githubusercontent.com/KanungoS/mf-direct-performance/main/data/my_portfolio.csv"

# ============================================================
# LOAD DATA
# ============================================================
@st.cache_data(ttl=3600)
def load_main_data():
    df = pd.read_csv(RAW_MF_URL)
    return df

@st.cache_data(ttl=3600)
def load_portfolio():
    try:
        df = pd.read_csv(RAW_PORT_URL)
    except:
        df = pd.DataFrame(columns=[
            "Scheme Code","Scheme Name","Units","Purchase NAV","Date of Purchase",
            "Total Purchase Value","Current NAV","Current Value","% Deviation",
            "Will Exit Load Apply","Exit Load %"
        ])
    return df

mf = load_main_data()
portfolio = load_portfolio()

# Convert numeric fields
for col in mf.columns:
    if "NAV" in col or "Return" in col or "Volatility" in col or "AI Fund Score" in col:
        mf[col] = pd.to_numeric(mf[col], errors="coerce")

# ============================================================
# SIDEBAR FILTERS
# ============================================================
st.sidebar.title("🔍 Filters")

f_amc = st.sidebar.multiselect("AMC", sorted(mf["AMC"].unique()))
f_cat = st.sidebar.multiselect("Category", sorted(mf["Scheme Category"].unique()))
f_sec = st.sidebar.multiselect("Sector Theme", sorted(mf["Sector Theme"].unique()))

filtered = mf.copy()

if f_amc:
    filtered = filtered[filtered["AMC"].isin(f_amc)]
if f_cat:
    filtered = filtered[filtered["Scheme Category"].isin(f_cat)]
if f_sec:
    filtered = filtered[filtered["Sector Theme"].isin(f_sec)]

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 MF Grid",
    "🔥 Top 10",
    "🌡 Sector Heatmap",
    "📈 Rolling Returns",
    "🏆 Benchmark Comparison",
    "📚 Category Explorer",
    "💼 My Portfolio Tracker"
])

# ============================================================
# TAB 1 — MAIN GRID
# ============================================================
with tab1:
    st.header("📊 Mutual Fund Performance Grid")
    st.caption("Auto-updated every day at 8:30 AM IST")

    st.dataframe(filtered, use_container_width=True)

    st.download_button(
        "⬇️ Download Filtered CSV",
        filtered.to_csv(index=False).encode(),
        "filtered_mf.csv"
    )

# ============================================================
# TAB 2 — TOP 10
# ============================================================
with tab2:
    st.header("🔥 Top 10 Funds")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🚀 Best 1M Performers")
        st.dataframe(mf.nlargest(10, "NAV 1M")[["Scheme Name","AMC","NAV 1M"]])

    with col2:
        st.subheader("🚀 Best 3M Performers")
        st.dataframe(mf.nlargest(10, "NAV 3M")[["Scheme Name","AMC","NAV 3M"]])

    st.subheader("🏆 Best 1Y Performers")
    st.dataframe(mf.nlargest(10, "NAV 1Y")[["Scheme Name","AMC","NAV 1Y"]])

    st.subheader("🧊 Low Volatility Funds")
    st.dataframe(mf.nsmallest(10, "Volatility (StdDev 1Y)")[["Scheme Name","Volatility (StdDev 1Y)"]])

    st.subheader("🌟 Top Quartile Category Leaders")
    leaders = mf[mf["Quartile (1Y)"] == "Top Quartile"].head(20)
    st.dataframe(leaders)

# ============================================================
# TAB 3 — SECTOR HEATMAP
# ============================================================
with tab3:
    st.header("🌡 Sector Heatmap (Return vs Volatility)")
    
    heat = mf[["Sector Theme","NAV 1Y","Volatility (StdDev 1Y)"]].dropna()
    heat = heat.groupby("Sector Theme").mean().reset_index()

    fig = px.scatter(
        heat,
        x="Volatility (StdDev 1Y)",
        y="NAV 1Y",
        color="Sector Theme",
        size="NAV 1Y",
        hover_name="Sector Theme",
        title="Sector Performance Heatmap"
    )
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 4 — ROLLING RETURNS
# ============================================================
with tab4:
    st.header("📈 Rolling Returns (1Y & 3Y)")

    scheme = st.selectbox("Choose Scheme", mf["Scheme Name"].unique())

    code = mf[mf["Scheme Name"] == scheme]["Scheme Code"].iloc[0]

    @st.cache_data
    def get_nav(code):
        url = f"https://api.mfapi.in/mf/{code}"
        js = requests.get(url).json()
        df = pd.DataFrame(js["data"])
        df["date"] = pd.to_datetime(df["date"])
        df["nav"] = df["nav"].astype(float)
        df = df.sort_values("date")
        return df

    df = get_nav(code)

    df["RR_1Y"] = df["nav"].pct_change(365) * 100
    df["RR_3Y"] = df["nav"].pct_change(365*3) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["RR_1Y"], name="Rolling 1Y", mode="lines"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["RR_3Y"], name="Rolling 3Y", mode="lines"))
    fig.update_layout(title="Rolling Returns", height=450)

    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# TAB 5 — BENCHMARK COMPARISON
# ============================================================
with tab5:
    st.header("🏆 Benchmark Comparison")

    scheme = st.selectbox("Select Fund for Benchmark", mf["Scheme Name"].unique(), key="bench")

    code = mf[mf["Scheme Name"] == scheme]["Scheme Code"].iloc[0]
    df = get_nav(code)

    @st.cache_data
    def get_index(symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5y&interval=1d"
        js = requests.get(url).json()
        timestamps = js["chart"]["result"][0]["timestamp"]
        close = js["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        df = pd.DataFrame({
            "date": pd.to_datetime(timestamps, unit="s"),
            "close": close
        })
        return df

    nifty = get_index("^NSEI")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=df["date"], y=df["nav"], name=scheme))
    fig2.add_trace(go.Scatter(x=nifty["date"], y=nifty["close"], name="NIFTY 50"))
    fig2.update_layout(title="Fund vs Benchmark", height=450)

    st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# TAB 6 — CATEGORY EXPLORER
# ============================================================
with tab6:
    st.header("📚 Category Explorer")

    cat = st.selectbox("Select Category", sorted(mf["Scheme Category"].unique()))

    sub = mf[mf["Scheme Category"] == cat]

    fig3 = px.scatter(
        sub,
        x="Volatility (StdDev 1Y)",
        y="NAV 1Y",
        size="NAV 1Y",
        color="AMC",
        hover_name="Scheme Name",
        title=f"Risk vs Return ({cat})"
    )
    st.plotly_chart(fig3, use_container_width=True)

# ============================================================
# TAB 7 — PORTFOLIO TRACKER
# ============================================================
with tab7:
    st.header("💼 My Portfolio Tracker")

    if len(portfolio) == 0:
        st.warning("Your portfolio file is empty. Add holdings in data/my_portfolio.csv")
    else:
        st.subheader("📈 Portfolio Holdings")
        st.dataframe(portfolio, use_container_width=True)

        # Portfolio Summary
        tot_cost = portfolio["Total Purchase Value"].sum()
        tot_curr = portfolio["Current Value"].sum()
        pnl = tot_curr - tot_cost
        pnl_pct = (pnl / tot_cost) * 100 if tot_cost else 0

        st.metric("Total Investment Value", f"₹{tot_cost:,.0f}")
        st.metric("Current Portfolio Value", f"₹{tot_curr:,.0f}")
        st.metric("Net Gain/Loss", f"₹{pnl:,.0f} ({pnl_pct:.2f}%)")

        # Exit Load Alerts
        drop_alerts = portfolio[portfolio["% Deviation"] <= -5]

        if len(drop_alerts):
            st.error("⚠ ALERT: Some funds have dropped more than 5%!")
            st.dataframe(drop_alerts[["Scheme Name","% Deviation"]])

        # Pie chart – Sector Allocation
        st.subheader("🔍 Sector Allocation")
        merged = portfolio.merge(mf[["Scheme Code","Sector Theme"]], on="Scheme Code", how="left")
        alloc = merged.groupby("Sector Theme")["Current Value"].sum().reset_index()

        fig4 = px.pie(alloc, names="Sector Theme", values="Current Value", title="Sector Allocation")
        st.plotly_chart(fig4, use_container_width=True)

        # Download portfolio
        st.download_button(
            "⬇️ Download Portfolio CSV",
            portfolio.to_csv(index=False).encode(),
            "portfolio_report.csv"
        )

st.markdown("---")
st.caption("Dashboard auto-updated everyday at 8:30 AM IST")
