# Stock Interval Total Return (CN A-Shares) — Unadjusted Price + Cash Dividends + Bonus/Allotment Value

This tool computes a stock's interval total return with high fidelity for China A-shares by:
- Using unadjusted daily closing prices for the start and end trading dates
- Including all cash dividends within the interval (no dividend reinvestment)
- Including the value of additional shares from bonus/transfer/allotment within the interval, valued at the end-date close
- Avoiding inaccuracies from forward/rear-adjusted price series

## Formula

Total Return (no reinvestment):
```
TR = (End_Close
      + SumCashDividendsPerShare
      + End_Close * AdditionalSharesPerShare
      - Start_Close) / Start_Close
```

Annualized Return (calendar-day basis):
```
Annualized = (1 + TR)^(365 / Days) - 1
```
where Days is the number of calendar days between start_trade_date and end_trade_date.

- AdditionalSharesPerShare = per-share sum of 送股/转增/配股 events that occur in (start_trade_date, end_trade_date].
- Value of additional shares is computed at End_Close.
- Allotment purchase price cash flow is not considered (only added shares are valued as requested).

## Data Sources (AkShare)

- Price: `stock_zh_a_hist` with `adjust=""` (unadjusted)
- Dividends (primary): `stock_history_dividend_detail` (Sina, per-stock)
- Dividends (fallback): `stock_fhps_detail_ths` (THS, per-stock textual plan)
- Stock name: `stock_individual_info_em` (EM) with fallback to `stock_info_a_code_name` mapping

Notes on columns and parsing:
- On Sina, numeric columns such as “派息” (cash dividend), “送股” (bonus), “转增” (transfer), and “配股方案” (allotment plan) are typically per 10 shares. The tool converts them to per-share by dividing by 10.
- THS textual plans (e.g., “10派X元”, “每10股派X元”, “每股派X元”) are parsed to derive per-share cash dividends.
- Dividends included by ex-dividend date ∈ (start_trade_date, end_trade_date].

## Features

- Derives trading window from the stock’s own unadjusted price history (no global calendar dependency).
- Outputs stock name (股票简称) in console.
- Computes and prints annualized return.
- Includes a final description column listing bonus/transfer/allotment events in the interval.
- Saves a CSV with comprehensive fields for further processing.

## Quick Start

1) Environment
- Python 3.9+
- macOS/Windows/Linux

2) Install
```
pip install -r requirements.txt
```

3) Configure
Edit `config.yaml`:
```yaml
stocks:
  - code: 600519   # 贵州茅台
  - code: 000001   # 平安银行
  - code: 000568   # 泸州老窖
start_date: 2019-01-01
# end_date: 2025-01-10  # optional; if omitted defaults to previous trading day
```
Notes:
- Codes are 6-digit A-share codes without exchange prefix (e.g., 600519, 000001).
- Dates use YYYY-MM-DD.

4) Run
- Simple launcher:
```
python main.py
```
- Module mode (with src on sys.path):
```
PYTHONPATH=src python -m totalreturn.cli
```

5) Output
- Console summary per stock:
```
name,start_trade_date,end_trade_date,start_close,end_close,div_sum_per_share,div_event_count,total_return_pct,annualized_return_pct,bonus_allot_desc,error
```
- CSV saved to `output/summary_YYYYMMDD_HHMMSS.csv` with additional fields:
  - name, code
  - start_trade_date, end_trade_date
  - start_close, end_close
  - div_sum_per_share, div_event_count
  - additional_shares_per_share, additional_event_count, additional_value_per_share, bonus_allot_desc
  - total_return (decimal), annualized_return (decimal)
  - total_return_pct, annualized_return_pct

## Assumptions and Clarifications

- Prices are unadjusted.
- Cash dividends included by ex-dividend date in (start_trade_date, end_trade_date].
- Additional shares (bonus/transfer/allotment) included when their ex/record date falls in (start_trade_date, end_trade_date], valued at end-date close.
- Allotment purchase price cash flow is not modeled; only added shares are valued.
- No dividend reinvestment.

## Troubleshooting

- If AkShare API schemas change, update column detection in `src/totalreturn/ak_client.py`.
- If the start date is a non-trading day, the tool auto-selects the next trading day as start.
- If no dividends or share changes exist in the interval, respective sums will be 0.
- Network issues: re-run if requests fail intermittently.

## Project Structure

```
stock-total-return-interval/
  README.md
  README_en.md
  README_zh.md
  requirements.txt
  config.yaml
  main.py
  src/
    totalreturn/
      __init__.py
      config.py
      ak_client.py
      calculator.py
      cli.py
  output/  (auto-created)
```

## License

MIT
