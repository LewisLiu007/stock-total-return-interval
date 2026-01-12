import akshare as ak

def test_hist():
    print("Testing stock_zh_a_hist for 600519 (daily, unadjusted)...")
    try:
        df = ak.stock_zh_a_hist(symbol="600519", period="daily", start_date="20210101", end_date="20210115", adjust="")
        print("hist shape:", df.shape)
        print("hist columns:", list(df.columns))
        print(df.head().to_string())
    except Exception as e:
        print("hist error:", e)

def test_dividends_per_stock():
    code = "600519"
    print("\nTesting dividends per-stock endpoints for", code, "...")

    print(" - stock_history_dividend_detail (Sina)")
    try:
        dv1 = ak.stock_history_dividend_detail(symbol=code, indicator="分红", date="")
        print("Sina shape:", dv1.shape)
        print("Sina columns:", list(dv1.columns))
        print(dv1.head().to_string())
    except Exception as e:
        print("Sina error:", e)

    print("\n - stock_fhps_detail_ths (THS fallback)")
    try:
        dv2 = ak.stock_fhps_detail_ths(symbol=code)
        print("THS shape:", dv2.shape)
        print("THS columns:", list(dv2.columns))
        print(dv2.head().to_string())
    except Exception as e:
        print("THS error:", e)

if __name__ == "__main__":
    test_hist()
    test_dividends_per_stock()
