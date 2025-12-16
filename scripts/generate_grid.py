# scripts/generate_grid.py
# ------------------------------------------------------------
# Daily MF Grid + Portfolio Engine (robust, final)
# ------------------------------------------------------------

import os
import sys
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import smtplib
from email.mime.text import MIMEText
import json

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------
DATA_DIR = "data"
MASTER_LIST = os.path.join(DATA_DIR, "master_list.csv")
GRID_CSV = os.path.join(DATA_DIR, "mf_direct_grid.csv")
GRID_XLSX = os.path.join(DATA_DIR, "mf_direct_grid.xlsx")
PORTFOLIO_CSV = os.path.join(DATA_DIR, "my_portfolio.csv")

AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

IST = pytz.timezone("Asia/Kolkata")

ALERT_THRESHOLD = -5.0  # %

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def ist_now():
    return datetime.now(IST)

def safe_float(x):
    try:
        return float(x)
    except:
        return None

def fetch_amfi_nav():
    r = requests.get(AMFI_URL, timeout=60)
    r.raise_for_status()

    rows = []
    for line in r.text.splitlines():
        if ";" in line and line.count(";") >= 4:
            parts = line.split(";")
            try:
                scheme_code = int(parts[0])
                nav = float(parts[-2])
                nav_date = datetime.strptime(parts[-1], "%d-%b-%Y").date()
                rows.append((scheme_code, nav, nav_date))
            except:
                continue

    df = pd.DataFrame(rows, columns=["Scheme Code", "NAV", "NAV Date"])
    df = df.sort_values("NAV Date").groupby("Scheme Code").tail(1)
    return df

def send_email(subject, body):
    user = os.getenv("SMTP_USERNAME")
    pwd = os.getenv("GMAIL_APP_PASSWORD")
    to = os.getenv("EMAIL_TO")

    if not all([user, pwd, to]):
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(user, pwd)
        s.send_message(msg)

def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=30)

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    amfi = fetch_amfi_nav()

    # ---------------- GRID ----------------
    master = pd.read_csv(MASTER_LIST)
    grid = master.merge(amfi, how="left", left_on="Scheme Code", right_on="Scheme Code")

    grid["NAV Latest"] = grid["NAV"]
    grid["NAV Date"] = grid["NAV Date"]

    grid.drop(columns=["NAV"], inplace=True)

    grid.to_csv(GRID_CSV, index=False)
    grid.to_excel(GRID_XLSX, index=False)

    # ---------------- PORTFOLIO (OPTIONAL) ----------------
    alerts = []

    if os.path.exists(PORTFOLIO_CSV):
        pf = pd.read_csv(PORTFOLIO_CSV)

        for i, row in pf.iterrows():
            code = safe_float(row.get("Scheme Code"))
            units = safe_float(row.get("Units"))
            purchase_nav = safe_float(row.get("Purchase NAV"))
            invested = safe_float(row.get("Total Purchase Value"))

            if not all([code, units, purchase_nav, invested]):
                continue

            hit = amfi[amfi["Scheme Code"] == int(code)]
            if hit.empty:
                continue

            nav = hit.iloc[0]["NAV"]
            nav_date = hit.iloc[0]["NAV Date"]

            current_value = round(units * nav, 2)
            deviation = round(((current_value - invested) / invested) * 100, 2)

            pf.at[i, "Current NAV"] = round(nav, 4)
            pf.at[i, "Current Date"] = nav_date.strftime("%d-%m-%Y")
            pf.at[i, "Current Value"] = current_value
            pf.at[i, "% Deviation"] = deviation

            if deviation <= ALERT_THRESHOLD:
                alerts.append(
                    f"{row.get('Scheme Name')} : {deviation}%"
                )

        pf.to_csv(PORTFOLIO_CSV, index=False)

    # ---------------- ALERTS ----------------
    if alerts:
        msg = "⚠ MF Alert (<= -5%)\n\n" + "\n".join(alerts)
        send_email("MF Drop Alert", msg)
        send_telegram(msg)

# ------------------------------------------------------------
if __name__ == "__main__":
    main()
