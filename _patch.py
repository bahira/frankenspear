import re

# T18: __all__ in intuition.py
src = open('intuition.py', encoding='utf-8').read()
if '__all__' not in src:
    src = src.replace(
        'import numpy as np\nimport numpy.typing as npt\n',
        'import numpy as np\nimport numpy.typing as npt\n\n__all__ = [\n'
        '    "tanh_pade", "sigmoid_alu", "silu_alu", "gelu_quintic", "gelu_erf",\n'
        '    "gelu_fast_relu", "silu_fast_relu", "sigmoid_fast", "gaussian_cdf_fast",\n'
        '    "probit", "gauss_kernel", "lorentz_kernel", "concurrence_pure",\n'
        '    "chsh_correlation", "grover_amplitude", "qfi_dephasing", "lorentz_gamma",\n'
        '    "kelly_fraction", "rsi_momentum", "QUANTUM", "CHAMPIONS", "FAST",\n'
        '    "features_from_text", "get_cache_stats", "IntuitionInstant",\n'
        '    "SpearEmb", "TinyPolicy", "LogisticGate", "_lr_from_corpus", "_golden_nll",\n'
        '    "demo", "export_weights",\n]\n'
    )
    open('intuition.py', 'w', encoding='utf-8').write(src)
    print('T18 done')

# T19: cov.py seuils per fichier
src2 = open('cov.py', encoding='utf-8').read()
if 'THRESHOLDS' not in src2:
    old = 'pi = dict(rows).get("intuition.py", 0.0)\n    assert pi > 0.80, pi\n    print("cov ok")'
    new = 'THRESHOLDS: dict[str, float] = {"intuition.py": 0.80, "spear_fable.py": 0.70}\n'
    new += '    for fname, th in THRESHOLDS.items():\n'
    new += '        pct = dict(rows).get(fname, 0.0)\n'
    new += '        if pct < th:\n'
    new += '            raise SystemExit(fname + " coverage " + str(pct) + " < " + str(th))\n'
    new += '    print("cov ok")'
    src2 = src2.replace(old, new)
    open('cov.py', 'w', encoding='utf-8').write(src2)
    print('T19 done')

# T20: schema.py
open('schema.py', 'w', encoding='utf-8').write(
'''# schema.py - minimal stdlib validator for JSON reports
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
''')
print('T20 done')
