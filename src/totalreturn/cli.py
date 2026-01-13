from __future__ import annotations

import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime

import pandas as pd
import akshare as ak

from .config import load_config, AppConfig
from .ak_client import (
    derive_trade_window_from_prices,
)
from .calculator import compute_interval_total_return


def resolve_trade_window(cfg: AppConfig) -> (str, str):
    """
    Resolve the interval trading window solely by deriving from a configured stock's own price history.
    This avoids reliance on external trading calendar endpoints.
    """
    if not cfg.stocks:
        raise RuntimeError("No stocks configured to derive trading window.")
    first_code = str(cfg.stocks[0].code).zfill(6)
    start_trade_date, end_trade_date = derive_trade_window_from_prices(first_code, cfg.start_date, cfg.end_date)
    if start_trade_date > end_trade_date:
        raise ValueError(
            f"Computed start_trade_date {start_trade_date} is after end_trade_date {end_trade_date}. "
            f"Please adjust start_date/end_date in config."
        )
    return start_trade_date, end_trade_date


def get_stock_name(code: str) -> str:
    """
    Resolve stock name (股票简称) for a given 6-digit A-share code.
    Strategy:
      1) Try EastMoney individual info (stock_individual_info_em), scanning ['item','value'] rows.
      2) Fallback to a market-wide code-name map (stock_info_a_code_name).
    """
    code6 = str(code).zfill(6)
    # Attempt 1: EM individual info
    try:
        df = ak.stock_individual_info_em(symbol=code6)
        if df is not None and not df.empty and "item" in df.columns and "value" in df.columns:
            for cand in ["股票简称", "SECURITY_NAME_ABBR", "证券简称"]:
                row = df.loc[df["item"] == cand]
                if not row.empty:
                    name_val = row.iloc[0]["value"]
                    if isinstance(name_val, str) and name_val.strip():
                        return name_val.strip()
    except Exception:
        pass
    # Attempt 2: Code-name map
    try:
        df_map = ak.stock_info_a_code_name()
        if df_map is not None and not df_map.empty:
            # Normalize code column to 6-digit numeric
            code_col = None
            for cand in ["证券代码", "A股代码"]:
                if cand in df_map.columns:
                    code_col = cand
                    break
            name_col = None
            for cand in ["证券简称", "股票简称"]:
                if cand in df_map.columns:
                    name_col = cand
                    break
            if code_col and name_col:
                df_map[code_col] = df_map[code_col].astype(str).str[-6:].str.zfill(6)
                match = df_map.loc[df_map[code_col] == code6]
                if not match.empty:
                    name_val = str(match.iloc[0][name_col]).strip()
                    if name_val:
                        return name_val
    except Exception:
        pass
    return code6


def run(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute calculation for all stocks in config.
    Returns a dict with 'rows' (list of result dicts) and 'csv_path'.
    """
    cfg = load_config(config_path)
    if not cfg.stocks:
        raise ValueError("No stocks configured. Please add at least one stock code in config.yaml.")

    rows: List[Dict[str, Any]] = []
    for s in cfg.stocks:
        code = str(s.code).zfill(6)
        name = get_stock_name(code)
        start_trade_date: Optional[str] = None
        end_trade_date: Optional[str] = None
        try:
            # Derive per-stock trading window to handle newly listed stocks properly
            start_trade_date, end_trade_date = derive_trade_window_from_prices(code, cfg.start_date, cfg.end_date)
            res = compute_interval_total_return(code, start_trade_date, end_trade_date)

            # Recompute additional shares and description explicitly to ensure presence in output
            try:
                from .ak_client import sum_additional_shares_in_interval
                add_shares, add_count, add_desc = sum_additional_shares_in_interval(code, start_trade_date, end_trade_date)
            except Exception:
                add_shares, add_count, add_desc = 0.0, 0, ""

            # Recompute total_return using explicit additional value to ensure consistency
            total_return = None
            try:
                end_close_val = res.end_close
                start_close_val = res.start_close
                div_sum_val = res.dividend_sum_per_share
                add_value_per_share = end_close_val * add_shares
                total_return = (end_close_val + div_sum_val + add_value_per_share - start_close_val) / start_close_val
            except Exception:
                total_return = res.total_return

            # Compute annualized return based on calendar days
            try:
                days = (datetime.strptime(end_trade_date, "%Y-%m-%d") - datetime.strptime(start_trade_date, "%Y-%m-%d")).days
                annualized = None
                if days and days > 0 and total_return is not None:
                    annualized = (1.0 + total_return) ** (365.0 / days) - 1.0
            except Exception:
                annualized = None

            row = res.as_dict()
            row["name"] = name
            row["code"] = code
            row["additional_shares_per_share"] = add_shares
            row["additional_event_count"] = add_count
            row["additional_value_per_share"] = res.end_close * add_shares
            row["bonus_allot_desc"] = add_desc
            row["total_return"] = total_return
            row["annualized_return"] = annualized
            rows.append(row)
        except Exception as e:
            rows.append({
                "name": name,
                "code": code,
                "start_trade_date": start_trade_date,
                "end_trade_date": end_trade_date,
                "start_close": None,
                "end_close": None,
                "div_sum_per_share": None,
                "div_event_count": None,
                "total_return": None,
                "annualized_return": None,
                "error": str(e),
            })

    # Print console summary
    header = [
        "name",
        "start_trade_date",
        "end_trade_date",
        "start_close",
        "end_close",
        "div_sum_per_share",
        "div_event_count",
        "total_return_pct",
        "annualized_return_pct",
        "bonus_allot_desc",
        "error",
    ]
    print(",".join(header))
    for r in rows:
        total_return_pct = ""
        annualized_return_pct = ""
        if r.get("total_return") is not None:
            total_return_pct = f"{r['total_return'] * 100:.4f}%"
        if r.get("annualized_return") is not None:
            annualized_return_pct = f"{r['annualized_return'] * 100:.4f}%"
        line = [
            r.get("name", ""),
            r.get("start_trade_date", ""),
            r.get("end_trade_date", ""),
            "" if r.get("start_close") is None else f"{r['start_close']:.4f}",
            "" if r.get("end_close") is None else f"{r['end_close']:.4f}",
            "" if r.get("div_sum_per_share") is None else f"{r['div_sum_per_share']:.4f}",
            "" if r.get("div_event_count") is None else str(r["div_event_count"]),
            total_return_pct,
            annualized_return_pct,
            r.get("bonus_allot_desc", ""),
            r.get("error", ""),
        ]
        print(",".join(line))

    # Save CSV
    out_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(out_dir, f"summary_{ts}.csv")
    df = pd.DataFrame(rows)
    # For CSV, also include percent as decimal for easier processing
    df["total_return_pct"] = df["total_return"] * 100.0
    df["annualized_return_pct"] = df["annualized_return"] * 100.0
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    print(f"Saved CSV: {csv_path}")
    return {"rows": rows, "csv_path": csv_path}


if __name__ == "__main__":
    # Allow running as: PYTHONPATH=src python -m totalreturn.cli
    run()
