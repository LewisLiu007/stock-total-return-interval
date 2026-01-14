from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import List, Dict, Any

from flask import Flask, render_template, request, send_file, redirect, url_for, flash
import pandas as pd

# Ensure src is importable
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gui_app import compute_for_codes  # reuse the computation logic


app = Flask(
    __name__,
    template_folder=os.path.join(HERE, "templates"),
    static_folder=None,
)
app.secret_key = "totalreturn-secret"  # simple secret for flash messages

LAST_ROWS: List[Dict[str, Any]] = []


def parse_codes_input(text: str) -> List[str]:
    """
    Accept comma or space-separated names/codes. Let compute_for_codes do the mapping.
    Here we just pass-through; compute_for_codes handles name->code lookup internally.
    """
    parts = [p.strip() for p in text.replace("，", ",").replace(" ", ",").split(",") if p.strip()]
    return parts


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", rows=None, start_date="2019-01-01", end_date="")


@app.route("/calculate", methods=["POST"])
def calculate():
    stocks_text = request.form.get("stocks", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip() or None

    if not stocks_text:
        flash("Please enter at least one stock name or 6-digit code.")
        return redirect(url_for("index"))

    if not start_date:
        flash("Please enter a start date (YYYY-MM-DD).")
        return redirect(url_for("index"))

    codes_or_names = parse_codes_input(stocks_text)

    try:
        rows = compute_for_codes(codes_or_names, start_date, end_date)
    except Exception as e:
        flash(f"Error computing results: {e}")
        return redirect(url_for("index"))

    # cache for export
    global LAST_ROWS
    LAST_ROWS = rows

    # decorate with percent strings for display
    display_rows = []
    for r in rows:
        rr = dict(r)
        rr["total_return_pct"] = "" if r.get("total_return") is None else f"{r['total_return'] * 100:.4f}%"
        rr["annualized_return_pct"] = "" if r.get("annualized_return") is None else f"{r['annualized_return'] * 100:.4f}%"
        display_rows.append(rr)

    return render_template("index.html", rows=display_rows, start_date=start_date, end_date=end_date or "")


@app.route("/export", methods=["GET"])
def export():
    global LAST_ROWS
    if not LAST_ROWS:
        flash("No results to export. Please calculate first.")
        return redirect(url_for("index"))

    # Build CSV in a temp file
    out_dir = os.path.join(os.getcwd(), "output")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(out_dir, f"web_summary_{ts}.csv")
    df = pd.DataFrame(LAST_ROWS)
    df["total_return_pct"] = df["total_return"] * 100.0
    df["annualized_return_pct"] = df["annualized_return"] * 100.0
    df.to_csv(path, index=False, encoding="utf-8-sig")

    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


def main():
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
