# readme_sync.py — python readme_sync.py : sync README.md depuis REPORT.json (idempotent)
from __future__ import annotations
import json, os, re

def _n(p: str) -> str: return os.path.join(os.path.dirname(os.path.abspath(__file__)), p)

def main() -> None:
    rp = _n("REPORT.json")
    if not os.path.exists(rp): print("skipped (no REPORT.json)"); return
    with open(rp, encoding="utf-8") as f: rep = json.load(f)
    with open(_n("README.md"), encoding="utf-8") as f: md = f.read()
    def fmt(v): return f"{v:.4g}" if isinstance(v,float) else str(v or "-")
    g = rep.get("gate", {})
    lr = g.get("logistic_regression", {})
    n1 = fmt(lr.get("f1")), fmt(lr.get("precision")), fmt(lr.get("recall")), fmt(lr.get("false_instant_rate"))
    e = rep.get("e2e",{}).get("verdict",{})
    n2 = fmt(e.get("latency_savings_pct")), fmt(e.get("token_savings_pct")), fmt(e.get("false_instant_rate") or e.get("false_instant") or "")
    w = rep.get("wasm",{}).get("medians",{})
    n3 = "; ".join(f"{k}={fmt(v)}" for k,v in sorted(w.items())[:4]) if w else "-"
    for marker, val in (("gate",n1),("e2e",n2),("wasm",n3)):
        pat = re.compile(rf"(<!-- BEGIN {marker} -->.*?<!-- END {marker} -->)", re.DOTALL)
        m = pat.search(md)
        if m is not None:
            old = m.group(1); new = f"<!-- BEGIN {marker} -->\n{val}\n<!-- END {marker} -->"
            md = md.replace(old, new)
    with open(_n("README.md"), "w", encoding="utf-8") as f: f.write(md)
    print(f"README.md synced ({len(md)} chars)")

if __name__ == "__main__": main()
