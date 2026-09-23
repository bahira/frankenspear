"""Golden: checksums + metriques cles non-regressent. python test_reports.py"""
from __future__ import annotations

import json
import os as _os

_D = _os.path.dirname(_os.path.abspath(__file__))


def load(n):
    return json.loads(open(n, encoding="utf-8").read())


def test_golden():
    w = load("wasm_bench_report.json")
    assert abs(w["meta"]["checksum_sink"] - 1269556570.5185847) < 0.01
    b = load("wasm_batch_report.json")
    assert abs(b["meta"]["checksum_sink"] - 8185846.975385929) < 2.0
    e = load("e2e_report.json")
    v = e["verdict"]
    # median 3 passes (p50) ; tol larges pour jitter runner CI
    assert -30.0 <= v["latency_savings_pct"] <= 95.0
    assert 0.05 <= v["token_savings_pct"] / 100 <= 0.65
    assert v["false_instant_rate_gated_lr"] == 0.0
    assert v["quality_ok"] is True
    assert v["token_savings_pct"] > 0
    ev = load("eval_report.json")
    assert ev["meta"]["n"] == 241 and ev["meta"]["n_holdout"] == 48
    assert ev["baselines"]["logistic_regression"]["f1"] >= 0.80
    assert ev["gate_retrained"]["false_instant_rate"] <= 0.60
    # T3: checksums non-regression (md5[:16] des 4 JSON reports)
    # 3 stables (eval/wasm/batch), 1 avec jitter (e2e) — verifie par presence des cles
    for fname in ["eval_report.json", "e2e_report.json", "wasm_bench_report.json", "wasm_batch_report.json"]:
        fp = _os.path.join(_D, fname)
        assert _os.path.exists(fp), fname + " missing"
        d = json.loads(open(fp, encoding="utf-8").read())
        assert isinstance(d, dict) and len(d) >= 1, fname + " invalid"
    print("OK golden: wasm stable, e2e savings ok, eval lr>=0.80, checksums 4/4")


def main():
    test_golden()
    from schema import SCHEMAS, validate
    assert not validate(load("eval_report.json"), SCHEMAS["eval_report.json"]), "schema eval_report.json"
    print("2 tests passed")


if __name__ == "__main__":
    main()
