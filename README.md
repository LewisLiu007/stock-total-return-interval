# 股票区间总收益率（A股）— Web/GUI/CLI 工具（默认中文）

本项目提供三种使用方式来计算中国 A 股在指定区间内的“总收益率”（不复权、不复投）：
- Web 界面（Flask，推荐）
- 桌面 GUI（Tkinter，受系统环境影响）
- 命令行 CLI

英文文档请参见: [English README](README_en.md)
数据接口与用法说明: [DATA_INTERFACES.md](DATA_INTERFACES.md)

---

## 一、Web 界面（推荐）

Web 界面提供可交互的浏览器页面，便于输入多只股票和日期区间，查看结果与导出 CSV。

- 入口文件: `src/web_app.py`
- 模板文件: `src/templates/index.html`

### 启动步骤
1) 安装依赖
```
pip install -r requirements.txt
```

2) 启动服务（默认监听 127.0.0.1:5000）
```
PYTHONPATH=src python src/web_app.py
```

3) 打开浏览器访问
```
http://127.0.0.1:5000
```

### 使用说明
- Stocks 输入框支持“股票名称”或“6位数字代码”，可混输，使用逗号分隔。例如：`贵州茅台, 五粮液, 000568, 洋河股份`
- Start Date 填写 YYYY-MM-DD 格式；End Date 留空表示取“上一个交易日”为终止交易日
- 点击 Calculate 进行计算；点击 Export CSV 导出结果到 `output/web_summary_YYYYMMDD_HHMMSS.csv`

### 交互细节
- 计算过程会显示“Calculating…”遮罩与进度指示，按钮在计算期间自动禁用，避免误操作
- 结果表格支持横向滚动查看所有字段
- 若输入了无法识别的名称或代码，会在结果中输出一条错误行（不影响其他股票的计算）

### 名称到代码映射
为提升体验，Web 使用以下策略进行名称→代码解析：
- 实时与离线映射：优先通过 AkShare 的 `stock_info_a_code_name` 和 `stock_zh_a_spot_em` 构建映射
- 模糊匹配：支持大小写忽略、子串匹配
- CLI 回退：必要时调用 CLI 的 `get_stock_name` 解析简称
- 静态兜底（常见酒类样例）：  
  - 贵州茅台 → 600519  
  - 五粮液 → 000858  
  - 洋河股份 → 002304  
  - 泸州老窖 → 000568

---

## 二、桌面 GUI（Tkinter）

- 入口文件: `src/gui_app.py`
- 运行方式:
```
PYTHONPATH=src python src/gui_app.py
```

注意事项：
- macOS 上若系统自带 Tk 版本不满足 `tkinter` 要求，窗口可能无法启动（环境依赖受系统约束）
- GUI 与 CLI/Web 核心计算逻辑保持一致，支持名称/代码混合输入、导出 CSV

---

## 三、命令行 CLI

- 入口文件：`main.py`（简易）或 `src/totalreturn/cli.py`（模块方式）
- 运行示例：
```
python main.py
# 或
PYTHONPATH=src python -m totalreturn.cli
```

### 配置
编辑 `config.yaml`：
```yaml
stocks:
  - code: 600519   # 贵州茅台
  - code: 000858   # 五粮液
  - code: 002304   # 洋河股份
  - code: 000568   # 泸州老窖
start_date: 2019-01-01
# end_date: 2025-01-10  # 可选；不填则默认取“上一个交易日”
```
说明：
- A 股代码使用 6 位数字（如 600519、000858），无需交易所前缀
- 日期格式为 YYYY-MM-DD

---

## 四、计算口径与公式（Web/GUI/CLI 通用）

本工具用于精确计算中国 A 股在指定区间内的“总收益率”（不复权、不复投），口径包含：
- 起止交易日均使用不复权的日收盘价
- 统计区间内的现金分红总额（不考虑分红再投资）
- 统计区间内的送股 / 转增 / 配股所带来的“每股新增股数”，并按终止交易日收盘价估值计入收益
- 避免使用前/后复权序列带来的口径偏差

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

- `AdditionalSharesPerShare` 为区间内发生的送股 / 转增 / 配股事件的“每股新增股数”之和（按每股口径）
- 新增股份价值按终止交易日收盘价估值
- 配股认购价的现金流不计入（仅将新增股份按终止交易日价格估值）

---

## 五、数据来源（AkShare）

- 行情价格：`stock_zh_a_hist`，`adjust=""`（不复权）
- 现金分红（优先）：`stock_history_dividend_detail`（新浪，单股）
- 现金分红（回退）：`stock_fhps_detail_ths`（同花顺，单股文本方案）
- 股票简称：`stock_individual_info_em`（东方财富），并回退到 `stock_info_a_code_name` 映射

字段与解析说明：
- 新浪的“派息”“送股”“转增”“配股方案”等数值列通常按“每10股”口径，统一转换为“每股”（除以 10）
- 同花顺的文本方案（如“10派X元”“每10股派X元”“每股派X元”）通过解析得到每股现金分红
- 现金分红按“除权除息日”计入，口径为 (start_trade_date, end_trade_date]

---

## 六、输出字段

- name, code
- start_trade_date, end_trade_date
- start_close, end_close
- div_sum_per_share, div_event_count
- additional_shares_per_share, additional_event_count, additional_value_per_share, bonus_allot_desc
- total_return（小数），annualized_return（小数）
- total_return_pct, annualized_return_pct
- error（若有）

Web/GUI 导出到 `output/web_summary_*.csv` / `output/gui_summary_*.csv`  
CLI 导出到 `output/summary_*.csv`

---

## 七、故障排查与注意事项

- 若 AkShare 接口字段有变，请在 `src/totalreturn/ak_client.py` 更新列名适配逻辑
- 起始日期若为非交易日，工具自动选择之后的首个交易日；终止日期若为非交易日，自动选择之前最近的交易日
- 区间内如无分红或送配事件，相关汇总值为 0
- Web 名称映射含模糊匹配与静态兜底，无法识别的输入会单独输出错误行
- 网络波动或服务端接口暂不可用时，可稍后重试

---

## 八、项目结构

```
stock-total-return-interval/
  README.md          # 默认中文（本文件），含 Web/GUI/CLI 说明
  README_en.md       # 英文文档
  README_zh.md       # 详细中文文档（CLI口径说明更全）
  requirements.txt
  config.yaml
  main.py
  src/
    web_app.py
    gui_app.py
    templates/
      index.html
    totalreturn/
      __init__.py
      config.py
      ak_client.py
      calculator.py
      cli.py
  output/  （程序运行时自动创建）
```

---

## 九、许可证

MIT
