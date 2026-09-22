# Architecture — Intuition Instant Layer

```
prompt
  |  features_from_text (16 dim, LRU cache 4096)          intuition.py:183
  v
SpearEmb.transform (normalise + W + 4 act. champions)     intuition.py:206
  |  z = xn @ W ; parts = [xn, silu(z), gauss(z), gelu(z), tanh(z)]
  v
TinyPolicy.predict_proba (40->32->1, tanh/sigmoid ALU)    intuition.py:230
  |  p in [0,1]
  v
gate (2 modes)                                            intuition.py:272,304
  |  conf : instant ssi label==0 et Phi(4|p-0.5|-1) >= 0.65
  |  lr   : P(trivial) = sigma(zw + b) >= 0.5
  v
instant : champion closed-form (12 Champions + 7 Quantum)
slow    : LLM complet (slow_path.py, offline si pas d'API)
```

## Signaux quantiques (attributes, intuition.py:369)
concurrence 2|ad-bc| · CHSH |e·m+e·o+p·m-p·o| · gamma=1/sqrt(1-b^2)
QFI N^2 t^2 e^{-N^2 g t} · Kelly f*=edge/odds · RSI 100-100/(1+u/d).

## Benches
- wasm_bench.js : ns/iter par variante (import-heavy, freestanding 0-import, js_alu)
- wasm_batch_bench.js : ns/elem, N={256,4096,65536,1e6}, median 2 passes, checksum
- e2e_bench.py : 4 scenarios, median 3 passes (p50/p99/mean), p50-based savings

## Flux de verification
run_all.py (16 etapes) -> typecheck.py -> intuition/demo -> eval -> e2e ->
3 tests python + wasm node + showcase -> cov -> export_csv -> make_report
(REPORT.md/JSON + changelog snapshot).
