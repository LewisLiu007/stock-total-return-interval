from __future__ import annotations

from typing import List, Dict, Any, Tuple

from src.gui_app import compute_for_codes
from src.totalreturn.config import load_config
from src.totalreturn.cli import run as cli_run


def key_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    """Extract comparable fields from a row dict."""
    return {
        "code": row.get("code"),
        "name": row.get("name"),
        "start_trade_date": row.get("start_trade_date"),
        "end_trade_date": row.get("end_trade_date"),
        "start_close": row.get("start_close"),
        "end_close": row.get("end_close"),
        "div_sum_per_share": row.get("div_sum_per_share"),
        "div_event_count": row.get("div_event_count"),
        "additional_shares_per_share": row.get("additional_shares_per_share"),
        "additional_event_count": row.get("additional_event_count"),
        "additional_value_per_share": row.get("additional_value_per_share"),
        "bonus_allot_desc": row.get("bonus_allot_desc"),
        "total_return": row.get("total_return"),
        "annualized_return": row.get("annualized_return"),
        "error": row.get("error"),
    }


def approx_equal(a: Any, b: Any, tol: float = 1e-6) -> bool:
    try:
        if a is None and b is None:
            return True
        if a is None or b is None:
            return False
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return a == b


def compare_rows(gui_rows: List[Dict[str, Any]], cli_rows: List[Dict[str, Any]]) -> List[str]:
    """Compare per-code rows and return list of diff messages."""
    # Map by code
    gui_map = {r.get("code"): key_fields(r) for r in gui_rows}
    cli_map = {r.get("code"): key_fields(r) for r in cli_rows}

    diffs: List[str] = []
    codes = sorted(set(gui_map.keys()) | set(cli_map.keys()))
    for code in codes:
        g = gui_map.get(code)
        c = cli_map.get(code)
        if g is None:
            diffs.append(f"GUI missing code {code} present in CLI")
            continue
        if c is None:
            diffs.append(f"CLI missing code {code} present in GUI")
            continue

        # Compare important numeric fields
        checks = [
            ("start_trade_date", g["start_trade_date"], c["start_trade_date"]),
            ("end_trade_date", g["end_trade_date"], c["end_trade_date"]),
            ("start_close", g["start_close"], c["start_close"]),
            ("end_close", g["end_close"], c["end_close"]),
            ("div_sum_per_share", g["div_sum_per_share"], c["div_sum_per_share"]),
            ("div_event_count", g["div_event_count"], c["div_event_count"]),
            ("additional_shares_per_share", g["additional_shares_per_share"], c["additional_shares_per_share"]),
            ("additional_event_count", g["additional_event_count"], c["additional_event_count"]),
            ("additional_value_per_share", g["additional_value_per_share"], c["additional_value_per_share"]),
            ("total_return", g["total_return"], c["total_return"]),
            ("annualized_return", g["annualized_return"], c["annualized_return"]),
            ("bonus_allot_desc", g["bonus_allot_desc"], c["bonus_allot_desc"]),
            ("error", g["error"], c["error"]),
        ]
        for field, gv, cv in checks:
            eq = approx_equal(gv, cv) if field not in ("bonus_allot_desc", "error", "start_trade_date", "end_trade_date") else (gv == cv)
            if not eq:
                diffs.append(f"code {code} field {field} differs: GUI={gv} CLI={cv}")
    return diffs


def main():
    # Load codes and dates from config
    cfg = load_config()
    codes = [str(s.code).zfill(6) for s in cfg.stocks]
    start_date = cfg.start_date
    end_date = cfg.end_date

    # Compute via GUI logic (headless function)
    gui_rows = compute_for_codes(codes, start_date, end_date)

    # Compute via CLI logic
    cli_result = cli_run(None)
    cli_rows = cli_result["rows"]

    # Compare
    diffs = compare_rows(gui_rows, cli_rows)
    if not diffs:
        print("GUI vs CLI: All comparable fields match for all codes.")
    else:
        print("GUI vs CLI: Differences found:")
        for d in diffs:
            print(" -", d)


if __name__ == "__main__":
    main()
