# schema.py — validation stdlib des 5 JSON reports
from __future__ import annotations

from typing import Any


def validate(obj: Any, schema: Any, path: str = "") -> list[str]:
    if isinstance(schema, type):
        return [] if isinstance(obj, schema) else [f"{path}: expected {schema.__name__} got {type(obj).__name__}"]
    if isinstance(schema, list) and len(schema) == 1:
        return sum([validate(obj[i], schema[0], f"{path}[{i}]") for i in range(min(len(obj), 1)) if isinstance(obj, list)], [])
    if isinstance(schema, dict) and isinstance(obj, dict):
        return sum([validate(obj.get(k), v, f"{path}.{k}") for k, v in schema.items()], [])
    if schema is None:
        return []
    return []


SCHEMAS = {
    "eval_report.json": {
        "meta": {"n": int, "n_holdout": int},
        "gate_retrained": {"f1": float},
        "gate_toy": {"f1": float},
        "baselines": {"logistic_regression": {"f1": float}},
    },
    "e2e_report.json": {
        "verdict": {"latency_savings_pct": float, "token_savings_pct": float},
        "scenarios": {"gated_lr": {"p50_us": float}},
    },
    "wasm_bench_report.json": {"verdict": {"statement": str}},
    "wasm_batch_report.json": {"verdict": {"crossover_N": int, "median_speedup_per_n": dict}},
}
