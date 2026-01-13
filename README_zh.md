# 股票区间总收益率（A股）— 不复权价格 + 现金分红 + 送配股价值

本工具用于精确计算中国 A 股在指定区间内的“总收益率”（不复权、不复投），口径包含：
- 起止交易日均使用不复权的日收盘价
- 统计区间内的现金分红总额（不考虑分红再投资）
- 统计区间内的送股 / 转增 / 配股所带来的“每股新增股数”，并按终止交易日收盘价估值计入收益
- 避免使用前/后复权序列带来的口径偏差

## 计算公式

区间总收益率（不复投）：
```
TR = (End_Close
      + SumCashDividendsPerShare
      + End_Close * AdditionalSharesPerShare
      - Start_Close) / Start_Close
```

年化收益率（按自然日）：
```
Annualized = (1 + TR)^(365 / Days) - 1
```
其中 `Days` 为起止交易日之间的自然日数量。

- `AdditionalSharesPerShare` 为区间内发生的送股 / 转增 / 配股事件的“每股新增股数”之和（按每股口径）。
- 新增股份价值按终止交易日收盘价估值。
- 配股认购价的现金流不计入（仅将新增股份按终止交易日价格估值），符合“送配股的股数按照最后结束日期的股价算到收益里面去”的要求。

## 数据来源（AkShare）

- 行情价格：`stock_zh_a_hist`，`adjust=""`（不复权）
- 现金分红（优先）：`stock_history_dividend_detail`（新浪，单股）
- 现金分红（回退）：`stock_fhps_detail_ths`（同花顺，单股文本方案）
- 股票简称：`stock_individual_info_em`（东方财富），并回退到 `stock_info_a_code_name` 映射

字段与解析说明：
- 新浪的“派息”“送股”“转增”“配股方案”等数值列通常按“每10股”口径，本工具统一转换为“每股”（除以 10）。
- 同花顺的文本方案（如“10派X元”“每10股派X元”“每股派X元”）通过解析得到每股现金分红。
- 现金分红按“除权除息日”计入，口径为 (start_trade_date, end_trade_date]。

## 功能特性

- 交易区间：基于个股不复权价格自动推导，无需全市场交易日历。
- 控制台输出股票简称（股票名称）。
- 计算并输出年化收益率。
- 控制台末列增加“送配说明”（bonus_allot_desc），列出区间内的送股/转增/配股事件。
- 生成包含完整字段的 CSV，便于后续处理。

## 快速开始

1) 环境
- Python 3.9+
- macOS / Windows / Linux

2) 安装依赖
```
pip install -r requirements.txt
```

3) 配置
编辑 `config.yaml`：
```yaml
stocks:
  - code: 600519   # 贵州茅台
  - code: 000001   # 平安银行
  - code: 000568   # 泸州老窖
start_date: 2019-01-01
# end_date: 2025-01-10  # 可选；不填则默认取“上一个交易日”
```
说明：
- A 股代码使用 6 位数字（如 600519、000001），无需交易所前缀。
- 日期格式为 YYYY-MM-DD。

4) 运行
- 简易入口：
```
python main.py
```
- 模块方式（需将 src 加入 sys.path）：
```
PYTHONPATH=src python -m totalreturn.cli
```

## 输出

- 控制台汇总（每只股票）：
```
name,start_trade_date,end_trade_date,start_close,end_close,div_sum_per_share,div_event_count,total_return_pct,annualized_return_pct,bonus_allot_desc,error
```
- 同时保存 CSV 至 `output/summary_YYYYMMDD_HHMMSS.csv`，包含以下字段：
  - name, code
  - start_trade_date, end_trade_date
  - start_close, end_close
  - div_sum_per_share, div_event_count
  - additional_shares_per_share, additional_event_count, additional_value_per_share, bonus_allot_desc
  - total_return（小数），annualized_return（小数）
  - total_return_pct, annualized_return_pct

## 假设与口径

- 行情价格使用不复权。
- 现金分红按除权除息日计入，区间口径为 (start_trade_date, end_trade_date]。
- 送股 / 转增 / 配股：当其除权或登记日期落入区间时计入，对应新增股份按终止交易日收盘价估值。
- 配股认购价的现金流不纳入收益，遵循用户需求：仅将新增股份价值计入。
- 不考虑分红再投资。

## 故障排查

- 若 AkShare 接口字段有变，请在 `src/totalreturn/ak_client.py` 中更新列名适配逻辑。
- 起始日期若为非交易日，工具自动选择之后的首个交易日；终止日期若为非交易日，自动选择之前最近的交易日。
- 区间内如无分红或送配事件，相关汇总值为 0。
- 若网络波动导致请求失败，可重试。

## 项目结构

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
  output/  （程序运行时自动创建）
```

## 许可证

MIT
