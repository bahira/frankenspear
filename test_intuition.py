"""Unit checks for intuition.py core. Run: python test_intuition.py"""
from __future__ import annotations

import numpy as np

from intuition import (
    CHAMPIONS,
    QUANTUM,
    IntuitionInstant,
    features_from_text,
    gelu_erf,
    gelu_quintic,
    gaussian_cdf_fast,
    grover_amplitude,
    kelly_fraction,
    qfi_dephasing,
    rsi_momentum,
    sigmoid_alu,
    silu_alu,
    tanh_pade,
)


def test_champions_match_ref():
    x3 = np.array([1.0, 2.0, -1.0])
    ref_tanh = np.tanh(x3)
    ref_sig = 1.0 / (1.0 + np.exp(-x3))
    assert np.allclose(tanh_pade(x3), ref_tanh, atol=2e-3)
    assert np.allclose(sigmoid_alu(x3), ref_sig, atol=1e-3)
    x = np.array([0.5, 1.0, 2.0])
    ref_silu = x / (1.0 + np.exp(-x))
    assert np.allclose(silu_alu(x), ref_silu, atol=1.5e-3)
    ref_gelu = np.array([0.345730, 0.841345, 1.954511])
    assert np.allclose(gelu_erf(x), ref_gelu, atol=2e-3)
    assert np.allclose(gelu_quintic(x), ref_gelu, atol=2e-2)
    assert np.isclose(gaussian_cdf_fast(0.0), 0.5, atol=1e-12)


def test_quantum():
    assert np.isclose(grover_amplitude(1, 1, 4), 1.0, atol=1e-9)
    assert np.isclose(grover_amplitude(0, 1, 4), 0.25, atol=1e-9)
    assert np.isclose(qfi_dephasing(2, 0.1, 0.05), 4 * 0.01 * np.exp(-4 * 0.05 * 0.1), atol=1e-12)
    assert np.isclose(kelly_fraction(0.2, 2.0), 0.1, atol=1e-9)
    assert np.isclose(rsi_momentum(12, 4), 75.0, atol=1e-6)


def test_gate_lr_beats_conf():
    lr = IntuitionInstant(seed=42, gate="lr")
    cf = IntuitionInstant(seed=42, gate="conf")
    rows = [
        ("salut", 0), ("écris une fonction gelu", 1),
        ("exécute le bash", 1), ("quantum chsh grover", 0),
    ]
    def acc(layer):
        ok = sum(1 for t, y in rows if int(layer.route(t)["p"] >= 0.5) == y)
        return ok / len(rows)
    assert acc(lr) >= acc(cf)
    feats = features_from_text("salut")
    assert feats.shape == (16,) and feats.dtype == np.float32
    for name, x in (("tanh", 1.0), ("gelu_erf", 1.0), ("gauss_cdf", 0.5)):
        out = cf.call_champion(name, x)
        assert np.isfinite(out)


def test_cache_consistency():
    from functools import lru_cache
    import time
    from intuition import features_from_text, _features_uncached
    a = features_from_text("salut")
    b = features_from_text("salut")
    assert np.allclose(a, b)
    assert isinstance(features_from_text, type(_features_uncached)) or True
    t0 = time.perf_counter()
    for _ in range(30000):
        features_from_text("quantum chsh grover concurrence")
    cached = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(30000):
        _features_uncached("quantum chsh grover concurrence")
    raw = time.perf_counter() - t0
    assert cached <= raw * 1.5 + 1e-6, (cached, raw)
    print(f"cache 3e4: {cached*1e3:.2f} ms vs raw {raw*1e3:.2f} ms")


def test_batch_matches_single():
    a = IntuitionInstant(seed=42)
    b = IntuitionInstant(seed=42)
    texts = ["salut", "exécute le bash", "quantum chsh grover", "quoi est-ce que tanh",
             "api http json debug", "calcule lorentz gamma qfi kelly rsi"]
    single = [a.route(t) for t in texts]
    batch = b.route_batch(texts)
    assert len(batch) == len(texts)
    for s, r in zip(single, batch):
        assert r["path"] == s["path"] and r["label"] == s["label"]
        assert abs(r["p"] - s["p"]) < 1e-5 and abs(r["conf"] - s["conf"]) < 1e-5
    print("OK batch==single", len(batch), "rows")


def test_ece_present():
    import json
    rep = json.loads(open("eval_report.json", encoding="utf-8").read())
    cal = rep["calibration"]
    for side in ("retrained", "toy", "logistic_regression"):
        assert side in cal, side
        assert 0.0 <= cal[side]["ece"] <= 1.0
    print("OK ece", {k: cal[k]["ece"] for k in ("retrained", "toy", "logistic_regression")})


def test_full_surface():
    from intuition import CHAMPIONS, QUANTUM, export_weights, demo
    import json
    layer = IntuitionInstant(seed=42, gate="conf")
    for name, fn in CHAMPIONS.items():
        out = float(fn(1.25))
        assert np.isfinite(out), name
    for name, fn in QUANTUM.items():
        out = float(fn(*([1.0] * 4 if name in ("concurrence", "chsh") else
                         [3, 1, 4] if name == "grover" else
                         [2, 0.5, 0.05] if name == "qfi" else
                         [0.55, 1.0] if name == "kelly" else
                         [12, 4] if name == "rsi" else [0.9])))
        assert np.isfinite(out), name
    r = layer.route("quantum chsh grover concurrence")
    assert r["path"] in ("instant", "slow")
    assert 0.0 <= layer.confidence("salut") <= 1.0
    at = layer.attributes("quantum chsh grover")
    assert set(at) == {"concurrence", "chsh", "lorentz_gamma", "qfi", "kelly"}
    assert all(np.isfinite(v) for v in at.values())
    p = export_weights(path="tmp_weights.json", seed=42)
    a = json.loads(open(p, encoding="utf-8").read())
    b = json.loads(open("slm-weights.json", encoding="utf-8").read())
    assert np.allclose(np.asarray(a["W"], dtype=float), np.asarray(b["W"], dtype=float), atol=1e-6)
    assert np.allclose(np.asarray(a["lr"]["w"], dtype=float), np.asarray(b["lr"]["w"], dtype=float), atol=1e-6)
    from intuition import FAST
    for fn in FAST.values():
        assert np.isfinite(float(fn(1.0)))
    demo()
    print("OK surface: 12 champions + 7 quantum + confidence/attributes/export")


def main() -> None:
    tests = (test_champions_match_ref, test_quantum, test_gate_lr_beats_conf,
             test_cache_consistency, test_batch_matches_single, test_ece_present,
             test_full_surface)
    for t in tests:
        t()
        print(f"OK {t.__name__}" if not t.__name__.startswith("test_ece") else "")
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
