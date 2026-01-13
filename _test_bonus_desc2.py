from src.totalreturn.config import load_config
from src.totalreturn.ak_client import derive_trade_window_from_prices, sum_additional_shares_in_interval

def run():
    cfg = load_config()
    print("Testing bonus/transfer/allotment description with proper start/end per stock...\n")
    for s in cfg.stocks:
        code = str(s.code).zfill(6)
        try:
            start_trade_date, end_trade_date = derive_trade_window_from_prices(code, cfg.start_date, cfg.end_date)
            add_shares, add_count, desc = sum_additional_shares_in_interval(code, start_trade_date, end_trade_date)
            print(f"code={code} start={start_trade_date} end={end_trade_date} add_shares_per_share={add_shares:.6f} add_event_count={add_count}")
            print(f"desc: {desc}\n")
        except Exception as e:
            print(f"code={code} error: {e}\n")

if __name__ == "__main__":
    run()
