# REPORT

- genere: 2026-09-22T16:41:23
- statut GLOBAL: GREEN
- sources JSON lus: 4/4

## Gate quality (F1 / precision / recall / faux-instant)

| gate | F1 | precision | recall | faux-instant |
|---|---|---|---|---|
| gate_retrained@0.65 | 0.6061 | 0.4545 | 0.9091 | 0.5455 |
| gate_toy@0.65 | 0.069 | 0.1429 | 0.0455 | 0.8571 |
| logistic_regression | 0.8444 | 0.8261 | 0.8636 | 0.1739 |
| len baseline (len_lt_12_words) | 0.6567 | 0.4889 | 1 | 0.5111 |

## E2E (latence us, full_rate, token_cost)

| scenario | p50_us | p99_us | mean_us | full_rate | token_cost |
|---|---|---|---|---|---|
| always_full | 1534 | 2625 | 1608 | 1 | 179397 |
| always_fast | 19.3 | 64.41 | 20.18 | 0 | 0 |
| gated | 246 | 1944 | 878.8 | 0.4587 | 80333 |
| gated_lr | 1638 | 2193 | 1332 | 0.6606 | 119964 |

- savings: latence 45.4% / tokens 55.2% vs always_full

## WASM (median speedups)

| ratio | median |
|---|---|
| importheavy_vs_js_pkg | 0.4121 |
| importheavy_vs_js_alu | 0.08847 |
| freestanding_vs_js_alu | 0.2969 |

- import-heavy package WASM is 2.43x SLOWER than its own JS (median 0.41x) — env host-import overhead dominates; 0-import freestanding WASM is 0.30x vs JS ALU.

## WASM batch (median speedup js/wasm per N)

| N | speedup |
|---|---|
| 256 | 0.6154 |
| 4096 | 1.264 |
| 65536 | 1.1 |
| 1000000 | 1.136 |

- crossover N=4096 | batch WASM beats JS (>1.05x median) from N=4096 — boundary cost amortized.

## Multi-conf / verdict negatif

- quality_ok: True
- gate: 45.4% latency / 55.2% tokens vs always_full; false-instant conf=1.0 lr=0.0 vs always_fast=1.0

## SLM weights (shapes)

| key | shape |
|---|---|
| W | 16 |
| mu | 16 |
| sigma | 16 |
| W1 | 48 |
| b1 | 32 |
| W2 | 32 |
| b2 | 1 |
| lr | ['mu', 'sd', 'w', 'b'] |

## Tests

| test | exit | ok |
|---|---|---|
| eval_harness.py --self-check | 0 | OK |
| multi_conf.py | 0 | OK |
| test_slow_path.py | 0 | OK |
| test_intuition.py | 0 | OK |
| test_discover.py | 0 | OK |
| test_showcase.js | 0 | OK |
| wasm_bench.js | 0 | OK |
| wasm_batch_bench.js | 0 | OK |

### Extraits (first/last line)

- `eval_harness.py --self-check` exit=0 first='model                      prec    rec     F1  falseInst inst_rate' last='SELF-CHECK OK'
- `multi_conf.py` exit=0 first='self-check OK  (top-30% overlap scalar/current=1.00, risk@30 scalar=0.0% multi=0.0%)' last='re-run: python multi_conf.py'
- `test_slow_path.py` exit=0 first='OK test_paths_exist' last='3 tests passed'
- `test_intuition.py` exit=0 first='OK test_champions_match_ref' last='3 tests passed'
- `test_discover.py` exit=0 first='OK 8 kernels, all max_rel_err < 0.0001' last='OK 8 kernels, all max_rel_err < 0.0001'
- `test_showcase.js` exit=0 first='json ok 21 kernels; W1 48x32' last='ALL GREEN'
- `wasm_bench.js` exit=0 first='wasm_bench  n=100000 samples=100 warmup=5 passes=2  node=v24.13.0' last='report â†’ wasm_bench_report.json | checksum 1269556570.5185847'
- `wasm_batch_bench.js` exit=0 first='wasm_batch_bench  passes=2  node=v24.13.0' last='report â†’ wasm_batch_report.json | checksum 8185846.975385929'

## Next actions

1. Gate par defaut = logistic_regression (F1=0.8444) > retrained (F1=0.6061); faux-instant 0.1739 vs 0.5455
2. WASM batch: preferrer batch (N>=4096) — scalar ~0.3x, batch ~1-2x vs JS

## Changelog

- 2026-09-22T07:27:42 | GREEN | tests_ok=4/4 | delta: initial
- 2026-09-22T07:28:34 | GREEN | tests_ok=4/4 | delta: latency_savings_pct: 33->50.4
- 2026-09-22T07:46:45 | GREEN | tests_ok=4/4 | delta: latency_savings_pct: 50.4->54.5
- 2026-09-22T08:05:16 | GREEN | tests_ok=4/4 | delta: latency_savings_pct: 54.5->49
- 2026-09-22T08:07:46 | GREEN | tests_ok=4/4 | delta: latency_savings_pct: 49->45
- 2026-09-22T08:11:02 | GREEN | tests_ok=4/4 | delta: latency_savings_pct: 45->46.2
- 2026-09-22T08:13:56 | GREEN | tests_ok=4/4 | delta: latency_savings_pct: 46.2->55.4
- 2026-09-22T08:18:30 | GREEN | tests_ok=4/4 | delta: latency_savings_pct: 55.4->46.9; wasm_median_js_pkg: 0.3015->0.3614; wasm_median_js_alu: 0.06294->0.05956; wasm_median_freestanding: 0.3586->0.2536
- 2026-09-22T08:22:27 | GREEN | tests_ok=5/5 | delta: tests_ok: 4->5; latency_savings_pct: 46.9->48.9; wasm_median_js_pkg: 0.3614->0.3517; wasm_median_js_alu: 0.05956->0.07532; wasm_median_freestanding: 0.2536->0.4237
- 2026-09-22T08:24:51 | GREEN | tests_ok=5/5 | delta: latency_savings_pct: 48.9->47.2; wasm_median_js_pkg: 0.3517->0.3667; wasm_median_js_alu: 0.07532->0.0851; wasm_median_freestanding: 0.4237->0.3474; wasm_batch_crossover_n: -->4096
- 2026-09-22T08:26:26 | GREEN | tests_ok=7/7 | delta: tests_ok: 5->7; latency_savings_pct: 47.2->43.4; wasm_median_js_pkg: 0.3667->0.3743; wasm_median_js_alu: 0.0851->0.07988; wasm_median_freestanding: 0.3474->0.3927
- 2026-09-22T08:29:17 | GREEN | tests_ok=7/7 | delta: latency_savings_pct: 43.4->46.5; wasm_median_js_pkg: 0.3743->0.403; wasm_median_js_alu: 0.07988->0.08239; wasm_median_freestanding: 0.3927->0.3401
- 2026-09-22T08:35:28 | GREEN | tests_ok=8/8 | delta: tests_ok: 7->8; latency_savings_pct: 46.5->45.1; wasm_median_js_pkg: 0.403->0.3832; wasm_median_js_alu: 0.08239->0.08744; wasm_median_freestanding: 0.3401->0.3465
- 2026-09-22T08:36:34 | GREEN | tests_ok=8/8 | delta: latency_savings_pct: 45.1->43.8; wasm_median_js_pkg: 0.3832->0.3781; wasm_median_js_alu: 0.08744->0.08216; wasm_median_freestanding: 0.3465->0.352
- 2026-09-22T08:39:45 | GREEN | tests_ok=8/8 | delta: latency_savings_pct: 43.8->45.3; wasm_median_js_pkg: 0.3781->0.3714; wasm_median_js_alu: 0.08216->0.07974; wasm_median_freestanding: 0.352->0.3498
- 2026-09-22T16:41:23 | GREEN | tests_ok=8/8 | delta: latency_savings_pct: 45.3->45.4; wasm_median_js_pkg: 0.3714->0.4121; wasm_median_js_alu: 0.07974->0.08847; wasm_median_freestanding: 0.3498->0.2969
