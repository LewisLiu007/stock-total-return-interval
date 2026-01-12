from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from .ak_client import (
    get_unadjusted_close_on,
    get_dividends,
    sum_cash_dividends_in_interval,
    sum_additional_shares_in_interval,
)


@dataclass
class IntervalResult:
    code: str
    start_trade_date: str
    end_trade_date: str
    start_close: float
    end_close: float
    dividend_sum_per_share: float
    dividend_event_count: int
    additional_shares_per_share: float  # 送股/转增/配股合计，每股新增股数
    additional_event_count: int
    additional_value_per_share: float  # 按结束日收盘价计算的新增股份价值（每股）
    bonus_allot_desc: str  # 说明文本
    total_return: float  # decimal, e.g., 0.1234 for 12.34%

    def as_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "start_trade_date": self.start_trade_date,
            "end_trade_date": self.end_trade_date,
            "start_close": self.start_close,
            "end_close": self.end_close,
            "div_sum_per_share": self.dividend_sum_per_share,
            "div_event_count": self.dividend_event_count,
            "additional_shares_per_share": self.additional_shares_per_share,
            "additional_event_count": self.additional_event_count,
            "additional_value_per_share": self.additional_value_per_share,
            "bonus_allot_desc": self.bonus_allot_desc,
            "total_return": self.total_return,
        }


def compute_interval_total_return(code: str, start_trade_date: str, end_trade_date: str) -> IntervalResult:
    """
    Compute interval total return including cash dividends and additional shares value:
      TotalReturn = (End_Close + SumCashDividendsPerShare + End_Close * AdditionalSharesPerShare - Start_Close) / Start_Close
    where:
      - Prices are unadjusted
      - Dividends counted with ex-date in (start_trade_date, end_trade_date]
      - Additional shares (送股/转增/配股) counted with ex/record dates in (start_trade_date, end_trade_date] and valued at End_Close
    """
    # Prices
    start_close = float(get_unadjusted_close_on(code, start_trade_date))
    end_close = float(get_unadjusted_close_on(code, end_trade_date))

    # Dividends
    events = get_dividends(code)
    div_sum, div_count = sum_cash_dividends_in_interval(events, start_trade_date, end_trade_date)

    # Additional shares (bonus, transfer, allotment)
    add_shares_per_share, add_event_count, add_desc = sum_additional_shares_in_interval(code, start_trade_date, end_trade_date)
    add_value_per_share = end_close * add_shares_per_share

    total_return = (end_close + div_sum + add_value_per_share - start_close) / start_close

    return IntervalResult(
        code=code,
        start_trade_date=start_trade_date,
        end_trade_date=end_trade_date,
        start_close=start_close,
        end_close=end_close,
        dividend_sum_per_share=div_sum,
        dividend_event_count=div_count,
        additional_shares_per_share=add_shares_per_share,
        additional_event_count=add_event_count,
        additional_value_per_share=add_value_per_share,
        bonus_allot_desc=add_desc,
        total_return=total_return,
    )
