"""export_lr.py — fit LR gate (identique a eval_harness) puis MAJ slm-weights.json + showcase.html."""
from __future__ import annotations

import json
import re

import numpy as np

from eval_harness import build_corpus, stratified_split, fit_lr
from intuition import features_from_text


def fit_gate() -> dict:
    """Meme split 80/20 seed 42, normalisation mu/sd sur TRAIN, fit_lr epochs 400 lr 0.5."""
    texts, y = build_corpus()
    tr, _ = stratified_split(y)
    X = np.array([features_from_text(t) for t in texts], np.float32)
    Xtr, ytr = X[tr], y[tr]
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    w, b = fit_lr((Xtr - mu) / sd, (ytr == 0).astype(np.float64), epochs=400, lr=0.5)
    return {"mu": [float(v) for v in mu], "sd": [float(v) for v in sd],
            "w": [float(v) for v in w], "b": float(b)}


def p_trivial(lr: dict, text: str) -> float:
    f = np.asarray(features_from_text(text), np.float64)
    z = ((f - np.asarray(lr["mu"], np.float64)) / np.asarray(lr["sd"], np.float64)) \
        @ np.asarray(lr["w"], np.float64) + lr["b"]
    return float(1.0 / (1.0 + np.exp(-np.clip(z, -30, 30))))


def main() -> None:
    lr = fit_gate()
    with open("showcase.html", encoding="utf-8") as fh:
        html = fh.read()
    m = re.search(r'id="slm">([\s\S]*?)</script>', html)
    assert m, 'id="slm" block not found'
    slm = json.loads(m.group(1))
    slm["lr"] = lr
    payload = json.dumps(slm, ensure_ascii=False)
    with open("slm-weights.json", "w", encoding="utf-8") as f:
        json.dump(slm, f, ensure_ascii=False)
    html = html[:m.start(1)] + payload + html[m.end(1):]
    with open("showcase.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"lr dim: mu={len(lr['mu'])} sd={len(lr['sd'])} w={len(lr['w'])} b={lr['b']:.4f}")
    for t in ("salut", "écris une fonction gelu"):
        p = p_trivial(lr, t)
        print(f"lr {t!r} p_trivial={p:.3f} path={'instant' if p >= 0.5 else 'slow'}")
    print("wrote slm-weights.json + re-injected showcase.html")


if __name__ == "__main__":
    main()
