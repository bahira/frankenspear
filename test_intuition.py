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


def main() -> None:
    tests = (test_champions_match_ref, test_quantum, test_gate_lr_beats_conf)
    for t in tests:
        t()
        print(f"OK {t.__name__}")
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
