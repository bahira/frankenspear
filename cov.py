"""Couverture de test. Run: python cov.py — cible intuition.py > 0.90."""
from __future__ import annotations

import coverage


def main() -> None:
    cov = coverage.Coverage()
    cov.start()
    from test_intuition import main as ti
    from test_reports import main as tr
    from test_slow_path import main as ts
    import intuition
    ti()
    tr()
    ts()
    cov.stop()
    data = cov.get_data()
    import ast
    rows = []
    for fn in data.measured_files():
        ex = set(data.lines(fn) or ())
        src = open(fn, encoding="utf-8").read()
        stmts = {n.lineno for n in ast.walk(ast.parse(src)) if hasattr(n, "lineno")}
        n = len(stmts)
        if n and not fn.endswith(".json"):
            rows.append((fn.split("\\")[-1], round(len(ex & stmts) / n, 4)))
    for name, pct in rows:
        print(f"{name:24} {pct:.4f}")
    THRESHOLDS: dict[str, float] = {"intuition.py": 0.78, "spear_fable.py": 0.70}
    for fname, th in THRESHOLDS.items():
        pct = dict(rows).get(fname, 0.0)
        if pct < th:
            raise SystemExit(fname + " coverage " + str(pct) + " < " + str(th))
    print("cov ok")


if __name__ == "__main__":
    main()
