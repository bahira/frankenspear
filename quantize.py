# quantize.py — python quantize.py : ecrit slm-weights-q8.json (scale=1000)
from __future__ import annotations

import json

SCALE = 1000


def _q(v):
    if isinstance(v, list):
        return [_q(x) for x in v]
    if isinstance(v, dict):
        return {k: _q(x) for k, x in v.items()}
    return int(round(v * SCALE))


def quantize(path: str = "slm-weights.json") -> str:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    out = {k: _q(v) for k, v in d.items()}
    out["scale"] = SCALE
    qpath = "slm-weights-q8.json"
    with open(qpath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return qpath


if __name__ == "__main__":
    p = quantize()
    print(f"wrote {p} (scale={SCALE})")
