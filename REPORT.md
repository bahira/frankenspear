# REPORT

- genere: 2026-09-23T07:17:25
- statut GLOBAL: GREEN
- sources JSON lus: 4/4

## Gate quality (F1 / precision / recall / faux-instant)

| gate | F1 | precision | recall | faux-instant |
|---|---|---|---|---|
| gate_retrained@0.65 | 0.6154 | 0.4651 | 0.9091 | 0.5349 |
| gate_toy@0.65 | 0.3871 | 0.6667 | 0.2727 | 0.3333 |
| logistic_regression | 0.8444 | 0.8261 | 0.8636 | 0.1739 |
| len baseline (len_lt_12_words) | 0.6567 | 0.4889 | 1 | 0.5111 |

## E2E (latence us, full_rate, token_cost)

| scenario | p50_us | p99_us | mean_us | full_rate | token_cost |
|---|---|---|---|---|---|
| always_full | 3075 | 6864 | 3582 | 1 | 180213 |
| always_fast | 32.2 | 84.31 | 31.59 | 0 | 0 |
| gated | 3518 | 7081 | 3715 | 0.9083 | 164225 |
| gated_lr | 3140 | 6161 | 2749 | 0.6606 | 120653 |

- savings: latence -2.1% / tokens 33% vs always_full

## WASM (median speedups)

| ratio | median |
|---|---|
| importheavy_vs_js_pkg | 0.3629 |
| importheavy_vs_js_alu | 0.07188 |
| freestanding_vs_js_alu | 0.3401 |

- import-heavy package WASM is 2.76x SLOWER than its own JS (median 0.36x) — env host-import overhead dominates; 0-import freestanding WASM is 0.34x vs JS ALU.

## WASM batch (median speedup js/wasm per N)

| N | speedup |
|---|---|
| 256 | 0.76 |
| 4096 | 1.326 |
| 65536 | 1.012 |
| 1000000 | 1.114 |

- crossover N=4096 | batch WASM beats JS (>1.05x median) from N=4096 — boundary cost amortized.

## Multi-conf / verdict negatif

- quality_ok: True
- gate: -2.1% latency / 33.0% tokens vs always_full; false-instant conf=0.0 lr=0.0 vs always_fast=1.0

## SLM weights (shapes)

| key | shape |
|---|---|
| W | 19 |
| mu | 19 |
| sigma | 19 |
| W1 | 51 |
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
| test_properties.py | 0 | OK |
| test_discover.py | 0 | OK |
| test_showcase.js | 0 | OK |
| cov.py | 0 | OK |
| gen_showcase.py | 0 | OK |
| changelog.py | 0 | OK |
| demo_agent.py | 0 | OK |
| wasm_bench.js | 0 | OK |
| wasm_batch_bench.js | 0 | OK |

### Extraits (first/last line)

- `typecheck.py` exit=0 first='Success: no issues found in 9 source files' last='Success: no issues found in 9 source files'
- `eval_harness.py --self-check` exit=0 first='model                      prec    rec     F1  falseInst inst_rate' last='SELF-CHECK OK'
- `multi_conf.py` exit=0 first='self-check OK  (top-30% overlap scalar/current=1.00, risk@30 scalar=0.0% multi=0.0%)' last='re-run: python multi_conf.py'
- `test_slow_path.py` exit=0 first='OK test_paths_exist' last='3 tests passed'
- `test_intuition.py` exit=0 first='OK test_champions_match_ref' last='9 tests passed'
- `test_reports.py` exit=0 first='OK golden: wasm stable, e2e savings ok, eval lr>=0.80, checksums 4/4' last='2 tests passed'
- `test_properties.py` exit=0 first='test_fuzz OK (14 prompts)' last='ALL GREEN'
- `test_discover.py` exit=0 first='OK 89 ids package' last='OK 61 kernels, all max_rel_err < 0.001'
- `test_showcase.js` exit=0 first='json ok 21 kernels; W1 48x32' last='ALL GREEN'
- `cov.py` exit=0 first='OK test_champions_match_ref' last='cov ok'
- `gen_showcase.py` exit=0 first='bench block regenere (1814 octets)' last='bench block regenere (1814 octets)'
- `changelog.py` exit=0 first='CHANGELOG.md (0 lignes)' last='CHANGELOG.md (0 lignes)'
- `demo_agent.py` exit=0 first='instant p=0.270 conf=0.449 cx=0.153 372.1us  salut qui es-tu aide' last='stats instant=3 slow=0'
- `wasm_bench.js` exit=0 first='wasm_bench  n=100000 samples=100 warmup=5 passes=2  node=v24.13.0' last='report â†’ wasm_bench_report.json | checksum 1269556570.5185847'
- `wasm_batch_bench.js` exit=0 first='wasm_batch_bench  passes=2  node=v24.13.0' last='report â†’ wasm_batch_report.json | checksum 8185846.975385929'

## Next actions

1. Gate par defaut = logistic_regression (F1=0.8444) > retrained (F1=0.6154); faux-instant 0.1739 vs 0.5349
2. WASM batch: preferrer batch (N>=4096) — scalar ~0.3x, batch ~1-2x vs JS

## Changelog

- 2026-09-23T02:15:01 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 81.6->79.8; wasm_median_js_pkg: 0.399->0.3416; wasm_median_js_alu: 0.08836->0.07861; wasm_median_freestanding: 0.3512->0.3537
- 2026-09-23T02:20:47 | RED | tests_ok=14/15 | delta: status: GREEN->RED; tests_ok: 15->14; latency_savings_pct: 79.8->74.3; wasm_median_js_pkg: 0.3416->0.4206; wasm_median_js_alu: 0.07861->0.08647; wasm_median_freestanding: 0.3537->0.355
- 2026-09-23T02:51:02 | RED | tests_ok=14/15 | delta: latency_savings_pct: 74.3->89.2; wasm_median_js_pkg: 0.4206->0.3884; wasm_median_js_alu: 0.08647->0.08028; wasm_median_freestanding: 0.355->0.3392
- 2026-09-23T02:56:14 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 14->15; latency_savings_pct: 89.2->81.8; wasm_median_js_pkg: 0.3884->0.392; wasm_median_js_alu: 0.08028->0.07365; wasm_median_freestanding: 0.3392->0.3248
- 2026-09-23T03:36:37 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 81.8->59.9; wasm_median_js_pkg: 0.392->0.3429; wasm_median_js_alu: 0.07365->0.04958; wasm_median_freestanding: 0.3248->0.1785
- 2026-09-23T03:43:10 | RED | tests_ok=14/15 | delta: status: GREEN->RED; tests_ok: 15->14; latency_savings_pct: 59.9->77.6; wasm_median_js_pkg: 0.3429->0.3781; wasm_median_js_alu: 0.04958->0.0614; wasm_median_freestanding: 0.1785->0.3578
- 2026-09-23T03:57:23 | RED | tests_ok=14/15 | delta: latency_savings_pct: 77.6->55.6; wasm_median_js_pkg: 0.3781->0.4539; wasm_median_js_alu: 0.0614->0.05362; wasm_median_freestanding: 0.3578->0.2183
- 2026-09-23T04:41:05 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 14->15; latency_savings_pct: 55.6->79; wasm_median_js_pkg: 0.4539->0.3525; wasm_median_js_alu: 0.05362->0.06199; wasm_median_freestanding: 0.2183->0.2222
- 2026-09-23T04:51:54 | RED | tests_ok=13/15 | delta: status: GREEN->RED; tests_ok: 15->13; latency_savings_pct: 79->42.8; wasm_median_js_pkg: 0.3525->0.6525; wasm_median_js_alu: 0.06199->0.07085; wasm_median_freestanding: 0.2222->0.2841
- 2026-09-23T04:59:29 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 13->15; latency_savings_pct: 42.8->81.8; wasm_median_js_pkg: 0.6525->0.4098; wasm_median_js_alu: 0.07085->0.05885; wasm_median_freestanding: 0.2841->0.3274
- 2026-09-23T05:49:21 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 81.8->73.1; wasm_median_js_pkg: 0.4098->0.376; wasm_median_js_alu: 0.05885->0.07394; wasm_median_freestanding: 0.3274->0.2097
- 2026-09-23T06:00:10 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 73.1->70.2; wasm_median_js_pkg: 0.376->0.4293; wasm_median_js_alu: 0.07394->0.04938; wasm_median_freestanding: 0.2097->0.2136
- 2026-09-23T06:13:22 | RED | tests_ok=12/15 | delta: status: GREEN->RED; tests_ok: 15->12; latency_savings_pct: 70.2->5; token_savings_pct: 55.2->8.9; wasm_median_js_pkg: 0.4293->0.31; wasm_median_js_alu: 0.04938->0.04834; wasm_median_freestanding: 0.2136->0.2176
- 2026-09-23T06:43:14 | RED | tests_ok=12/15 | delta: latency_savings_pct: 5->-12.6; wasm_median_js_pkg: 0.31->0.363; wasm_median_js_alu: 0.04834->0.0551; wasm_median_freestanding: 0.2176->0.2504
- 2026-09-23T06:48:20 | RED | tests_ok=12/15 | delta: latency_savings_pct: -12.6->-3.8; wasm_median_js_pkg: 0.363->0.377; wasm_median_js_alu: 0.0551->0.07295; wasm_median_freestanding: 0.2504->0.3224
- 2026-09-23T06:55:32 | RED | tests_ok=12/15 | delta: latency_savings_pct: -3.8->-92.7; wasm_median_js_pkg: 0.377->0.5706; wasm_median_js_alu: 0.07295->0.1048; wasm_median_freestanding: 0.3224->0.2394
- 2026-09-23T07:03:20 | RED | tests_ok=13/15 | delta: tests_ok: 12->13; latency_savings_pct: -92.7->24.5; token_savings_pct: 8.9->33; wasm_median_js_pkg: 0.5706->0.3423; wasm_median_js_alu: 0.1048->0.04464; wasm_median_freestanding: 0.2394->0.2313
- 2026-09-23T07:08:31 | RED | tests_ok=13/15 | delta: latency_savings_pct: 24.5->12.7; wasm_median_js_pkg: 0.3423->0.365; wasm_median_js_alu: 0.04464->0.08052; wasm_median_freestanding: 0.2313->0.3485
- 2026-09-23T07:12:40 | RED | tests_ok=13/15 | delta: latency_savings_pct: 12.7->8.6; wasm_median_js_pkg: 0.365->0.3385; wasm_median_js_alu: 0.08052->0.07681; wasm_median_freestanding: 0.3485->0.3574
- 2026-09-23T07:17:25 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 13->15; latency_savings_pct: 8.6->-2.1; wasm_median_js_pkg: 0.3385->0.3629; wasm_median_js_alu: 0.07681->0.07188; wasm_median_freestanding: 0.3574->0.3401
