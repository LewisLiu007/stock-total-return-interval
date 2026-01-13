from src.totalreturn.calculator import compute_interval_total_return
from src.totalreturn.ak_client import derive_trade_window_from_prices

def run():
    code = "600809"
    start_trade_date, end_trade_date = derive_trade_window_from_prices(code, "2019-01-01", None)
    res = compute_interval_total_return(code, start_trade_date, end_trade_date)
    d = res.as_dict()
    print("IntervalResult.as_dict keys:", list(d.keys()))
    for k, v in d.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    run()
