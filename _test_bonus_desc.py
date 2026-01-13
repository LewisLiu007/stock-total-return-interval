import akshare as ak
from src.totalreturn.ak_client import sum_additional_shares_in_interval
from src.totalreturn.config import load_config

def run():
    cfg = load_config()
    print("Testing bonus/transfer/allotment description for configured stocks...\n")
    for s in cfg.stocks:
        code = str(s.code).zfill(6)
        try:
            add_shares, add_count, desc = sum_additional_shares_in_interval(code, cfg.start_date, cfg.end_date or "")
            print(f"code={code} add_shares_per_share={add_shares:.6f} add_event_count={add_count}")
            print(f"desc: {desc}\n")
        except Exception as e:
            print(f"code={code} error: {e}\n")

if __name__ == "__main__":
    run()
