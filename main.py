from __future__ import annotations

import os
import sys

def _ensure_src_on_path():
    here = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(here, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

def main():
    _ensure_src_on_path()
    from totalreturn.cli import run
    run()

if __name__ == "__main__":
    main()
