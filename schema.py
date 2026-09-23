# schema.py - minimal stdlib validator for JSON reports
from __future__ import annotations
from typing import Any


def validate(obj: Any, schema: Any, path: str = "") -> list[str]:
    """Validate nested dict/list against a dict/list schema."""
    if schema is None or obj is None:
        return []
    if isinstance(schema, type):
        if isinstance(obj, schema):
            return []
        return [path + ": expected " + schema.__name__ + ", got " + type(obj).__name__]
    if isinstance(schema, dict) and isinstance(obj, dict):
        errors: list[str] = []
        for k, v in schema.items():
            errors.extend(validate(obj.get(k), v, path + "." + k))
        return errors
    return []


SCHEMAS = {
    "eval_report.json": {"best_f1": float, "gate_retrained": {"f1": float},
                         "gate_toy": {"f1": float},
                         "baselines": {"logistic_regression": {"f1": float}}},
    "e2e_report.json": {"verdict": {"latency_savings_pct": float,
                                     "token_savings_pct": float},
                        "scenarios": {"gated_lr": {"p50_us": float}}},
    "wasm_bench_report.json": {"verdict": {"statement": str}},
    "wasm_batch_report.json": {"verdict": {"crossover_N": int,
                                            "median_speedup_per_n": dict}},
}
