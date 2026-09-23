from __future__ import annotations

import numpy as np

import intuition


def test_fuzz():
    layer = intuition.IntuitionInstant(seed=42)
    texts = ["salut qui es-tu aide", "ecris gelu fibonacci code fonction",
             "execute lance bash tool run", "quantum chsh grover concurrence kernel math"]
    rng = np.random.RandomState(7)
    mots = ["tanh", "sigmoid", "silu", "gelu", "probit", "bash", "api", "json", "def", "script"]
    for _ in range(10):
        k = rng.randint(1, 15)
        texts.append(" ".join(str(rng.choice(mots)) for _ in range(int(k))))
    for t in texts:
        f = intuition.features_from_text(t)
        assert len(f) == 19, f"dim {len(f)}"
        r = layer.route(t)
        assert 0 <= r["p"] <= 1 and 0 <= r["conf"] <= 1
    rb = layer.route_batch(texts)
    for t, br in zip(texts, rb):
        sr = layer.route(t)
        assert sr["path"] == br["path"], f"parite scalar/batch sur {t[:30]}"
    print(f"test_fuzz OK ({len(texts)} prompts)")


if __name__ == "__main__":
    test_fuzz()
    print("ALL GREEN")
