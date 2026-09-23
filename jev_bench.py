"""Jev vs IntuitionInstant — benchmark croise sur corpus complet n=241."""
from __future__ import annotations

import json
import sys
import time
from typing import Any

import httpx

from eval_harness import build_corpus, ece_score
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
    y_list = [int(v) for v in y]
    yt = [1 if v == 0 else 0 for v in y_list]

    layer = IntuitionInstant(seed=42, gate="lr")
    py_probs = [float(layer.lr.predict_instant_proba(t)) if layer.lr else 0.0 for t in texts]
    py_m = fpr(y_list, py_probs, 0.5)

    jv_probs: list[float] = []
    for t in texts:
        jv_probs.append(call_jev(t))
    jv_m = fpr(y_list, jv_probs, 0.5)

    py_ece = ece_score(py_probs, yt)
    jv_ece = ece_score(jv_probs, yt)

    print(f"py  f1={py_m['f1']:.4f}  ece={py_ece:.4f}")
    print(f"jev f1={jv_m['f1']:.4f}  ece={jv_ece:.4f}")
    print(f"n={len(texts)}")
    HTTP.close()


if __name__ == "__main__":
    main()
