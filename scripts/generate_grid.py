import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import os
import smtplib
from email.mime.text import MIMEText

# ---------------- CONFIG ----------------
PORTFOLIO_FILE = "data/my_portfolio.csv"
AMFI_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
IST = pytz.timezone("Asia/Kolkata")

ALERT_THRESHOLD = -5.0  # percent

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ---------------- EMAIL ----------------
def send_email(subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.environ["SMTP_USERNAME"]
        msg["To"] = os.environ["EMAIL_TO"]

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(os.environ["SMTP_USERNAME"], os.environ["GMAIL_APP_PASSWORD"])
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email failed:", e)

# ---------------- TELEGRAM ----------------
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage"
        payload = {
            "chat_id": os.environ["TELEGRAM_CHAT_ID"],
            "text": message
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram failed:", e)

# ---------------- NAV FETCH ----------------
def fetch_latest_nav_map():
    r = requests.get(AMFI_URL, timeout=30)
    lines = r.text.splitlines()

    nav_map = {}
    for line in lines:
        if ";" in line and line[0].isdigit():
            parts = line.split(";")
            try:
                code = int(parts[0])
                nav = float(parts[4])
                nav_date = datetime.strptime(parts[5], "%d-%b-%Y")
                nav_map[code] = (nav, nav_date)
            except:
                continue
    return nav_map

# ---------------- MAIN ----------------
def main():
    df = pd.read_csv(PORTFOLIO_FILE)
    nav_map = fetch_latest_nav_map()

    alerts = []

    for i, row in df.iterrows():
        code = int(row["Scheme Code"])
        units = float(row["Units"])
        invested = float(row["Total Purchase Value"])

        if code not in nav_map:
            continue

        nav, nav_date = nav_map[code]

        current_value = units * nav
        deviation = ((current_value - invested) / invested) * 100

        df.at[i, "Current NAV"] = round(nav, 4)
        df.at[i, "Current Date"] = nav_date.strftime("%d-%m-%Y")
        df.at[i, "Current Value"] = round(current_value, 2)
        df.at[i, "% Deviation"] = round(deviation, 2)

        if deviation <= ALERT_THRESHOLD:
            alerts.append(
                f"{row['Scheme Name']}\n"
                f"Deviation: {round(deviation,2)}%\n"
                f"NAV: {round(nav,4)} | Value: ₹{round(current_value,2)}"
            )

    # Save updated portfolio (overwrite – as agreed)
    df.to_csv(PORTFOLIO_FILE, index=False)

    # Send alerts if any
    if alerts:
        message = "🚨 MF ALERT: −5% Breach 🚨\n\n" + "\n\n".join(alerts)
        send_email("MF Alert: Portfolio Drop Detected", message)
        send_telegram(message)

if __name__ == "__main__":
    main()
