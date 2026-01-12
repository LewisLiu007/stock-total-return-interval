import inspect
import akshare as ak

candidates = []
for name in dir(ak):
    lname = name.lower()
    if not name.startswith("stock"):
        continue
    if any(k in lname for k in ["fhps", "fh", "div", "bonus", "gbbq", "cq", "right", "ex"]):
        obj = getattr(ak, name)
        if callable(obj):
            candidates.append(name)

print("Found candidate functions (count={}):".format(len(candidates)))
print(", ".join(sorted(candidates)))

print("\nSignatures:")
for name in sorted(candidates):
    obj = getattr(ak, name)
    try:
        sig = inspect.signature(obj)
    except Exception:
        sig = "(signature unavailable)"
    print(f"{name}: {sig}")
