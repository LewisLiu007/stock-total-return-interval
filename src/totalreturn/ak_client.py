from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Tuple

import akshare as ak
import pandas as pd


DATE_FMT = "%Y-%m-%d"


def _to_exchange_symbol(code: str) -> str:
    """
    Normalize to 6-digit numeric stock code used by AkShare EastMoney endpoints.
    For stock_zh_a_hist and most EM interfaces, symbol should NOT include sh/sz prefix.
    """
    code = str(code).strip()
    if not code:
        raise ValueError(f"Invalid stock code: {code!r}")
    # If user passed like "sh600519" or "sz000001", strip prefix and keep last 6 digits
    if not code.isdigit():
        code = code[-6:]
    return code.zfill(6)


def get_all_trade_dates() -> List[str]:
    """
    Fetch full trading calendar via AkShare with robust fallbacks.
    Primary: tool_trade_date_hist_sina
    Fallback: derive from a highly liquid stock's unadjusted daily history (e.g., SH 600000).
    Returns sorted list of YYYY-MM-DD strings.
    """
    dates: List[str] = []
    # Primary source
    try:
        df = ak.tool_trade_date_hist_sina()
        if df is not None and not df.empty:
            col = "trade_date" if "trade_date" in df.columns else df.columns[0]
            ser = pd.to_datetime(df[col].astype(str), format="%Y%m%d", errors="coerce")
            dates = ser.dropna().dt.strftime(DATE_FMT).tolist()
    except Exception:
        dates = []

    # Fallback: build from stock price history if primary failed/empty
    if not dates:
        try:
            today_str = datetime.today().strftime("%Y%m%d")
            df2 = ak.stock_zh_a_hist(
                symbol="600000", period="daily", start_date="19900101", end_date=today_str, adjust=""
            )
            if df2 is not None and not df2.empty:
                date_col = "日期" if "日期" in df2.columns else ("date" if "date" in df2.columns else df2.columns[0])
                ser2 = pd.to_datetime(df2[date_col], errors="coerce").dt.strftime(DATE_FMT)
                dates = sorted({d for d in ser2.dropna().tolist()})
        except Exception:
            dates = []

    # Ensure sorted ascending
    dates = sorted(dates)
    return dates


def pick_start_trade_date(start_date: str, trade_dates: List[str]) -> str:
    """
    For a given start_date (YYYY-MM-DD), return the first trading date >= start_date.
    """
    s = start_date
    for d in trade_dates:
        if d >= s:
            return d
    raise ValueError(f"No trading date found on/after {start_date}")


def pick_end_trade_date(end_date: str, trade_dates: List[str]) -> str:
    """
    For a given end_date (YYYY-MM-DD), return the last trading date <= end_date.
    """
    e = end_date
    last = None
    for d in trade_dates:
        if d <= e:
            last = d
        else:
            break
    if last is None:
        raise ValueError(f"No trading date found on/before {end_date}")
    return last


def get_default_end_trade_date(trade_dates: List[str]) -> str:
    """
    Default to the previous trading day relative to today's calendar date.
    If today is a trading day, still choose the previous one to avoid partial-day effects.
    """
    today_str = datetime.today().strftime(DATE_FMT)
    prev = None
    for d in trade_dates:
        if d < today_str:
            prev = d
        else:
            break
    if prev is None:
        # If no trading day before today (e.g., very early start), fallback to last available
        prev = trade_dates[-1]
    return prev


def get_hist_unadjusted_range(code: str, start_date: str, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch unadjusted daily price history for a date range [start_date, end_date].
    Dates are strings YYYY-MM-DD. If end_date is None, use today's calendar date.
    """
    symbol = _to_exchange_symbol(code)
    start_ymd = start_date.replace("-", "")
    end_ymd = (end_date or datetime.today().strftime(DATE_FMT)).replace("-", "")
    df = ak.stock_zh_a_hist(
        symbol=symbol, period="daily", start_date=start_ymd, end_date=end_ymd, adjust=""
    )
    return df


def derive_trade_window_from_prices(code: str, start_date: str, end_date: Optional[str] = None) -> Tuple[str, str]:
    """
    Derive (start_trade_date, end_trade_date) for a specific stock using its own price history,
    without relying on a global trading calendar.

    Rules:
    - start_trade_date: first available trading day >= start_date
    - end_trade_date when provided: last available trading day <= end_date
    - end_trade_date when not provided: default to previous trading day relative to today:
        * take the latest available trading day <= today
        * if that day equals today's date, pick the previous available trading day if exists
    """
    df = get_hist_unadjusted_range(code, start_date, end_date)
    if df is None or df.empty:
        # Fallback: try common liquid proxies to derive a general trading calendar
        fallback_symbols = ["600000", "000001", "601318", "000002"]
        dates: List[str] = []
        for sym in fallback_symbols:
            try:
                df2 = ak.stock_zh_a_hist(
                    symbol=sym, period="daily",
                    start_date=start_date.replace("-", ""),
                    end_date=(end_date or datetime.today().strftime(DATE_FMT)).replace("-", ""),
                    adjust=""
                )
                if df2 is not None and not df2.empty:
                    date_col2 = "日期" if "日期" in df2.columns else ("date" if "date" in df2.columns else df2.columns[0])
                    ser2 = pd.to_datetime(df2[date_col2], errors="coerce").dt.strftime(DATE_FMT)
                    dates = sorted({d for d in ser2.dropna().tolist()})
                    if dates:
                        break
            except Exception:
                continue

        if not dates:
            raise RuntimeError(f"Failed to fetch price history for code {code} to derive trade window.")

        # Use the derived general trading dates to pick start/end boundaries
        start_trade_date = pick_start_trade_date(start_date, dates)
        if end_date:
            end_trade_date = pick_end_trade_date(end_date, dates)
        else:
            end_trade_date = get_default_end_trade_date(dates)

        if start_trade_date > end_trade_date:
            raise RuntimeError(
                f"Derived start_trade_date {start_trade_date} is after end_trade_date {end_trade_date} for {code}."
            )

        return start_trade_date, end_trade_date

    date_col = "日期" if "日期" in df.columns else ("date" if "date" in df.columns else df.columns[0])
    ser = pd.to_datetime(df[date_col], errors="coerce").dt.strftime(DATE_FMT)
    dates = sorted({d for d in ser.dropna().tolist()})
    if not dates:
        raise RuntimeError(f"No valid trading dates found in price history for {code}.")

    # Start trade date
    start_candidates = [d for d in dates if d >= start_date]
    if not start_candidates:
        raise RuntimeError(f"No trading date on/after start_date {start_date} for {code}.")
    start_trade_date = start_candidates[0]

    # Determine boundary for end date
    if end_date:
        boundary = end_date
    else:
        today_str = datetime.today().strftime(DATE_FMT)
        # Latest <= today
        boundary = today_str

    end_candidates = [d for d in dates if d <= boundary]
    if not end_candidates:
        raise RuntimeError(f"No trading date on/before end boundary {boundary} for {code}.")

    end_trade_date = end_candidates[-1]

    # When end_date is None, enforce "previous trading day" if latest equals today
    if end_date is None:
        today_str = datetime.today().strftime(DATE_FMT)
        if end_trade_date == today_str and len(end_candidates) >= 2:
            end_trade_date = end_candidates[-2]

    if start_trade_date > end_trade_date:
        raise RuntimeError(
            f"Derived start_trade_date {start_trade_date} is after end_trade_date {end_trade_date} for {code}."
        )

    return start_trade_date, end_trade_date


def _get_hist_df_unadjusted(code: str, trade_date: str) -> pd.DataFrame:
    """
    Fetch unadjusted daily price history for a specific date (single-day window).
    Returns AkShare dataframe.
    """
    symbol = _to_exchange_symbol(code)
    ymd = trade_date.replace("-", "")
    df = ak.stock_zh_a_hist(
        symbol=symbol, period="daily", start_date=ymd, end_date=ymd, adjust=""
    )
    return df


def get_unadjusted_close_on(code: str, trade_date: str) -> float:
    """
    Get unadjusted close price on the given trading date.
    """
    df = _get_hist_df_unadjusted(code, trade_date)
    if df is None or df.empty:
        raise ValueError(f"No price data for {code} on {trade_date}")

    # Normalize columns
    date_col = "日期" if "日期" in df.columns else ("date" if "date" in df.columns else None)
    close_col = "收盘" if "收盘" in df.columns else ("close" if "close" in df.columns else None)
    if not date_col or not close_col:
        # Try to infer by position as last resort
        date_col = date_col or df.columns[0]
        close_col = close_col or df.columns[2]

    # Ensure date format alignment
    df[date_col] = pd.to_datetime(df[date_col]).dt.strftime(DATE_FMT)
    row = df.loc[df[date_col] == trade_date]
    if row.empty:
        # Some APIs may return a range even if single day; still ensure equality
        # If not found exact, try nearest within same day
        raise ValueError(f"Price row not found for {code} on {trade_date}")

    close_val = pd.to_numeric(row.iloc[0][close_col], errors="coerce")
    if pd.isna(close_val):
        raise ValueError(f"Invalid close price for {code} on {trade_date}")
    return float(close_val)


def _parse_cash_per_share_from_text(plan_text: str) -> float:
    """
    Parse cash dividend per share from Chinese plan text like:
      - "10派5元(含税)" -> 0.5 per share
      - "每10股派4.3元(含税)" -> 0.43 per share
      - "10派1.2元转4股" -> 0.12 per share
    Returns 0.0 if not found.
    """
    if not isinstance(plan_text, str) or not plan_text:
        return 0.0
    text = plan_text.replace("（", "(").replace("）", ")").replace(" ", "")
    text = text.lower()

    # First try explicit per-share patterns like "每股派0.5元" or "每股派息0.5元"
    m_ps = re.search(r"每股派(?:发)?(?:现金)?(?:红利)?([\d\.]+)元", text) or re.search(r"每股派息(?:现金)?(?:红利)?([\d\.]+)元", text)
    if m_ps:
        try:
            return float(m_ps.group(1))
        except Exception:
            pass

    # Common robust patterns for "per 10 shares cash dividend X yuan"
    patterns = [
        r"10派([\d\.]+)元",  # "10派X元"
        r"每10股派(?:发)?(?:现金)?(?:红利)?([\d\.]+)元",  # "每10股派X元"
        r"每10股(?:派发)?(?:现金)?(?:红利)?([\d\.]+)元",  # slight variants
        r"10送\d+(?:\.\d+)?股?转?\d*(?:\.\d+)?股?派([\d\.]+)元",  # "10送X转Y派Z元"
        r"10派([\d\.]+)元\(含税\)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            amt = m.group(1)
            try:
                val = float(amt) / 10.0
                return val
            except Exception:
                continue

    # Another attempt: find "...派0.5元" then check if "每10股" appears somewhere
    m2 = re.search(r"派([\d\.]+)元", text)
    if m2 and ("每10股" in text or text.startswith("10")):
        try:
            return float(m2.group(1)) / 10.0
        except Exception:
            return 0.0

    return 0.0


@dataclass
class DividendEvent:
    ex_date: str  # YYYY-MM-DD
    cash_per_share: float  # yuan per share (pre-tax)


def fetch_dividends_em(code: str) -> List[DividendEvent]:
    """
    Fetch dividend events from EastMoney via AkShare: stock_fhps_detail_em (per stock).
    Return list of DividendEvent with ex_date and cash_per_share (yuan per share).
    """
    try:
        df = ak.stock_fhps_detail_em(symbol=str(code))
    except Exception:
        return []
    if df is None or df.empty:
        return []

    # Normalize ex-dividend date
    ex_col = None
    for cand in ["A股除权除息日", "除权除息日", "除权日", "除息日", "ExDate", "ex_date"]:
        if cand in df.columns:
            ex_col = cand
            break
    if not ex_col:
        # Can't proceed if no ex-date
        return []

    # Attempt to get numeric per-share dividend columns
    numeric_per_share_cols = [c for c in df.columns if isinstance(c, str) and ("每股派息" in c or "派息(税前)" in c or "每股税前" in c or "派息" in c)]
    numeric_per_10_cols = [c for c in df.columns if isinstance(c, str) and ("每10股派息" in c or "每10股红利" in c)]

    plan_text_col = None
    for cand in ["分配方案", "派息方案", "分红方案", "方案", "预案"]:
        if cand in df.columns:
            plan_text_col = cand
            break

    events: List[DividendEvent] = []
    for _, row in df.iterrows():
        ex_val = row.get(ex_col, None)
        if pd.isna(ex_val):
            continue
        try:
            ex_dt = pd.to_datetime(ex_val).strftime(DATE_FMT)
        except Exception:
            continue

        cash_per_share: Optional[float] = None

        # Prefer numeric "per share" columns if available
        for c in numeric_per_share_cols:
            v = pd.to_numeric(row.get(c, None), errors="coerce")
            if pd.notna(v):
                cash_per_share = float(v)
                break

        # Next try "per 10 shares" numeric columns
        if cash_per_share is None:
            for c in numeric_per_10_cols:
                v = pd.to_numeric(row.get(c, None), errors="coerce")
                if pd.notna(v):
                    cash_per_share = float(v) / 10.0
                    break

        # Fallback to parse plan text
        if cash_per_share is None and plan_text_col:
            cash_per_share = _parse_cash_per_share_from_text(str(row.get(plan_text_col, "")))

        if cash_per_share is None:
            # Generic '派息' numeric column could exist; treat as per-share amount
            if "派息" in df.columns:
                v = pd.to_numeric(row.get("派息", None), errors="coerce")
                if pd.notna(v):
                    cash_per_share = float(v)

        if cash_per_share is None:
            cash_per_share = 0.0

        # Only record positive cash dividends
        if cash_per_share > 0:
            events.append(DividendEvent(ex_date=ex_dt, cash_per_share=cash_per_share))

    return events


def fetch_dividends_ths_fallback(code: str) -> List[DividendEvent]:
    """
    Primary per-stock dividend fetch via AkShare: stock_history_dividend_detail
    Use '除权除息日' as ex-date and numeric '派息' as cash per share (元/股，税前) when available.
    """
    try:
        df = ak.stock_history_dividend_detail(symbol=str(code), indicator="分红", date="")
    except Exception:
        return []

    if df is None or df.empty:
        return []

    # Ex-date column
    ex_col = None
    for cand in ["除权除息日", "A股除权除息日"]:
        if cand in df.columns:
            ex_col = cand
            break
    if not ex_col:
        return []

    # Numeric cash per share column
    cash_col = None
    # Prefer explicit per-share fields, then fall back to '派息' which is per 10 shares on Sina
    for cand in ["每股派息(税前)", "每股税前", "派息"]:
        if cand in df.columns:
            cash_col = cand
            break

    # Optional plan text column for fallback parsing
    plan_text_col = None
    for cand in ["分红方案说明", "分配方案", "方案", "预案"]:
        if cand in df.columns:
            plan_text_col = cand
            break

    events: List[DividendEvent] = []
    for _, row in df.iterrows():
        ex_val = row.get(ex_col, None)
        if pd.isna(ex_val):
            continue
        try:
            ex_dt = pd.to_datetime(ex_val).strftime(DATE_FMT)
        except Exception:
            continue

        cash_per_share = 0.0
        if cash_col is not None:
            v = pd.to_numeric(row.get(cash_col, None), errors="coerce")
            if pd.notna(v) and float(v) > 0:
                # Sina '派息' is per 10 shares; convert to per-share by dividing by 10
                if cash_col == "派息":
                    cash_per_share = float(v) / 10.0
                else:
                    cash_per_share = float(v)

        if cash_per_share <= 0 and plan_text_col:
            cash_per_share = _parse_cash_per_share_from_text(str(row.get(plan_text_col, "")))

        if cash_per_share > 0:
            events.append(DividendEvent(ex_date=ex_dt, cash_per_share=cash_per_share))

    return events

def fetch_dividends_ths(code: str) -> List[DividendEvent]:
    """
    Fallback per-stock dividend fetch via 同花顺: stock_fhps_detail_ths.
    Parse 'A股除权除息日' as ex-date and extract cash per share from '分红方案说明' text.
    """
    try:
        df = ak.stock_fhps_detail_ths(symbol=str(code))
    except Exception:
        return []
    if df is None or df.empty:
        return []

    # Ex-date column
    ex_col = None
    for cand in ["A股除权除息日", "除权除息日"]:
        if cand in df.columns:
            ex_col = cand
            break
    if not ex_col:
        return []

    # Plan text column for parsing cash per share
    plan_text_col = None
    for cand in ["分红方案说明", "分配方案", "方案", "预案"]:
        if cand in df.columns:
            plan_text_col = cand
            break

    events: List[DividendEvent] = []
    for _, row in df.iterrows():
        ex_val = row.get(ex_col, None)
        if pd.isna(ex_val):
            continue
        try:
            ex_dt = pd.to_datetime(ex_val).strftime(DATE_FMT)
        except Exception:
            continue

        cash_per_share = 0.0
        if plan_text_col:
            cash_per_share = _parse_cash_per_share_from_text(str(row.get(plan_text_col, "")))

        if cash_per_share > 0:
            events.append(DividendEvent(ex_date=ex_dt, cash_per_share=cash_per_share))

    return events


def get_dividends(code: str) -> List[DividendEvent]:
    """
    Get dividend events with cash per share.
    Prefer 历史分红单股接口 'stock_history_dividend_detail' (per stock; fast; contains 除权除息日 & 派息),
    and fall back to EastMoney 'stock_fhps_detail_em' if unavailable.
    """
    try:
        events = fetch_dividends_ths_fallback(code)
    except Exception:
        events = []
    if not events:
        events = fetch_dividends_ths(code)
    # Deduplicate by ex_date if duplicates exist, summing cash if same day has multiple events
    if not events:
        return []
    df = pd.DataFrame([{"ex_date": e.ex_date, "cash": e.cash_per_share} for e in events])
    agg = df.groupby("ex_date", as_index=False)["cash"].sum()
    return [DividendEvent(ex_date=r["ex_date"], cash_per_share=float(r["cash"])) for _, r in agg.iterrows()]


def sum_cash_dividends_in_interval(events: List[DividendEvent], start_trade_date: str, end_trade_date: str) -> Tuple[float, int]:
    """
    Sum cash dividends per share with ex_date in (start_trade_date, end_trade_date].
    Returns (sum_cash, event_count)
    """
    total = 0.0
    count = 0
    for e in events:
        if start_trade_date < e.ex_date <= end_trade_date:
            total += e.cash_per_share
            count += 1
    return total, count


def sum_additional_shares_in_interval(code: str, start_trade_date: str, end_trade_date: str) -> Tuple[float, int, str]:
    """
    Sum additional shares per original share arising from stock bonus/transfer/allotment within (start_trade_date, end_trade_date].
    - '分红' indicator provides numeric columns: '送股', '转增' (commonly per 10 shares on Sina)
    - '配股' indicator provides numeric '配股方案' (commonly per 10 shares)
    Returns (total_additional_shares_per_share, event_count, desc_text)
    desc_text is a semicolon-separated description of events, e.g.:
      "2024-06-19: 送0.5股/股, 转0.3股/股; 2023-12-20: 配0.2股/股"
    Note: We treat numeric columns as per-10-shares amounts and convert to per-share by dividing by 10.
    """
    total_additional = 0.0
    count = 0
    notes: List[str] = []

    # 分红: 送股/转增
    try:
        df_bonus = ak.stock_history_dividend_detail(symbol=str(code), indicator="分红", date="")
    except Exception:
        df_bonus = pd.DataFrame()

    if df_bonus is not None and not df_bonus.empty:
        # date column
        ex_col = None
        for cand in ["除权除息日", "A股除权除息日"]:
            if cand in df_bonus.columns:
                ex_col = cand
                break
        # numeric columns
        send_col = "送股" if "送股" in df_bonus.columns else None
        transfer_col = "转增" if "转增" in df_bonus.columns else None

        for _, row in df_bonus.iterrows():
            try:
                ex_val = row.get(ex_col) if ex_col else None
                if pd.isna(ex_val):
                    continue
                ex_dt = pd.to_datetime(ex_val).strftime(DATE_FMT)
            except Exception:
                continue
            if not (start_trade_date < ex_dt <= end_trade_date):
                continue

            send_val = pd.to_numeric(row.get(send_col, None), errors="coerce") if send_col else None
            transfer_val = pd.to_numeric(row.get(transfer_col, None), errors="coerce") if transfer_col else None

            per_share_added = 0.0
            if pd.notna(send_val) and float(send_val) > 0:
                per_share_added += float(send_val) / 10.0
            if pd.notna(transfer_val) and float(transfer_val) > 0:
                per_share_added += float(transfer_val) / 10.0

            if per_share_added > 0:
                total_additional += per_share_added
                count += 1
                notes.append(f"{ex_dt}: 送{'' if send_val is None or pd.isna(send_val) else f'{float(send_val)/10.0:.4f}'}股/股, 转{'' if transfer_val is None or pd.isna(transfer_val) else f'{float(transfer_val)/10.0:.4f}'}股/股")

    # 配股: 配股方案
    try:
        df_allot = ak.stock_history_dividend_detail(symbol=str(code), indicator="配股", date="")
    except Exception:
        df_allot = pd.DataFrame()

    if df_allot is not None and not df_allot.empty:
        # ex-date column for allotments
        ex_col2 = None
        for cand in ["除权日", "股权登记日"]:
            if cand in df_allot.columns:
                ex_col2 = cand
                break
        allot_col = "配股方案" if "配股方案" in df_allot.columns else None

        for _, row in df_allot.iterrows():
            try:
                ex_val = row.get(ex_col2) if ex_col2 else None
                if pd.isna(ex_val):
                    continue
                ex_dt = pd.to_datetime(ex_val).strftime(DATE_FMT)
            except Exception:
                continue
            if not (start_trade_date < ex_dt <= end_trade_date):
                continue

            allot_val = pd.to_numeric(row.get(allot_col, None), errors="coerce") if allot_col else None
            if pd.notna(allot_val) and float(allot_val) > 0:
                per_share_added = float(allot_val) / 10.0
                total_additional += per_share_added
                count += 1
                notes.append(f"{ex_dt}: 配{per_share_added:.4f}股/股")

    desc = "; ".join(notes)
    return total_additional, count, desc
