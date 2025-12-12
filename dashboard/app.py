import streamlit as st
import pandas as pd
import plotly.express as px
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "mf_direct_grid.csv")

st.set_page_config(page_title="MF Direct Performance Dashboard", layout="wide")

@st.cache_data
def load_data():
    return pd.read_csv(DATA_FILE)

df = load_data()

st.title("📊 Mutual Fund Performance Dashboard (Direct Plans)")

# Sidebar Filters
st.sidebar.header("Filters")

amc = st.sidebar.multiselect("Select AMC", sorted(df["AMC"].dropna().unique()))
category = st.sidebar.multiselect("Select Category", sorted(df["Scheme Category"].unique()))
sector = st.sidebar.multiselect("Select Sector Theme", sorted(df["Sector Theme"].unique()))

filtered = df.copy()
if amc:
    filtered = filtered[filtered["AMC"].isin(amc)]
if category:
    filtered = filtered[filtered["Scheme Category"].isin(category)]
if sector:
    filtered = filtered[filtered["Sector Theme"].isin(sector)]

st.subheader(f"Filtered Funds ({len(filtered)})")
st.dataframe(filtered, height=400)

# Performance Distribution Chart
st.subheader("Performance Distribution (1Y Return)")
fig = px.histogram(filtered, x="%Return 1Y", nbins=30, title="Distribution of 1Y Returns")
st.plotly_chart(fig, use_container_width=True)

# Sector Leaders & Laggards
st.subheader("Sector Leaders & Laggards (1Y)")

leaders = filtered[filtered["Sector Performance Tag (1Y)"] == "Sector Leader"]
laggards = filtered[filtered["Sector Performance Tag (1Y)"] == "Sector Laggard"]

col1, col2 = st.columns(2)

with col1:
    st.write("### 🟦 Sector Leaders")
    st.dataframe(leaders)

with col2:
    st.write("### 🔴 Sector Laggards")
    st.dataframe(laggards)

# NAV Trend Chart for a selected fund
st.subheader("NAV Trend")

fund = st.selectbox("Select a Fund for NAV Chart", filtered["Scheme Name"].unique())

fund_code = filtered[filtered["Scheme Name"] == fund]["Scheme Code"].iloc[0]
nav_file = os.path.join(BASE_DIR, "data", "cache", f"{fund_code}.json")

if os.path.exists(nav_file):
    nav_json = pd.read_json(nav_file)
    nav_data = pd.DataFrame(nav_json["data"].tolist())
    nav_data["date"] = pd.to_datetime(nav_data["date"], dayfirst=True)
    nav_data["nav"] = nav_data["nav"].astype(float)

    fig2 = px.line(nav_data, x="date", y="nav", title=f"NAV Trend — {fund}")
    st.plotly_chart(fig2, use_container_width=True)

else:
    st.warning("NAV history not available yet.")

# Download Section
st.subheader("Download Data")
st.download_button("Download CSV", df.to_csv(index=False), "mf_direct_performance.csv")
