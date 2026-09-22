"""metrics.csv flattener: eval + e2e + wasm + batch -> 1 table cle,valeur."""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows():
    out = []

    def add(section, key, val):
        if val is not None:
            out.append({"section": section, "key": key, "value": val})

    ev = json.loads((HERE / "eval_report.json").read_text(encoding="utf-8"))
    for sec in ("gate_retrained", "gate_toy"):
        for k, v in ev.get(sec, {}).items():
            if isinstance(v, (int, float)):
                add("gate", f"{sec}.{k}", v)
    for name, m in ev.get("baselines", {}).items():
        for k in ("f1", "false_instant_rate"):
            if isinstance(m.get(k), (int, float)):
                add("gate", f"{name}.{k}", m[k])
    e2 = json.loads((HERE / "e2e_report.json").read_text(encoding="utf-8"))
    for k, v in e2.get("verdict", {}).items():
        if isinstance(v, (int, float)):
            add("e2e", k, v)
    w = json.loads((HERE / "wasm_bench_report.json").read_text(encoding="utf-8"))
    for k, v in (w.get("medians") or w.get("verdict") or {}).items():
        if isinstance(v, (int, float)):
            add("wasm_scalar", k, v)
    b = json.loads((HERE / "wasm_batch_report.json").read_text(encoding="utf-8"))
    for k, v in (b.get("verdict") or {}).items():
        if isinstance(v, (int, float)):
            add("wasm_batch", k, v)
    return out


def main():
    rs = rows()
    with open(HERE / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=("section", "key", "value"))
        w.writeheader()
        w.writerows(rs)
    print(f"metrics.csv: {len(rs)} lignes")


if __name__ == "__main__":
    main()
