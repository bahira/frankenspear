"""Jev vs IntuitionInstant — benchmark croise sur holdout n=48."""
from __future__ import annotations

import json
import sys
import time
from typing import Any

import httpx

from eval_harness import build_corpus, stratified_split
from intuition import IntuitionInstant

API_KEY = "apikey_2211b2c64e65775540cfb0e3494c985e68e7_d2736b39c7428af04adac95889b6767bcbae603675006a88e0a14cec187ea5c9"
SERVER = "https://api.typesafe.ai/v1/systemone"
HTTP = httpx.Client(timeout=15)


def call_jev(text: str) -> float:
    payload: dict[str, Any] = {
        "state": text,
        "model": "jev-latest",
        "questions": {
            "is_trivial": {
                "type": "noul",
                "instructions": "The message is a trivial prompt suitable for instant closed-form handling",
            }
        },
    }
    r = HTTP.post(
        SERVER,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        json=payload,
    )
    return float(r.json()["answers"]["is_trivial"]["noul"])


def fpr(labels: list[int], probs: list[float], thr: float) -> dict[str, float]:
    n = len(labels)
    tp = sum(1 for i in range(n) if probs[i] >= thr and labels[i] == 0)
    fp = sum(1 for i in range(n) if probs[i] >= thr and labels[i] == 1)
    fn = sum(1 for i in range(n) if probs[i] < thr and labels[i] == 0)
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2.0 * prec * rec / max(prec + rec, 1e-9)
    fi = fp / max(tp + fp, 1)
    return {"f1": f1, "fi": fi, "n": tp + fp}


def main() -> None:
    texts, y = build_corpus()
    _, te = stratified_split(y)
    texts_te = [texts[i] for i in te]
    y_te = [int(y[i]) for i in te]

    # Py — IntuitionInstant (local, numpy pur)
    layer = IntuitionInstant(seed=42, gate="lr")
    t0 = time.perf_counter_ns()
    routes = layer.route_batch(texts_te)
    py_us = (time.perf_counter_ns() - t0) / 1000.0 / max(len(texts_te), 1)
    py_probs = [float(layer.lr.predict_instant_proba(t)) if layer.lr else 0.0 for t in texts_te]
    py_m = fpr(y_te, py_probs, 0.5)

    # Jev — remote via httpx
    jv_probs: list[float] = []
    t0 = time.perf_counter_ns()
    for t in texts_te:
        jv_probs.append(call_jev(t))
    jv_ms = (time.perf_counter_ns() - t0) / 1000.0 / max(len(texts_te), 1)
    jv_m = fpr(y_te[:len(jv_probs)], jv_probs, 0.5) if all(p >= 0 for p in jv_probs) else None

    print(f"holdout={len(texts_te)}  n_jev={len(jv_probs)}")
    print(f"py   p50={py_us:.0f}us  f1={py_m['f1']:.4f}  fi={py_m['fi']:.4f}")
    if jv_m is not None:
        print(f"jev  p50={jv_ms:.1f}ms  f1={jv_m['f1']:.4f}  fi={jv_m['fi']:.4f}")
    HTTP.close()


if __name__ == "__main__":
    main()
