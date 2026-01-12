import akshare as ak

def run():
    code = "600519"
    print("Testing stock_history_dividend_detail for", code)
    try:
        df = ak.stock_history_dividend_detail(symbol=code, indicator="分红", date="")
        print("shape:", df.shape)
        print("columns:", list(df.columns))
        print(df.head().to_string())
    except Exception as e:
        print("error calling stock_history_dividend_detail:", e)

    print("\\nTesting stock_fhps_detail_ths for", code)
    try:
        df2 = ak.stock_fhps_detail_ths(symbol=code)
        print("shape:", df2.shape)
        print("columns:", list(df2.columns))
        print(df2.head().to_string())
    except Exception as e:
        print("error calling stock_fhps_detail_ths:", e)

if __name__ == "__main__":
    run()
