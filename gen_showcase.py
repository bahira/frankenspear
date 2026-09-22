"""Regenerer le bloc id="bench" de showcase.html depuis les JSON. python gen_showcase.py"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    ev = json.loads((HERE / "eval_report.json").read_text(encoding="utf-8"))
    w = json.loads((HERE / "wasm_bench_report.json").read_text(encoding="utf-8"))
    b = json.loads((HERE / "wasm_batch_report.json").read_text(encoding="utf-8"))
    cal = ev.get("calibration", {})
    wr = w.get("results", {})
    batch = {}
    for kid, res in b.get("results", {}).items():
        batch[kid] = {}
        for n, cell in (res.get("ns") or {}).items():
            jsn, wsn = cell.get("js", {}).get("p50_ns_per_elem"), cell.get("wasm", {}).get("p50_ns_per_elem")
            batch[kid][n] = {"js": jsn, "wasm": wsn,
                             "sp": cell.get("speedup_js_over_wasm")}
    payload = {
        "calib": {"retrained": cal.get("retrained", {}).get("ece"),
                  "toy": cal.get("toy", {}).get("ece"),
                  "lr": cal.get("logistic_regression", {}).get("ece")},
        "batch": batch,
        "js_alu": {k: v["modes"]["js_alu"]["p50_ns"] for k, v in wr.items()},
        "freestanding": {k: v["modes"]["freestanding"]["p50_ns"] for k, v in wr.items()},
        "import_heavy": {k: v["modes"]["importheavy"]["p50_ns"] for k, v in wr.items()},
    }
    js = json.dumps(payload, separators=(",", ":"))
    html = (HERE / "showcase.html").read_text(encoding="utf-8")
    m = re.search(r'(<script type="application/json" id="bench">)([\s\S]*?)(</script>)', html)
    assert m is not None, "bench block not found"
    out = html[:m.start(2)] + js + html[m.end(2):]
    (HERE / "showcase.html").write_text(out, encoding="utf-8")
    print(f"bench block regenere ({len(js)} octets)")


if __name__ == "__main__":
    main()
