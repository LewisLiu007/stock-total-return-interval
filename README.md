# Stock Interval Total Return (CN A-Shares) — Unadjusted Price + Cash Dividends

中文在下方

Overview
This tool computes a stock's interval return precisely by:
- Using unadjusted (non-adjusted) daily closing prices for both the start and end dates
- Adding up all cash dividends within the interval (no dividend reinvestment)
- Avoiding inaccuracies from forward/rear-adjusted price series

Formula
Total Return (no reinvestment) = (End_Close + Sum(Cash_Dividends_Per_Share in (Start_Trade_Day, End_Trade_Day]) - Start_Close) / Start_Close

Key points:
- Prices are unadjusted
- Dividends are included by ex-dividend date (除权除息日) strictly greater than start trading day and less than or equal to end trading day
- Only cash dividends are included; stock bonuses/splits/rights are ignored per requirement

Data Source
- AkShare: https://github.com/akfamily/akshare
  - Price: stock_zh_a_hist (adjust="")
  - Dividends (primary): stock_history_dividend_detail (Sina)
  - Dividends (fallback): stock_fhps_detail_ths (THS)
  - Trading window: derived from per-stock unadjusted price history (no global calendar dependency)

Features
- Read stock code(s), start date, and optional end date from config.yaml
- End date defaults to previous trading day when omitted
- Robust dividend extraction:
  - Prefer numeric per-share '派息' when available
  - Fallback to parsing plan text (分配方案) with common patterns like "10派X元" or "每10股派X元"
- Handles non-trading start/end by snapping to nearest trading days (start: next >=; end: prev <=)
- Outputs summary to console and CSV under output/

Quick Start
1) Environment
- Python 3.9+
- macOS/Windows/Linux

2) Install
- Create and activate a virtual environment (recommended)
- Install dependencies:
  pip install -r requirements.txt

3) Configure
- Edit config.yaml:
  stocks:
    - code: 600519
    - code: 000001
  start_date: 2021-01-01
  # end_date: 2025-01-10  # optional; if omitted defaults to previous trading day

Notes:
- Codes are A-share numeric codes without exchange prefix (e.g., 600519, 000001)
- Dates use YYYY-MM-DD

4) Run
- Option A (simple launcher):
  python main.py

- Option B (module mode, with src on sys.path):
  PYTHONPATH=src python -m totalreturn.cli

5) Output
- Console summary per stock:
  code,start_trade_date,end_trade_date,start_close,end_close,div_sum_per_share,total_return_pct
- CSV saved to output/summary_YYYYMMDD_HHMMSS.csv

Assumptions and Clarifications
- Dividends included by ex-dividend date (除权除息日) ∈ (start_trade_day, end_trade_day]
- If AkShare network temporarily fails, you may re-run; tool has basic fallbacks for end date selection
- Only cash dividends are included. Share bonuses, splits, allotments are ignored by design
- No dividend reinvestment

Troubleshooting
- If AkShare API schema changes, update column detection in ak_client.py accordingly
- If a start date is a non-trading day, the tool auto-selects the next trading day as start
- If no dividends exist in the interval, dividend sum will be 0

Project Structure
- stock-total-return-interval/
  - README.md
  - requirements.txt
  - config.yaml
  - main.py
  - src/
    - totalreturn/
      - __init__.py
      - config.py
      - ak_client.py
      - calculator.py
      - cli.py
  - output/ (auto-created)

License
- MIT

-------------------------------------------------------------------------------
中文说明

概述
本工具精确计算“区间总收益率（不复权+含现金分红，不复投）”：
- 起止价均使用不复权的日收盘价
- 将区间内所有现金分红累加（不考虑分红再投资）
- 避免使用前/后复权序列带来的区间起点偏差

计算公式
总收益率（不复投） = (区间终点收盘价 + 区间内现金分红总额/每股 - 区间起点收盘价) / 区间起点收盘价

关键点：
- 使用不复权价格
- 以除权除息日统计现金分红，严格使用 (起始交易日, 终止交易日] 区间
- 只计入现金分红；送转股、配股等不纳入本工具口径

数据来源
- AkShare: https://github.com/akfamily/akshare
  - 行情价格：stock_zh_a_hist (adjust="")
  - 分红数据（优先）：stock_history_dividend_detail（新浪）
  - 分红数据（回退）：stock_fhps_detail_ths（同花顺）
  - 交易区间：基于个股不复权价格序列自动推导（无需全市场交易日历）

功能
- 从 config.yaml 读取股票代码、起始日期、可选终止日期
- 若未设置终止日期则默认取“上一个交易日”
- 现金分红提取具备容错：
  - 优先使用数值型字段（每股派息“派息”）
  - 若缺失则解析分配方案文本（如“10派X元”、“每10股派X元”）
- 起止日期若为非交易日，自动对齐到最近的交易日（起点取后一个，终点取前一个）
- 控制台打印结果，同时写出 CSV 到 output/ 目录

快速开始
1) 环境
- Python 3.9+

2) 安装依赖
  pip install -r requirements.txt

3) 配置
- 编辑 config.yaml:
  stocks:
    - code: 600519
    - code: 000001
  start_date: 2021-01-01
  # end_date: 2025-01-10  # 可选；不填则默认“上一个交易日”

说明：
- A股代码使用6位数字（例如 600519, 000001），无需交易所前缀
- 日期格式为 YYYY-MM-DD

4) 运行
- 方式A（简易入口）：
  python main.py

- 方式B（以模块方式运行，需把 src 加入 sys.path）：
  PYTHONPATH=src python -m totalreturn.cli

5) 输出
- 控制台每只股票汇总：
  code,start_trade_date,end_trade_date,start_close,end_close,div_sum_per_share,total_return_pct
- 同时保存 CSV：output/summary_YYYYMMDD_HHMMSS.csv

假设与口径
- 分红统计口径为除权除息日 ∈ (起始交易日, 终止交易日]
- 网络波动导致 AkShare 请求失败时可重试
- 只统计现金分红；送转、配股等不纳入
- 不考虑分红再投资

故障排查
- 若 AkShare 接口字段变更，请在 ak_client.py 中更新列名适配逻辑
- 起始日期若非交易日，将自动取之后的首个交易日；终止日期若非交易日，将自动取之前的最近交易日
- 区间内无分红则分红总额为 0

项目结构
- stock-total-return-interval/
  - README.md
  - requirements.txt
  - config.yaml
  - main.py
  - src/
    - totalreturn/
      - __init__.py
      - config.py
      - ak_client.py
      - calculator.py
      - cli.py
  - output/（程序运行时自动创建）

许可证
- MIT
