# REPORT

- genere: 2026-09-22T22:22:06
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
| always_full | 5070 | 1.156e+04 | 5806 | 1 | 179397 |
| always_fast | 39.6 | 136.5 | 42.26 | 0 | 0 |
| gated | 871 | 8995 | 2780 | 0.4587 | 80333 |
| gated_lr | 4423 | 9260 | 3784 | 0.6606 | 119964 |

- savings: latence 82.8% / tokens 55.2% vs always_full

## WASM (median speedups)

| ratio | median |
|---|---|
| importheavy_vs_js_pkg | 0.335 |
| importheavy_vs_js_alu | 0.06468 |
| freestanding_vs_js_alu | 0.3686 |

- import-heavy package WASM is 2.98x SLOWER than its own JS (median 0.34x) — env host-import overhead dominates; 0-import freestanding WASM is 0.37x vs JS ALU.

## WASM batch (median speedup js/wasm per N)

| N | speedup |
|---|---|
| 256 | 0.7059 |
| 4096 | 1.452 |
| 65536 | 1.068 |
| 1000000 | 1.025 |

- crossover N=4096 | batch WASM beats JS (>1.05x median) from N=4096 — boundary cost amortized.

## Multi-conf / verdict negatif

- quality_ok: True
- gate: 82.8% latency / 55.2% tokens vs always_full; false-instant conf=1.0 lr=0.0 vs always_fast=1.0

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
| typecheck.py | 0 | OK |
| eval_harness.py --self-check | 0 | OK |
| multi_conf.py | 0 | OK |
| test_slow_path.py | 0 | OK |
| test_intuition.py | 0 | OK |
| test_reports.py | 0 | OK |
| test_discover.py | 0 | OK |
| test_showcase.js | 0 | OK |
| cov.py | 0 | OK |
| wasm_bench.js | 0 | OK |
| wasm_batch_bench.js | 0 | OK |

### Extraits (first/last line)

- `typecheck.py` exit=0 first='Success: no issues found in 8 source files' last='Success: no issues found in 8 source files'
- `eval_harness.py --self-check` exit=0 first='model                      prec    rec     F1  falseInst inst_rate' last='SELF-CHECK OK'
- `multi_conf.py` exit=0 first='self-check OK  (top-30% overlap scalar/current=1.00, risk@30 scalar=0.0% multi=0.0%)' last='re-run: python multi_conf.py'
- `test_slow_path.py` exit=0 first='OK test_paths_exist' last='3 tests passed'
- `test_intuition.py` exit=0 first='OK test_champions_match_ref' last='7 tests passed'
- `test_reports.py` exit=0 first='OK golden: wasm stable, e2e savings ok, eval n=241 lr>=0.80' last='1 tests passed'
- `test_discover.py` exit=0 first='OK 89 ids package' last='OK 61 kernels, all max_rel_err < 0.001'
- `test_showcase.js` exit=0 first='json ok 21 kernels; W1 48x32' last='ALL GREEN'
- `cov.py` exit=0 first='OK test_champions_match_ref' last='cov ok'
- `wasm_bench.js` exit=0 first='wasm_bench  n=100000 samples=100 warmup=5 passes=2  node=v24.13.0' last='report â†’ wasm_bench_report.json | checksum 1269556570.5185847'
- `wasm_batch_bench.js` exit=0 first='wasm_batch_bench  passes=2  node=v24.13.0' last='report â†’ wasm_batch_report.json | checksum 8185846.975385929'

## Next actions

1. Gate par defaut = logistic_regression (F1=0.8444) > retrained (F1=0.6061); faux-instant 0.1739 vs 0.5455
2. WASM batch: preferrer batch (N>=4096) — scalar ~0.3x, batch ~1-2x vs JS

## Changelog

- 2026-09-22T08:39:45 | GREEN | tests_ok=8/8 | delta: latency_savings_pct: 43.8->45.3; wasm_median_js_pkg: 0.3781->0.3714; wasm_median_js_alu: 0.08216->0.07974; wasm_median_freestanding: 0.352->0.3498
- 2026-09-22T16:41:23 | GREEN | tests_ok=8/8 | delta: latency_savings_pct: 45.3->45.4; wasm_median_js_pkg: 0.3714->0.4121; wasm_median_js_alu: 0.07974->0.08847; wasm_median_freestanding: 0.3498->0.2969
- 2026-09-22T17:10:19 | GREEN | tests_ok=8/8 | delta: latency_savings_pct: 45.4->55.9; wasm_median_js_pkg: 0.4121->0.3722; wasm_median_js_alu: 0.08847->0.0572; wasm_median_freestanding: 0.2969->0.3015
- 2026-09-22T17:14:29 | GREEN | tests_ok=8/8 | delta: latency_savings_pct: 55.9->37.9; wasm_median_js_pkg: 0.3722->0.3263; wasm_median_js_alu: 0.0572->0.07357; wasm_median_freestanding: 0.3015->0.3208
- 2026-09-22T17:19:57 | RED | tests_ok=8/9 | delta: status: GREEN->RED; latency_savings_pct: 37.9->67.7; wasm_median_js_pkg: 0.3263->0.4084; wasm_median_js_alu: 0.07357->0.08711; wasm_median_freestanding: 0.3208->0.2799
- 2026-09-22T17:24:16 | GREEN | tests_ok=9/9 | delta: status: RED->GREEN; tests_ok: 8->9; latency_savings_pct: 67.7->49.9; wasm_median_js_pkg: 0.4084->0.3562; wasm_median_js_alu: 0.08711->0.1048; wasm_median_freestanding: 0.2799->0.2935
- 2026-09-22T17:29:21 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 49.9->63.4; wasm_median_js_pkg: 0.3562->0.3225; wasm_median_js_alu: 0.1048->0.05369; wasm_median_freestanding: 0.2935->0.2877
- 2026-09-22T17:30:49 | RED | tests_ok=8/9 | delta: status: GREEN->RED; tests_ok: 9->8; latency_savings_pct: 63.4->7.5; wasm_median_js_pkg: 0.3225->0.3786; wasm_median_js_alu: 0.05369->0.07624; wasm_median_freestanding: 0.2877->0.372
- 2026-09-22T17:34:14 | GREEN | tests_ok=9/9 | delta: status: RED->GREEN; tests_ok: 8->9; latency_savings_pct: 7.5->49.2; wasm_median_js_pkg: 0.3786->0.3709; wasm_median_js_alu: 0.07624->0.06501; wasm_median_freestanding: 0.372->0.2889
- 2026-09-22T17:39:18 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 49.2->49.9; wasm_median_js_pkg: 0.3709->0.3784; wasm_median_js_alu: 0.06501->0.07043; wasm_median_freestanding: 0.2889->0.2237
- 2026-09-22T17:43:42 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 49.9->50.7; wasm_median_js_pkg: 0.3784->0.3741; wasm_median_js_alu: 0.07043->0.0675; wasm_median_freestanding: 0.2237->0.2642
- 2026-09-22T17:48:45 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 50.7->49.2; wasm_median_js_pkg: 0.3741->0.4095; wasm_median_js_alu: 0.0675->0.08364; wasm_median_freestanding: 0.2642->0.4096
- 2026-09-22T17:58:01 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 49.2->56.4; wasm_median_js_pkg: 0.4095->0.3754; wasm_median_js_alu: 0.08364->0.06111; wasm_median_freestanding: 0.4096->0.2055
- 2026-09-22T18:07:44 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 56.4->58.2; wasm_median_js_pkg: 0.3754->0.4443; wasm_median_js_alu: 0.06111->0.09052; wasm_median_freestanding: 0.2055->0.3128
- 2026-09-22T18:46:02 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 58.2->52.5; wasm_median_js_pkg: 0.4443->0.4019; wasm_median_js_alu: 0.09052->0.0705; wasm_median_freestanding: 0.3128->0.287
- 2026-09-22T21:18:25 | GREEN | tests_ok=9/9 | delta: latency_savings_pct: 52.5->57.2; wasm_median_js_pkg: 0.4019->0.3867; wasm_median_js_alu: 0.0705->0.07445; wasm_median_freestanding: 0.287->0.3729
- 2026-09-22T21:46:26 | GREEN | tests_ok=11/11 | delta: tests_ok: 9->11; latency_savings_pct: 57.2->58.3; wasm_median_js_pkg: 0.3867->0.2865; wasm_median_js_alu: 0.07445->0.04263; wasm_median_freestanding: 0.3729->0.2473
- 2026-09-22T21:54:58 | RED | tests_ok=7/11 | delta: status: GREEN->RED; tests_ok: 11->7; latency_savings_pct: 58.3->55.6; wasm_median_js_pkg: 0.2865->0.3279; wasm_median_js_alu: 0.04263->0.05761; wasm_median_freestanding: 0.2473->0.3529
- 2026-09-22T22:10:27 | RED | tests_ok=8/11 | delta: tests_ok: 7->8; latency_savings_pct: 55.6->38.2; wasm_median_js_pkg: 0.3279->0.3253; wasm_median_js_alu: 0.05761->0.04072; wasm_median_freestanding: 0.3529->0.3523
- 2026-09-22T22:22:06 | GREEN | tests_ok=11/11 | delta: status: RED->GREEN; tests_ok: 8->11; latency_savings_pct: 38.2->82.8; wasm_median_js_pkg: 0.3253->0.335; wasm_median_js_alu: 0.04072->0.06468; wasm_median_freestanding: 0.3523->0.3686
