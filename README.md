# Mutual Fund Performance Engine

This repository automates mutual fund performance analysis, builds dashboards, generates a daily Excel grid, emails updates, and tracks your personal MF portfolio with alerts.

## 🚀 Features

- Daily auto-generation of Mutual Fund Grid  
- Automated GitHub Actions workflow for daily execution  
- Conditional formatting and dashboard sheets in Excel  
- Top-10 Fund Performers auto-created  
- Streamlit Dashboard deployment  
- Custom MF Portfolio tracker with alerts  
- Sector heatmaps, rolling return charts, benchmarking  
- SIP calculator + interactive tools  

## 📁 Repository Structure

```
mf-direct-performance/
│
├── dashboard/
│   └── app.py
│
├── scripts/
│   ├── generate_grid.py
│   ├── email_results.py
│   └── utils/
│
├── data/
│   ├── mf_direct_grid.csv
│   ├── mf_direct_grid.xlsx
│   └── my_portfolio.csv
│
├── .github/workflows/
│   └── daily_run.yml
│
└── requirements.txt
```

## ⚡ Automation

- GitHub Actions runs daily at 8:30 AM IST  
- Emails Excel report to your Gmail  
- Streamlit dashboard auto-updates from GitHub raw CSV  
- Portfolio tracker calculates:  
  - Purchase Value  
  - Current Value  
  - % Gain/Loss  
  - Exit Load (Yes/No + Amount)  
  - Alerts when NAV drops 5% from purchase NAV  

## 🧮 Portfolio CSV Format

```
Scheme Code,
Scheme Name,
Units,
Purchase NAV,
Purchase Date,
Current NAV,
Current Value,
% Deviation,
Exit Load Applies?,
Exit Load %
```

## 📊 Streamlit Dashboard

Includes:
- Complete MF Grid  
- Top 10 Performers  
- Sector Heatmap  
- Rolling Returns (1Y, 3Y)  
- Benchmark Comparison  
- SIP Calculator  
- Portfolio Tracker with Alerts  
- Download Buttons  
- Screenshot capability  

App auto-updates when GitHub CSV updates.

## 📬 Email Automation

Uses Gmail App Password (stored in GitHub Secrets).  
Attaches daily Excel grid.

## 🛠 Requirements

- Python 3.10+
- GitHub Actions enabled
- Gmail App Password for email automation

Install dependencies:
```
pip install -r requirements.txt
```

## 📎 License

Open-source for personal and analytical use.

---

For any enhancement, open an issue or request new features!
