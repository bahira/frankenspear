"""Golden: checksums + metriques cles non-regressent. python test_reports.py"""
from __future__ import annotations

import json


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
    assert 0.50 <= v["latency_savings_pct"] / 100 <= 0.95
    assert 0.45 <= v["token_savings_pct"] / 100 <= 0.65
    assert v["gate_saves_latency"] and v["gate_saves_tokens"]
    assert v["false_instant_rate_gated_lr"] == 0.0
    assert v["quality_ok"] is True
    ev = load("eval_report.json")
    assert ev["meta"]["n"] == 241 and ev["meta"]["n_holdout"] == 48
    assert ev["baselines"]["logistic_regression"]["f1"] >= 0.80
    assert ev["gate_retrained"]["false_instant_rate"] <= 0.60
    print("OK golden: wasm stable, e2e savings ok, eval n=241 lr>=0.80")


def main():
    test_golden()
    from schema import SCHEMAS, validate
    assert not validate(load("eval_report.json"), SCHEMAS["eval_report.json"]), "schema eval_report.json"
    print("2 tests passed")


if __name__ == "__main__":
    main()
