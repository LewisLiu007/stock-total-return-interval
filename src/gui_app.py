from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import pandas as pd
import akshare as ak

# Make sure src is importable if run from repo root
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from totalreturn.ak_client import (
    derive_trade_window_from_prices,
)
from totalreturn.calculator import compute_interval_total_return


def build_code_maps() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Build mappings between stock name and code using AkShare lists.
    Primary: stock_info_a_code_name (SSE/SZSE code-name).
    Fallback: stock_zh_a_spot_em (real-time A-share list).
    Returns (name_to_code, code_to_name).
    """
    name_to_code: Dict[str, str] = {}
    code_to_name: Dict[str, str] = {}

    # Primary mapping via code-name list
    try:
        df_map = ak.stock_info_a_code_name()
        if df_map is not None and not df_map.empty:
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
                for _, row in df_map.iterrows():
                    code = str(row[code_col]).zfill(6)
                    name = str(row[name_col]).strip()
                    if name:
                        name_to_code[name] = code
                        code_to_name[code] = name
    except Exception:
        pass

    # Fallback: real-time spot list
    if not name_to_code:
        try:
            spot_df = ak.stock_zh_a_spot_em()
            if spot_df is not None and not spot_df.empty:
                code_col2 = None
                for cand in ["代码", "股票代码", "证券代码", "code"]:
                    if cand in spot_df.columns:
                        code_col2 = cand
                        break
                name_col2 = None
                for cand in ["名称", "股票简称", "证券简称", "name"]:
                    if cand in spot_df.columns:
                        name_col2 = cand
                        break
                if code_col2 and name_col2:
                    spot_df[code_col2] = spot_df[code_col2].astype(str).str[-6:].str.zfill(6)
                    for _, row in spot_df.iterrows():
                        code = str(row[code_col2]).zfill(6)
                        name = str(row[name_col2]).strip()
                        if name:
                            # only set if not already present to prefer primary source
                            if name not in name_to_code:
                                name_to_code[name] = code
                            if code not in code_to_name:
                                code_to_name[code] = name
        except Exception:
            pass

    # Static fallback for common names to ensure web GUI works even if AkShare lists are empty
    static_map = {
        "贵州茅台": "600519",
        "五粮液": "000858",
        "洋河股份": "002304",
        "泸州老窖": "000568",
    }
    for nm, cd in static_map.items():
        if nm not in name_to_code:
            name_to_code[nm] = cd
        if cd not in code_to_name:
            code_to_name[cd] = nm

    return name_to_code, code_to_name


def parse_input_to_codes(text: str, name_to_code: Dict[str, str]) -> List[str]:
    """
    Parse user input text into a list of 6-digit codes.
    Accepts comma or space-separated stock names or codes.
    """
    if not text:
        return []
    parts = [p.strip() for p in text.replace("，", ",").replace(" ", ",").split(",") if p.strip()]
    codes: List[str] = []
    for p in parts:
        if p.isdigit() and len(p) <= 6:
            codes.append(p.zfill(6))
        else:
            # try name lookup
            code = name_to_code.get(p)
            if code:
                codes.append(code)
            else:
                # try case-insensitive match
                for k, v in name_to_code.items():
                    if k.lower() == p.lower():
                        codes.append(v)
                        break
    # deduplicate preserving order
    seen = set()
    res = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            res.append(c)
    return res


def resolve_to_code(text: str, name_to_code: Dict[str, str]) -> str | None:
    """
    Resolve user-provided input (name or code) into a 6-digit stock code.
    Strategy:
      - If it's digits: zfill(6)
      - Exact name match (case-sensitive)
      - Exact name match (case-insensitive)
      - Fuzzy: substring match (user input in known name, or known name in user input)
    Returns None if not resolvable.
    """
    if not isinstance(text, str) or not text.strip():
        return None
    s = text.strip()
    # digits -> code
    if s.isdigit() and len(s) <= 6:
        return s.zfill(6)
    # exact match
    code = name_to_code.get(s)
    if code:
        return code
    # case-insensitive exact
    sl = s.lower()
    for k, v in name_to_code.items():
        if k.lower() == sl:
            return v
    # substring match
    candidates: List[str] = []
    for k, v in name_to_code.items():
        if s in k or k in s:
            candidates.append(v)
    if candidates:
        # pick the first candidate for now
        return candidates[0]
    return None


def compute_additional_and_desc(code: str, start_trade_date: str, end_trade_date: str) -> Tuple[float, int, str]:
    """
    Compute additional shares (送股/转增/配股) and description using ak_client's function.
    """
    try:
        from totalreturn.ak_client import sum_additional_shares_in_interval
        add_shares, add_count, add_desc = sum_additional_shares_in_interval(code, start_trade_date, end_trade_date)
        return float(add_shares), int(add_count), add_desc
    except Exception:
        return 0.0, 0, ""


def compute_for_codes(codes: List[str], start_date: str, end_date: str | None) -> List[Dict[str, Any]]:
    """
    Compute interval results for the given codes using the same logic as CLI:
      - derive per-stock window
      - compute unadjusted closes and cash dividends
      - compute additional shares and description
      - recompute total_return and annualized_return
    Returns list of row dicts.
    """
    name_to_code, code_to_name = build_code_maps()

    # Normalize mixed input (names or codes) into 6-digit codes, collect unresolved items
    normalized: List[Tuple[str, str]] = []
    unresolved_items: List[str] = []
    for item in codes:
        s = str(item).strip()
        rc = resolve_to_code(s, name_to_code)
        if rc:
            normalized.append((rc, s))
        else:
            unresolved_items.append(s)

    rows: List[Dict[str, Any]] = []
    # Emit error rows for unresolved items
    for s in unresolved_items:
        rows.append({
            "name": s,
            "code": "",
            "start_trade_date": None,
            "end_trade_date": None,
            "start_close": None,
            "end_close": None,
            "div_sum_per_share": None,
            "div_event_count": None,
            "additional_shares_per_share": None,
            "additional_event_count": None,
            "additional_value_per_share": None,
            "bonus_allot_desc": "",
            "total_return": None,
            "annualized_return": None,
            "error": "Unknown stock name or code",
        })

    # Robust name resolution via CLI's get_stock_name if available
    try:
        from totalreturn.cli import get_stock_name as _get_name
    except Exception:
        _get_name = None

    for code, input_label in normalized:
        name = _get_name(code) if _get_name else code_to_name.get(code, code)
        try:
            start_trade_date, end_trade_date = derive_trade_window_from_prices(code, start_date, end_date)
            res = compute_interval_total_return(code, start_trade_date, end_trade_date)

            # additional shares & description
            add_shares, add_count, add_desc = compute_additional_and_desc(code, start_trade_date, end_trade_date)
            add_value_per_share = res.end_close * add_shares

            # recompute total_return for consistency
            total_return = (res.end_close + res.dividend_sum_per_share + add_value_per_share - res.start_close) / res.start_close

            # annualized return
            try:
                days = (datetime.strptime(end_trade_date, "%Y-%m-%d") - datetime.strptime(start_trade_date, "%Y-%m-%d")).days
                annualized = (1.0 + total_return) ** (365.0 / days) - 1.0 if days and days > 0 else None
            except Exception:
                annualized = None

            row = res.as_dict()
            row["name"] = name
            row["code"] = code
            row["additional_shares_per_share"] = add_shares
            row["additional_event_count"] = add_count
            row["additional_value_per_share"] = add_value_per_share
            row["bonus_allot_desc"] = add_desc
            row["total_return"] = total_return
            row["annualized_return"] = annualized
            rows.append(row)
        except Exception as e:
            rows.append({
                "name": name,
                "code": code,
                "start_trade_date": None,
                "end_trade_date": None,
                "start_close": None,
                "end_close": None,
                "div_sum_per_share": None,
                "div_event_count": None,
                "additional_shares_per_share": None,
                "additional_event_count": None,
                "additional_value_per_share": None,
                "bonus_allot_desc": "",
                "total_return": None,
                "annualized_return": None,
                "error": str(e),
            })
    return rows


class TotalReturnGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("A-Share Interval Total Return (Unadjusted + Cash Dividends + Bonus/Allotment)")
        self.root.geometry("1000x600")

        self.name_to_code, self.code_to_name = build_code_maps()

        # Input frame
        frm_in = ttk.LabelFrame(root, text="Input")
        frm_in.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frm_in, text="Stocks (name or 6-digit codes; comma-separated):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.entry_stocks = ttk.Entry(frm_in, width=80)
        self.entry_stocks.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(frm_in, text="Start Date (YYYY-MM-DD):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.entry_start = ttk.Entry(frm_in, width=20)
        self.entry_start.insert(0, "2019-01-01")
        self.entry_start.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(frm_in, text="End Date (YYYY-MM-DD; empty = previous trading day):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.entry_end = ttk.Entry(frm_in, width=20)
        self.entry_end.insert(0, "")
        self.entry_end.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        btn_calc = ttk.Button(frm_in, text="Calculate", command=self.on_calculate)
        btn_calc.grid(row=3, column=0, padx=5, pady=10)

        btn_export = ttk.Button(frm_in, text="Export CSV", command=self.on_export)
        btn_export.grid(row=3, column=1, padx=5, pady=10, sticky="w")

        # Results frame
        frm_out = ttk.LabelFrame(root, text="Results")
        frm_out.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = [
            "name", "code", "start_trade_date", "end_trade_date",
            "start_close", "end_close", "div_sum_per_share", "div_event_count",
            "additional_shares_per_share", "additional_event_count", "additional_value_per_share",
            "total_return_pct", "annualized_return_pct", "bonus_allot_desc", "error"
        ]
        self.tree = ttk.Treeview(frm_out, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120 if c not in ("bonus_allot_desc", "error") else 300, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Status
        self.status = ttk.Label(root, text="", foreground="blue")
        self.status.pack(fill=tk.X, padx=10, pady=5)

        self.rows: List[Dict[str, Any]] = []

    def on_calculate(self) -> None:
        try:
            stocks_text = self.entry_stocks.get().strip()
            start_date = self.entry_start.get().strip()
            end_date = self.entry_end.get().strip() or None

            codes = parse_input_to_codes(stocks_text, self.name_to_code)
            if not codes:
                messagebox.showerror("Input Error", "Please enter at least one valid stock name or 6-digit code.")
                return

            self.rows = compute_for_codes(codes, start_date, end_date)

            # clear tree
            for item in self.tree.get_children():
                self.tree.delete(item)

            # insert rows
            for r in self.rows:
                total_pct = "" if r.get("total_return") is None else f"{r['total_return'] * 100:.4f}%"
                annual_pct = "" if r.get("annualized_return") is None else f"{r['annualized_return'] * 100:.4f}%"
                vals = [
                    r.get("name", ""),
                    r.get("code", ""),
                    r.get("start_trade_date", ""),
                    r.get("end_trade_date", ""),
                    "" if r.get("start_close") is None else f"{r['start_close']:.4f}",
                    "" if r.get("end_close") is None else f"{r['end_close']:.4f}",
                    "" if r.get("div_sum_per_share") is None else f"{r['div_sum_per_share']:.4f}",
                    "" if r.get("div_event_count") is None else str(r["div_event_count"]),
                    "" if r.get("additional_shares_per_share") is None else f"{r['additional_shares_per_share']:.6f}",
                    "" if r.get("additional_event_count") is None else str(r["additional_event_count"]),
                    "" if r.get("additional_value_per_share") is None else f"{r['additional_value_per_share']:.4f}",
                    total_pct,
                    annual_pct,
                    r.get("bonus_allot_desc", ""),
                    r.get("error", ""),
                ]
                self.tree.insert("", tk.END, values=vals)

            self.status.config(text=f"Calculated {len(self.rows)} rows at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            messagebox.showerror("Runtime Error", str(e))

    def on_export(self) -> None:
        if not self.rows:
            messagebox.showerror("Export Error", "No results to export. Please run Calculate first.")
            return
        try:
            out_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(out_dir, f"gui_summary_{ts}.csv")
            df = pd.DataFrame(self.rows)
            df["total_return_pct"] = df["total_return"] * 100.0
            df["annualized_return_pct"] = df["annualized_return"] * 100.0
            df.to_csv(path, index=False, encoding="utf-8-sig")
            self.status.config(text=f"Exported CSV: {path}")
            messagebox.showinfo("Export", f"Saved CSV: {path}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))


def main():
    root = tk.Tk()
    app = TotalReturnGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
