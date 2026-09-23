import json, subprocess, sys
import numpy as np
from eval_harness import build_corpus, stratified_split, fit_lr, ece_score
from intuition import (IntuitionInstant, features_from_text, _features_uncached,
                       LogisticGate, _golden_nll)

# T1: jev_bench in run_all.py
src = open('run_all.py', encoding='utf-8').read()
if 'jev_bench' not in src:
    src = src.replace(
        '["python", "readme_sync.py"],',
        '["python", "readme_sync.py"],\n    ["python", "jev_bench.py"],'
    )
    open('run_all.py', 'w', encoding='utf-8').write(src)
    print("T1: jev_bench in run_all")

# T4: sync README via readme_sync.py
subprocess.run(["python", "readme_sync.py"], capture_output=True, text=True)
print("T4: readme_sync ran")

# T2: extra features test — 16->19
def _extra_features(text: str) -> list[float]:
    t = (text or "").lower()
    open_p = t.count("(")
    close_p = t.count(")")
    ratio_parens = min(abs(open_p - close_p), 5.0) / 5.0
    nb_virgules = min(t.count(","), 10.0) / 10.0
    depth = 0
    max_depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
            max_depth = max(max_depth, depth)
        elif ch == ")":
            depth = max(0, depth - 1)
    profondeur_nid = min(max_depth, 5.0) / 5.0
    return [ratio_parens, nb_virgules, profondeur_nid]

# test extra features on corpus
texts, y = build_corpus()
f0 = features_from_text(texts[0])
extra = _extra_features(texts[0])
print(f"T2: dim={len(f0)} + {len(extra)} extras = {len(f0)+len(extra)}")

# T3: checksums for 4 JSON files
import hashlib, os
def md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

for fname in ["eval_report.json", "e2e_report.json", "wasm_bench_report.json", "wasm_batch_report.json"]:
    if os.path.exists(fname):
        print(f"T3: {fname} = {md5(fname)[:16]}")
    else:
        print(f"T3: {fname} MISSING")
