"""mypy strict gate. Run: python typecheck.py"""
from __future__ import annotations

import sys

from mypy.main import main as mypy_main


def main() -> None:
    sys.argv = ["mypy", "--config-file", "mypy.ini"]
    code = mypy_main()
    print(f"mypy strict -> exit {code}")
    sys.exit(0 if not code else 1)


if __name__ == "__main__":
    main()
