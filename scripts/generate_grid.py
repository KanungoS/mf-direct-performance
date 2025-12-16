import os
import sys
import math
import requests
import pandas as pd
from datetime import datetime
from io import StringIO

# =========================================================
# CONFIG
# =========================================================
DATA_DIR = "data"
PORTFOLIO_FILE = os.path.join(DATA_DIR, "my_portfolio.csv")
GRID_CSV = os.path.join(DATA_DIR, "mf_direct_grid.csv")
GRID_XLSX = os.path.join(DATA_DIR, "mf_direct_grid.xlsx")

ALERT_DROP_PCT = -5.0

EMAIL_TO = os.getenv("EMAIL_TO")
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================================================
# HELPERS
# =========================================================
def fetch_amfi_nav():
    url = "https://www.amfiindia.com/spages/NAVAll.txt"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def parse_amfi(text):
    rows = []
    for line in text.splitlines():
        if ";" not in line:
            continue
        parts = line.split(";")
        if len(parts) < 6:
            continue
        try:
            scheme_code = int(parts[0])
            scheme_name = parts[3].strip()
            nav = float(parts[4])
            nav_date = datetime.strptime(parts[5].strip(), "%d-%b-%Y")
            rows.append({
                "Scheme Code": scheme_code,
                "Scheme Name": scheme_name,
                "NAV Latest": nav,
                "NAV Date": nav_date
            })
        except:
            continue
    return pd.DataFrame(rows)


def send_telegram(msg):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})


def send_email(subject, body):
    if not (EMAIL_TO and SMTP_USERNAME and GMAIL_APP_PASSWORD):
        return
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USERNAME
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_USERNAME, GMAIL_APP_PASSWORD)
        server.send_message(msg)


# =========================================================
# MAIN
# =========================================================
def main():
    print("Fetching AMFI data...")
    raw = fetch_amfi_nav()
    amfi_df = parse_amfi(raw)

    if amfi_df.empty:
        raise RuntimeError("AMFI data empty")

    # -----------------------------------------------------
    # MASTER GRID (single source)
    # -----------------------------------------------------
    master_grid = amfi_df.copy()
    master_grid["NAV Date"] = master_grid["NAV Date"].dt.strftime("%d-%m-%Y")

    # EXPORT FIX — SAME DATA FOR CSV & XLSX
    master_grid.to_csv(GRID_CSV, index=False)
    master_grid.to_excel(GRID_XLSX, index=False)

    print("Master grid exported (CSV + XLSX identical)")

    # -----------------------------------------------------
    # PORTFOLIO UPDATE
    # -----------------------------------------------------
    if not os.path.exists(PORTFOLIO_FILE):
        print("Portfolio file not found, skipping portfolio update")
        return

    pf = pd.read_csv(PORTFOLIO_FILE)

    alerts = []

    for i, row in pf.iterrows():
        try:
            code = int(row["Scheme Code"])
        except:
            continue

        match = amfi_df[amfi_df["Scheme Code"] == code]
        if match.empty:
            continue

        nav = float(match.iloc[0]["NAV Latest"])
        nav_date = match.iloc[0]["NAV Date"]

        units = float(row["Units"])
        invested = float(row["Total Purchase Value"])

        current_value = units * nav
        deviation = ((current_value - invested) / invested) * 100

        pf.at[i, "Current NAV"] = round(nav, 4)
        pf.at[i, "Current Date"] = nav_date.strftime("%d-%m-%Y")
        pf.at[i, "Current Value"] = round(current_value, 2)
        pf.at[i, "% Deviation"] = round(deviation, 2)

        if deviation <= ALERT_DROP_PCT:
            alerts.append(
                f"{row['Scheme Name']} | {deviation:.2f}% | NAV {nav} ({nav_date.strftime('%d-%m-%Y')})"
            )

    pf.to_csv(PORTFOLIO_FILE, index=False)
    print("Portfolio updated")

    # -----------------------------------------------------
    # ALERTS
    # -----------------------------------------------------
    if alerts:
        msg = "⚠ MF Alert: NAV dropped below -5%\n\n" + "\n".join(alerts)
        send_email("MF Alert: -5% Breach", msg)
        send_telegram(msg)
        print("Alerts sent")
    else:
        print("No alerts triggered")


if __name__ == "__main__":
    main()
