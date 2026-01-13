import akshare as ak
from datetime import datetime
from src.totalreturn.ak_client import derive_trade_window_from_prices

def main():
    code = "001220"
    print(f"Testing data availability for code {code}...\n")

    # 1) Try fetching a narrow 2019 range (likely before listing if no data)
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20190101", end_date="20190115", adjust="")
        print("2019-01-01 ~ 2019-01-15 hist:")
        print("  shape:", df.shape)
        if not df.empty:
            print("  head:\n", df.head().to_string())
        else:
            print("  empty DataFrame (no data in this range)")
    except Exception as e:
        print("  error fetching 2019 range:", e)

    # 2) Fetch a broad range to find earliest available trading date for this code
    try:
        today_str = datetime.today().strftime("%Y%m%d")
        df_full = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="19900101", end_date=today_str, adjust="")
        print("\n1990-01-01 ~ today hist:")
        print("  shape:", df_full.shape)
        if not df_full.empty:
            date_col = "日期" if "日期" in df_full.columns else ("date" if "date" in df_full.columns else df_full.columns[0])
            earliest = df_full[date_col].min()
            latest = df_full[date_col].max()
            print(f"  earliest date: {earliest}, latest date: {latest}")
            print("  head:\n", df_full.head().to_string())
        else:
            print("  empty DataFrame (no data at all)")
    except Exception as e:
        print("  error fetching full range:", e)

    # 3) Fetch listing info via EastMoney individual info
    try:
        info_df = ak.stock_individual_info_em(symbol=code)
        print("\nstock_individual_info_em(item/value):")
        print(info_df.to_string())
        listing_rows = info_df.loc[info_df["item"].isin(["上市时间", "上市日期"])]
        if not listing_rows.empty:
            listing_date = listing_rows.iloc[0]["value"]
            print(f"  listing date: {listing_date}")
        else:
            print("  listing date not found in individual info response")
    except Exception as e:
        print("  error fetching individual info:", e)

    # 3b) Check presence in A-share code-name list and EM spot list
    try:
        code_map = ak.stock_info_a_code_name()
        present_map = False
        if code_map is not None and not code_map.empty:
            code_col = None
            for cand in ["证券代码", "A股代码"]:
                if cand in code_map.columns:
                    code_col = cand
                    break
            if code_col:
                code_map[code_col] = code_map[code_col].astype(str).str[-6:].str.zfill(6)
                present_map = not code_map.loc[code_map[code_col] == code].empty
        print("\nstock_info_a_code_name presence:", "FOUND" if present_map else "NOT FOUND")
    except Exception as e:
        print("  error fetching stock_info_a_code_name:", e)

    try:
        spot_df = ak.stock_zh_a_spot_em()
        present_spot = False
        if spot_df is not None and not spot_df.empty:
            code_col2 = None
            for cand in ["代码", "股票代码", "证券代码"]:
                if cand in spot_df.columns:
                    code_col2 = cand
                    break
            if code_col2:
                spot_df[code_col2] = spot_df[code_col2].astype(str).str[-6:].str.zfill(6)
                present_spot = not spot_df.loc[spot_df[code_col2] == code].empty
        print("stock_zh_a_spot_em presence:", "FOUND" if present_spot else "NOT FOUND")
    except Exception as e:
        print("  error fetching stock_zh_a_spot_em:", e)

    # 4) Use our function to derive a per-stock trading window from given start_date
    try:
        derived_start, derived_end = derive_trade_window_from_prices(code, "2019-01-01", None)
        print(f"\nderive_trade_window_from_prices with start_date=2019-01-01:")
        print(f"  derived start_trade_date: {derived_start}")
        print(f"  derived end_trade_date:   {derived_end}")
    except Exception as e:
        print("  error deriving trade window:", e)

    print("\nConclusion:")
    print("- If the earliest available date or listing date is AFTER 2019-01-02, then using a global start date of 2019-01-02 will fail for this code.")
    print("- The per-stock trade window should be used for recently listed codes to choose the first available trading date >= user-provided start_date.")

if __name__ == "__main__":
    main()
