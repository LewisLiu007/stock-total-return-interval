# 数据获取接口与用法说明（AkShare，单股粒度）

本文档系统性说明本项目在“股价、现金分红、送/转/配股、名称映射”方面使用的 AkShare 接口、调用粒度、解析口径与对应代码位置，便于维护与扩展。

## 1. 总体策略与调用粒度

- 粒度：统一采用“按单只股票请求”的策略，不一次性请求全市场，避免分页慢与字段变动带来的不稳定。
- 分拆：股价与分红/送配分别调用不同接口，互不影响。
- 回退：优先使用稳定单股接口；取不到时使用备用接口；必要时用常见品种构造交易日历兜底。

---

## 2. 股价（不复权）

- 接口  
  `ak.stock_zh_a_hist(symbol, period="daily", start_date, end_date, adjust="")`

- 用法要点  
  - `symbol`: 6 位数字代码（不带 `sh/sz` 前缀），例如 `"600519"`  
  - `start_date` / `end_date`: 字符串 `"YYYYMMDD"`  
  - `adjust=""`: 不复权

- 在代码中的位置  
  - `src/totalreturn/ak_client.py`  
    - `get_hist_unadjusted_range(code, start_date, end_date)`  
      拉该股一段不复权日线，用于推导交易区间等。  
    - `derive_trade_window_from_prices(code, start_date, end_date)`  
      基于该股自身价格选择区间首尾“有效交易日”；若该股无数据，会尝试 `600000/000001/601318/000002` 构造通用交易日历。  
    - `get_unadjusted_close_on(code, trade_date)`  
      通过单日窗口调用 `stock_zh_a_hist` 获得当日不复权收盘价。

- 示例  
  ```python
  import akshare as ak
  df = ak.stock_zh_a_hist(symbol="600519", period="daily",
                          start_date="20190101", end_date="20260112", adjust="")
  # 单日：
  df1 = ak.stock_zh_a_hist(symbol="600519", period="daily",
                           start_date="20190102", end_date="20190102", adjust="")
  ```

---

## 3. 现金分红（按除权除息日）

- 首选接口（Sina 单股，数值字段稳定、速度快）  
  `ak.stock_history_dividend_detail(symbol=code, indicator="分红", date="")`  
  - 读取“除权除息日”和“每股派息(税前)”或“派息”。  
  - 注意：“派息”字段常为“每10股”，需除以 10 转为每股。

- 回退接口（同花顺 单股文本解析）  
  `ak.stock_fhps_detail_ths(symbol=code)`  
  - 解析“分红方案说明”，识别“10派X元 / 每10股派X元 / 每股派X元”等，换算为每股金额。

- 在代码中的位置  
  - `src/totalreturn/ak_client.py`  
    - `get_dividends(code)`  
      先走 `fetch_dividends_ths_fallback`（Sina 单股），失败再走 `fetch_dividends_ths`（同花顺 单股文本）。同日多条事件会合并金额。  
    - `sum_cash_dividends_in_interval(events, start_trade_date, end_trade_date)`  
      对区间 `(start_trade_date, end_trade_date]` 汇总每股现金分红总额及事件计数。

- 示例  
  ```python
  df = ak.stock_history_dividend_detail(symbol="600519", indicator="分红", date="")
  df2 = ak.stock_fhps_detail_ths(symbol="600519")
  ```

---

## 4. 送股 / 转增 / 配股（每股新增股数）

- 接口（均为单股）  
  1) 送股/转增：  
     `ak.stock_history_dividend_detail(symbol=code, indicator="分红", date="")`  
     字段“送股”“转增”通常按“每10股”，需除以 10 转为“每股新增股数”。  
  2) 配股：  
     `ak.stock_history_dividend_detail(symbol=code, indicator="配股", date="")`  
     字段“配股方案”通常按“每10股”，同样除以 10。

- 在代码中的位置  
  - `src/totalreturn/ak_client.py`  
    - `sum_additional_shares_in_interval(code, start_trade_date, end_trade_date)`  
      汇总区间 `(start_trade_date, end_trade_date]` 的“每股新增股数”之和、事件数，并返回说明文本。  
      说明示例：“2021-07-05: 送0.4000股/股, 转0.0000股/股；2020-xx-xx: 配0.2000股/股”。

- 示例  
  ```python
  df_bonus = ak.stock_history_dividend_detail(symbol="600519", indicator="分红", date="")
  df_allot = ak.stock_history_dividend_detail(symbol="600519", indicator="配股", date="")
  ```

---

## 5. 名称 / 代码映射（用户输入体验）

- 接口与策略  
  1) `ak.stock_info_a_code_name()`（代码-简称映射表，优先）  
  2) `ak.stock_zh_a_spot_em()`（全 A 股现货列表，回退）  
  3) `ak.stock_individual_info_em(symbol=code)`（CLI 侧按 item/value 表查询“股票简称”）  
  4) Web/GUI 侧做模糊匹配与静态兜底（常见酒类样例：茅台/五粮液/洋河/泸州老窖）

- 在代码中的位置  
  - `src/gui_app.py::build_code_maps()`  
    先 `stock_info_a_code_name`，后 `stock_zh_a_spot_em`，再静态兜底 + 模糊匹配。  
  - `src/totalreturn/cli.py::get_stock_name(code)`  
    先 `stock_individual_info_em(item/value)`，回退 `stock_info_a_code_name`。

---

## 6. 每只股票一次完整计算的大致请求数（常见路径）

1) 推导交易区间：1 次 `stock_zh_a_hist`（范围）。若该股无数据，额外尝试至多 4 次常见股票兜底。  
2) 起止收盘价：2 次单日 `stock_zh_a_hist`。  
3) 现金分红：1 次 `stock_history_dividend_detail`；若失败再 1 次 `stock_fhps_detail_ths`。  
4) 送/转/配：`indicator="分红"` 1 次 + `indicator="配股"` 1 次。  

合计约 5-6 次单股请求（不含少量回退额外请求）。名称映射在 Web/GUI 通常进程启动或首次使用时构建一次并缓存，不随每股重复。

---

## 7. 计算口径如何用到上述数据

- `src/totalreturn/calculator.py::compute_interval_total_return`  
  - `start_close` / `end_close` ← `get_unadjusted_close_on`（不复权）  
  - `dividend_sum_per_share` ← `get_dividends` + `sum_cash_dividends_in_interval((start, end]]`  
  - `additional_shares_per_share` ← `sum_additional_shares_in_interval((start, end]]`  
  - `additional_value_per_share = end_close * additional_shares_per_share`  
  - `TR = (end_close + dividend_sum + additional_value - start_close) / start_close`  
  - `Annualized = (1 + TR)^(365 / Days) - 1`（按自然日）

---

## 8. 典型调用顺序（CLI/Web/GUI 共享核心逻辑）

1) `derive_trade_window_from_prices(code, start_date, end_date)`  
2) `compute_interval_total_return(code, start_trade_date, end_trade_date)`  
   - 内部调用 `get_unadjusted_close_on`、`get_dividends/sum_cash_dividends_in_interval`、`sum_additional_shares_in_interval`  
3) 输出总收益率与年化收益率，以及分红与送配说明。

---

## 9. 为什么不批量请求全市场

- 全市场接口通常分页且慢、字段格式变化频繁。  
- 本项目强调交互性能与口径稳定，故统一选择“单股、无分页”的接口拆分获取，并辅以解析与回退机制。

---

## 10. 参考接口一览（AkShare）

- 行情价格：`stock_zh_a_hist`（不复权）  
- 分红（优先）：`stock_history_dividend_detail`（Sina 单股）  
- 分红（回退）：`stock_fhps_detail_ths`（同花顺 单股文本）  
- 送/转/配：`stock_history_dividend_detail`（indicator="分红"/"配股"）  
- 名称映射：`stock_info_a_code_name` / `stock_zh_a_spot_em` / `stock_individual_info_em`
