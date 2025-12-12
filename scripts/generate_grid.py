import os, json, time, requests
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

from sector_mapping import detect_sector_theme
from category_order import category_rank
from peer_ranking import compute_category_peer_ranking
from sector_peer import compute_sector_peer_ranking

# =========================
# PATHS
# =========================

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

MASTER_LIST = os.path.join(DATA_DIR, "master_list.csv")
DISCONTINUED_FILE = os.path.join(DATA_DIR, "discontinued_schemes.csv")
FINAL_CSV = os.path.join(DATA_DIR, "mf_direct_grid.csv")
FINAL_XLSX = os.path.join(DATA_DIR, "mf_direct_grid.xlsx")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

MFAPI_LIST_URL = "https://api.mfapi.in/mf"
MFAPI_SCHEME_URL = "https://api.mfapi.in/mf/{}"

REQUEST_SLEEP = 0.25
HISTORY_YEARS = 5

# =========================
# HELPERS
# =========================

def fetch_json(url):
    time.sleep(REQUEST_SLEEP)
    try:
        r = requests.get(url, timeout=15)
        return r.json() if r.status_code == 200 else None
    except:
        return None


def load_master_list():
    if os.path.exists(MASTER_LIST):
        return pd.read_csv(MASTER_LIST, dtype=str)
    return pd.DataFrame(columns=["Scheme Code", "Scheme Name", "Scheme Category", "Scheme Status"])


def save_master_list(df):
    df.to_csv(MASTER_LIST, index=False)


def load_discontinued():
    if os.path.exists(DISCONTINUED_FILE):
        return pd.read_csv(DISCONTINUED_FILE, dtype=str)
    return pd.DataFrame(columns=["Scheme Code", "Scheme Name", "Date Discontinued"])


def save_discontinued(df):
    df.to_csv(DISCONTINUED_FILE, index=False)


# =========================
# FETCH DIRECT SCHEMES
# =========================

def fetch_direct_scheme_list():
    data = fetch_json(MFAPI_LIST_URL)
    if not data:
        return []
    out = []
    for s in data:
        nm = s.get("schemeName", "")
        if "direct" in nm.lower():
            out.append({
                "Scheme Code": str(s["schemeCode"]),
                "Scheme Name": nm.strip()
            })
    return out


# =========================
# CATEGORY NORMALIZATION
# =========================

def normalize_category(raw):
    if not raw:
        return "Other Equity"
    c = raw.lower()

    mapping = [
        ("large cap", "Large Cap"),
        ("large & mid", "Large & Mid Cap"),
        ("large and mid", "Large & Mid Cap"),
        ("mid cap", "Mid Cap"),
        ("small cap", "Small Cap"),
        ("multi cap", "Multi Cap"),
        ("flexi cap", "Flexi Cap"),
        ("focused", "Focused Fund"),
        ("value", "Value Fund"),
        ("contra", "Contra Fund"),
        ("dividend", "Dividend Yield"),
        ("elss", "ELSS"),
        ("tax", "ELSS"),
        ("sector", "Sectoral/Thematic"),
        ("thematic", "Sectoral/Thematic"),
        ("aggressive hybrid", "Aggressive Hybrid"),
        ("conservative hybrid", "Conservative Hybrid"),
        ("balanced advantage", "Balanced Advantage"),
        ("dynamic asset", "Balanced Advantage"),
        ("multi asset", "Multi Asset Allocation"),
        ("equity savings", "Equity Savings"),
        ("arbitrage", "Arbitrage Fund"),
        ("overnight", "Overnight Fund"),
        ("liquid", "Liquid Fund"),
        ("ultra short", "Ultra Short Duration Fund"),
        ("low duration", "Low Duration Fund"),
        ("money market", "Money Market Fund"),
        ("short duration", "Short Duration Fund"),
        ("medium duration", "Medium Duration Fund"),
        ("medium to long", "Medium to Long Duration Fund"),
        ("long duration", "Long Duration Fund"),
        ("corporate bond", "Corporate Bond Fund"),
        ("credit risk", "Credit Risk Fund"),
        ("floater", "Floater Fund"),
        ("banking & psu", "Banking & PSU Fund"),
        ("gilt fund with 10", "Gilt Fund with 10 year Constant Duration"),
        ("gilt", "Gilt Fund"),
        ("dynamic bond", "Dynamic Bond Fund"),
        ("retirement", "Retirement Fund"),
        ("children", "Children's Fund"),
        ("fund of funds", "FoF Domestic"),
        ("international", "FoF International"),
        ("gold", "Commodities"),
        ("silver", "Commodities"),
        ("commodity", "Commodities"),
        ("index", "Index Fund")
    ]

    for k, v in mapping:
        if k in c:
            return v

    return "Other Equity"


# =========================
# NAV + RETURNS
# =========================

def load_nav_history(code):
    cache_file = os.path.join(CACHE_DIR, f"{code}.json")

    if os.path.exists(cache_file):
        try:
            js = json.load(open(cache_file, "r"))
        except:
            js = {}
    else:
        js = fetch_json(MFAPI_SCHEME_URL.format(code))
        if not js:
            return pd.DataFrame(), {}
        json.dump(js, open(cache_file, "w"))

    df = pd.DataFrame(js.get("data", []))

    if df.empty:
        return pd.DataFrame(), js

    try:
        df["date"] = df["date"].apply(lambda d: parser.parse(d, dayfirst=True))
        df["nav"] = df["nav"].astype(float)
    except:
        return pd.DataFrame(), js

    df = df.sort_values("date")
    cutoff = datetime.today() - timedelta(days=365 * HISTORY_YEARS)
    df = df[df["date"] >= cutoff]

    return df, js


def nav_before(df, target):
    d = df[df["date"] <= target]
    if d.empty:
        return None
    return float(d.iloc[-1]["nav"])


def compute_returns(df):
    if df.empty:
        return {k: None for k in [
            "NAV Latest", "NAV 1D", "NAV 1W", "NAV 1M", "NAV 3M", "NAV 6M", "NAV 1Y",
            "%Return 1D", "%Return 1W", "%Return 1M", "%Return 3M", "%Return 6M", "%Return 1Y"
        ]}

    today = df["date"].max()
    latest = nav_before(df, today)

    def ret(days):
        past = nav_before(df, today - timedelta(days=days))
        if past in (None, 0):
            return None
        return (latest / past - 1) * 100

    return {
        "NAV Latest": latest,
        "NAV 1D": nav_before(df, today - timedelta(days=1)),
        "NAV 1W": nav_before(df, today - timedelta(days=7)),
        "NAV 1M": nav_before(df, today - timedelta(days=30)),
        "NAV 3M": nav_before(df, today - timedelta(days=90)),
        "NAV 6M": nav_before(df, today - timedelta(days=180)),
        "NAV 1Y": nav_before(df, today - timedelta(days=365)),
        "%Return 1D": ret(1),
        "%Return 1W": ret(7),
        "%Return 1M": ret(30),
        "%Return 3M": ret(90),
        "%Return 6M": ret(180),
        "%Return 1Y": ret(365),
    }


# =========================
# EXCEL EXPORT
# =========================

def save_excel(df):
    wb = Workbook()
    ws = wb.active
    ws.title = "Direct MF Grid"
    ws.freeze_panes = "A2"

    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    for col in ws.iter_cols(1, ws.max_column):
        col[0].font = Font(bold=True)
        ws.column_dimensions[col[0].column_letter].width = 16

    ws.auto_filter.ref = ws.dimensions

    grey = PatternFill(start_color="DDDDDD", fill_type="solid")
    yellow = PatternFill(start_color="FFF2CC", fill_type="solid")
    green = PatternFill(start_color="C6EFCE", fill_type="solid")
    lgreen = PatternFill(start_color="E2F0D9", fill_type="solid")
    lorange = PatternFill(start_color="FCE4D6", fill_type="solid")
    red = PatternFill(start_color="F8CBAD", fill_type="solid")
    blue = PatternFill(start_color="BDD7EE", fill_type="solid")
    orange = PatternFill(start_color="F8CBAD", fill_type="solid")

    qi = df.columns.get_loc("Quartile (1Y)") + 1
    si = df.columns.get_loc("Sector Performance Tag (1Y)") + 1
    di = df.columns.get_loc("Scheme Status") + 1
    ni = df.columns.get_loc("Name Changed (Yes/No)") + 1

    for r in range(2, ws.max_row + 1):

        if ws.cell(r, di).value == "Discontinued":
            for c in range(1, ws.max_column + 1):
                ws.cell(r, c).fill = grey
            continue

        if ws.cell(r, ni).value == "Yes":
            for c in range(1, ws.max_column + 1):
                ws.cell(r, c).fill = yellow

        q = ws.cell(r, qi).value
        if q == "Top Quartile":
            ws.cell(r, qi).fill = green
        elif q == "Second Quartile":
            ws.cell(r, qi).fill = lgreen
        elif q == "Third Quartile":
            ws.cell(r, qi).fill = lorange
        elif q == "Bottom Quartile":
            ws.cell(r, qi).fill = red

        s = ws.cell(r, si).value
        if s == "Sector Leader":
            ws.cell(r, si).fill = blue
        elif s == "Sector Laggard":
            ws.cell(r, si).fill = orange

    wb.save(FINAL_XLSX)


# =========================
# MAIN ENGINE
# =========================

def main():
    print("Loading master list...")
    master = load_master_list()
    discontinued = load_discontinued()

    print("Fetching Direct schemes...")
    curr = pd.DataFrame(fetch_direct_scheme_list())

    prev = set(master["Scheme Code"])
    now = set(curr["Scheme Code"])

    removed = prev - now
    added = now - prev

    # mark discontinued
    for code in removed:
        if discontinued[discontinued["Scheme Code"] == code].empty:
            old = master.loc[master["Scheme Code"] == code, "Scheme Name"].iloc[0]
            discontinued = pd.concat([
                discontinued,
                pd.DataFrame([{
                    "Scheme Code": code,
                    "Scheme Name": old,
                    "Date Discontinued": datetime.today().strftime("%Y-%m-%d")
                }])
            ], ignore_index=True)

    # add new schemes
    for code in added:
        nm = curr.loc[curr["Scheme Code"] == code, "Scheme Name"].iloc[0]
        master = pd.concat([
            master,
            pd.DataFrame([{
                "Scheme Code": code,
                "Scheme Name": nm,
                "Scheme Category": "",
                "Scheme Status": "Active"
            }])
        ], ignore_index=True)

    master["Scheme Status"] = master["Scheme Code"].apply(
        lambda c: "Discontinued" if c in removed else "Active"
    )

    rows = []
    print("Processing NAV + returns...\n")

    for i, r in master.iterrows():
        print(f" → Processing {i+1}/{len(master)}: {r['Scheme Name']} ({r['Scheme Code']})")

        code = r["Scheme Code"]
        oldname = r["Scheme Name"]

        df, js = load_nav_history(code)
        meta = js.get("meta", {})
        cat = normalize_category(meta.get("category", ""))
        amc = meta.get("fund_house", "")
        sector = detect_sector_theme(oldname)

        ret = compute_returns(df)
        name_changed = "Yes" if oldname != meta.get("scheme_name", "") else "No"

        rows.append({
            "AMC": amc,
            "Scheme Code": code,
            "Scheme Name": oldname,
            "Scheme Category": cat,
            "Sector Theme": sector,
            "Scheme Status": r["Scheme Status"],
            "Name Changed (Yes/No)": name_changed,
            **ret
        })

    df = pd.DataFrame(rows)

    df = compute_category_peer_ranking(df)
    df = compute_sector_peer_ranking(df)

    df["__cat_rank__"] = df["Scheme Category"].apply(category_rank)
    df = df.sort_values(["__cat_rank__", "AMC", "Scheme Name"]).drop(columns="__cat_rank__")

    df.to_csv(FINAL_CSV, index=False)
    save_excel(df)
    save_master_list(master)
    save_discontinued(discontinued)

    print("\nDONE ✓ Output generated.")


if __name__ == "__main__":
    main()
