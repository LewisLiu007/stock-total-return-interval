from totalreturn.ak_client import _parse_cash_per_share_from_text

def approx_equal(a, b, tol=1e-9):
    return abs(a - b) <= tol

def run_tests():
    cases = [
        ("10派5元(含税)", 0.5),
        ("每10股派4.3元(含税)", 0.43),
        ("10送3股转2股派3元(含税)", 0.3),
        ("10派1.2元转4股", 0.12),
        ("每股派0.5元", 0.5),
        ("每股派息0.8元", 0.8),
        ("每10股派发现金红利5.5元", 0.55),
        ("不分配不转增", 0.0),
        ("10派0元", 0.0),
        ("每10股派  2 元", 0.2),  # spacing robustness
    ]
    passed = 0
    for i, (text, expected) in enumerate(cases, start=1):
        got = _parse_cash_per_share_from_text(text)
        ok = approx_equal(got, expected)
        print(f"Case {i}: text={text!r} -> got={got}, expected={expected} {'OK' if ok else 'FAIL'}")
        if ok:
            passed += 1
    print(f"\nPassed {passed}/{len(cases)} cases")
    if passed != len(cases):
        raise SystemExit(1)

if __name__ == "__main__":
    run_tests()
