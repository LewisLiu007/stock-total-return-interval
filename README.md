# Stock Interval Total Return (CN A-Shares)

This repository calculates interval total return for China A-shares using:
- Unadjusted daily closing prices for start/end trading dates
- Cash dividends within the interval (no reinvestment)
- Value of additional shares from bonus/transfer/allotment within the interval (valued at end-date close)

Choose a language:
- English: README_en.md
- 中文：README_zh.md

Project structure:
- requirements.txt
- config.yaml
- main.py
- src/totalreturn/
  - __init__.py
  - config.py
  - ak_client.py
  - calculator.py
  - cli.py
- output/ (auto-created)
