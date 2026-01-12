import akshare as ak

def test(symbol):
    print(f"Testing stock_gbbq_ths with symbol={symbol!r} ...")
    try:
        df = ak.stock_gbbq_ths(symbol=symbol)
        print("shape:", df.shape)
        if df is not None and not df.empty:
            print("columns:", list(df.columns))
            print(df.head().to_string())
        else:
            print("empty dataframe")
    except Exception as e:
        print("error:", e)

if __name__ == "__main__":
    for sym in ["600519", "sh600519", "000001", "sz000001"]:
        test(sym)
