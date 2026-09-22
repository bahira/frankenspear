# make_report.py — aggregate existing JSON reports + run tests into REPORT.md/REPORT.json (stdlib only).
import json, os, subprocess, sys

D = os.path.dirname(os.path.abspath(__file__))
N = lambda p: os.path.join(D, p)
TIMEOUT = 60
TESTS = [
    ("typecheck.py", ["python", "typecheck.py"]),
    ("eval_harness.py --self-check", ["python", "eval_harness.py", "--self-check"]),
    ("multi_conf.py", ["python", "multi_conf.py"]),
    ("test_slow_path.py", ["python", "test_slow_path.py"]),
    ("test_intuition.py", ["python", "test_intuition.py"]),
    ("test_reports.py", ["python", "test_reports.py"]),
    ("test_discover.py", ["python", "test_discover.py"]),
    ("test_showcase.js", ["node", "test_showcase.js"]),
    ("cov.py", ["python", "cov.py"]),
    ("wasm_bench.js", ["node", "wasm_bench.js"]),
    ("wasm_batch_bench.js", ["node", "wasm_batch_bench.js"]),
]


def load(name):
    p = N(name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def useful(lines, idx):
    ls = [l for l in lines if l.strip()]
    return ls[idx] if ls else ""


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT, cwd=D)
        ls = ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines()
        return {"exit": r.returncode, "first": useful(ls, 0), "last": useful(ls, -1)}
    except Exception as e:
        return {"exit": None, "first": type(e).__name__, "last": str(e)[:120]}


def table(headers, rows):
    out = "| " + " | ".join(headers) + " |\n"
    out += "|" + "---|" * len(headers) + "\n"
    for r in rows:
        out += "| " + " | ".join(fmt(x) for x in r) + " |\n"
    return out


def snapshot(status, tests, e2e, wasm, batch=None):
    ev = (e2e or {}).get("verdict", {})
    wv = (wasm or {}).get("verdict", {})
    bv = (batch or {}).get("verdict", {})
    return {
        "status": status,
        "tests_ok": sum(1 for t in tests if t["ok"]),
        "tests_total": len(tests),
        "latency_savings_pct": ev.get("latency_savings_pct"),
        "token_savings_pct": ev.get("token_savings_pct"),
        "wasm_median_js_pkg": wv.get("median_importheavy_vs_js_pkg"),
        "wasm_median_js_alu": wv.get("median_imporheavy_vs_js_alu") or wv.get("median_importheavy_vs_js_alu"),
        "wasm_median_freestanding": wv.get("median_freestanding_vs_js_alu"),
        "wasm_batch_crossover_n": bv.get("crossover_N") or bv.get("crossover_n"),
        "wasm_batch_advantageous": bv.get("batch_wasm_advantageous"),
    }


def main():
    quiet = "--quiet" in sys.argv
    tests = [{"name": n, **run(c)} for n, c in TESTS]
    for t in tests:
        t["ok"] = (t["exit"] == 0)
    status = "GREEN" if all(t["ok"] for t in tests) else "RED"
    ts = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    ev = load("eval_report.json")
    e2e = load("e2e_report.json")
    wasm = load("wasm_bench_report.json")
    batch = load("wasm_batch_report.json")
    slm = load("slm-weights.json")
    sources = sum(1 for x in (ev, e2e, wasm, batch) if x)

    # gate table
    gr = (ev or {}).get("gate_retrained", {})
    gt = (ev or {}).get("gate_toy", {})
    bl = (ev or {}).get("baselines", {})
    lr = bl.get("logistic_regression", {})
    ln = bl.get("len_lt_12_words", {})
    gate_rows = [
        ["gate_retrained@0.65", gr.get("f1"), gr.get("precision"), gr.get("recall"), gr.get("false_instant_rate")],
        ["gate_toy@0.65", gt.get("f1"), gt.get("precision"), gt.get("recall"), gt.get("false_instant_rate")],
        ["logistic_regression", lr.get("f1"), lr.get("precision"), lr.get("recall"), lr.get("false_instant_rate")],
        ["len baseline (len_lt_12_words)", ln.get("f1"), ln.get("precision"), ln.get("recall"), ln.get("false_instant_rate")],
    ]

    # e2e table
    sc = (e2e or {}).get("scenarios", {})
    e2e_rows = []
    for name in ("always_full", "always_fast", "gated", "gated_lr"):
        s = sc.get(name, {})
        e2e_rows.append([name, s.get("p50_us"), s.get("p99_us"), s.get("mean_us"),
                         s.get("full_rate"), s.get("token_cost_proxy")])
    e2e_ver = (e2e or {}).get("verdict", {})

    # wasm table
    wv = (wasm or {}).get("verdict", {})
    bvv = (batch or {}).get("verdict", {})
    wasm_rows = [
        ["importheavy_vs_js_pkg", wv.get("median_importheavy_vs_js_pkg")],
        ["importheavy_vs_js_alu", wv.get("median_imporheavy_vs_js_alu") or wv.get("median_importheavy_vs_js_alu")],
        ["freestanding_vs_js_alu", wv.get("median_freestanding_vs_js_alu")],
    ]

    # next actions (derived)
    next = []
    if gr and lr:
        next.append(
            f"Gate par defaut = logistic_regression (F1={fmt(lr.get('f1'))}) > retrained (F1={fmt(gr.get('f1'))}); "
            f"faux-instant {fmt(lr.get('false_instant_rate'))} vs {fmt(gr.get('false_instant_rate'))}")
    if e2e_ver and not e2e_ver.get("quality_ok", True):
        next.append("Faux-instant gated=1.0 non-resolu: recalibrer seuil / enrichir features avant 1.0->~0.15")
    cr_n = bvv.get("crossover_N") or bvv.get("crossover_n")
    if cr_n:
        next.append(f"WASM batch: preferrer batch (N>={cr_n}) — scalar ~0.3x, batch ~1-2x vs JS")
    else:
        next.append("WASM: preferrer js_alu / freestanding 0-import (package importheavy ~3.3x plus lent que son propre JS)")
    next = next[:3]

    new_snap = snapshot(status, tests, e2e, wasm, batch)
    prev = load("REPORT.json")
    hist = (prev or {}).get("changelog", []) if prev else []
    delta = "initial"
    if hist:
        p = hist[-1]
        parts = []
        for k in ("status", "tests_ok", "latency_savings_pct", "token_savings_pct",
                  "wasm_median_js_pkg", "wasm_median_js_alu", "wasm_median_freestanding",
                  "wasm_batch_crossover_n"):
            if p.get(k) != new_snap.get(k):
                parts.append(f"{k}: {fmt(p.get(k))}->{fmt(new_snap.get(k))}")
        delta = "; ".join(parts) if parts else "identique"
    entry = {"generated_at": ts, "delta": delta, **new_snap}
    changelog = (hist + [entry])[-20:]

    # ---- REPORT.md ----
    md = f"# REPORT\n\n- genere: {ts}\n- statut GLOBAL: {status}\n- sources JSON lus: {sources}/4\n\n"
    md += "## Gate quality (F1 / precision / recall / faux-instant)\n\n"
    md += table(["gate", "F1", "precision", "recall", "faux-instant"], gate_rows) + "\n"
    md += "## E2E (latence us, full_rate, token_cost)\n\n"
    md += table(["scenario", "p50_us", "p99_us", "mean_us", "full_rate", "token_cost"], e2e_rows) + "\n"
    md += (f"- savings: latence {fmt(e2e_ver.get('latency_savings_pct'))}% / "
           f"tokens {fmt(e2e_ver.get('token_savings_pct'))}% vs always_full\n\n")
    md += "## WASM (median speedups)\n\n"
    md += table(["ratio", "median"], wasm_rows) + "\n"
    if wv.get("statement"):
        md += f"- {wv['statement']}\n\n"
    bvv = (batch or {}).get("verdict", {})
    if bvv:
        per_n = bvv.get("median_speedup_per_n", {})
        md += "## WASM batch (median speedup js/wasm per N)\n\n"
        md += table(["N", "speedup"], [[k, v] for k, v in per_n.items()]) + "\n"
        md += f"- crossover N={fmt(cr_n)} | {bvv.get('statement', '')}\n\n"
    md += "## Multi-conf / verdict negatif\n\n"
    md += f"- quality_ok: {e2e_ver.get('quality_ok')}\n"
    md += f"- {e2e_ver.get('summary', 'n/a')}\n\n"
    if slm:
        md += "## SLM weights (shapes)\n\n"
        md += table(["key", "shape"], [[k, len(v) if isinstance(v, list) else
                    (list(v.keys())[:6] if isinstance(v, dict) else v)] for k, v in slm.items()]) + "\n"
    md += "## Tests\n\n"
    md += table(["test", "exit", "ok"], [[t["name"], t["exit"], "OK" if t["ok"] else "FAIL"] for t in tests]) + "\n"
    md += "### Extraits (first/last line)\n\n"
    for t in tests:
        md += f"- `{t['name']}` exit={t['exit']} first={t['first']!r} last={t['last']!r}\n"
    md += "\n## Next actions\n\n"
    for i, a in enumerate(next, 1):
        md += f"{i}. {a}\n"
    md += "\n## Changelog\n\n"
    for e in changelog:
        md += f"- {e['generated_at']} | {e['status']} | tests_ok={e['tests_ok']}/{e['tests_total']} | delta: {e['delta']}\n"

    # ---- REPORT.json ----
    report = {
        "generated_at": ts,
        "status": status,
        "sources_read": sources,
        "gate": {
            "gate_retrained@0.65": {k: gr.get(k) for k in ("f1", "precision", "recall", "false_instant_rate")},
            "gate_toy@0.65": {k: gt.get(k) for k in ("f1", "precision", "recall", "false_instant_rate")},
            "logistic_regression": {k: lr.get(k) for k in ("f1", "precision", "recall", "false_instant_rate")},
            "len_baseline": {k: ln.get(k) for k in ("f1", "precision", "recall", "false_instant_rate")},
        },
        "e2e": {"scenarios": sc, "verdict": e2e_ver},
        "wasm": {"medians": {r[0]: r[1] for r in wasm_rows}, "statement": wv.get("statement")},
        "wasm_batch": {
            "median_speedup_per_n": bvv.get("median_speedup_per_n"),
            "crossover_n": bvv.get("crossover_N") or bvv.get("crossover_n"),
            "advantageous": bvv.get("batch_wasm_advantageous"),
            "statement": bvv.get("statement"),
        } if bvv else None,
        "tests": [{"name": t["name"], "exit": t["exit"], "ok": t["ok"]} for t in tests],
        "next": next,
        "changelog": changelog,
    }

    with open(N("REPORT.md"), "w", encoding="utf-8") as f:
        f.write(md)
    with open(N("REPORT.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    if not quiet:
        print(f"REPORT status={status} sources={sources}/4 tests_ok={new_snap['tests_ok']}/{len(tests)}")
    sys.exit(0 if sources >= 1 else 1)


if __name__ == "__main__":
    main()
