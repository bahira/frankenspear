# REPORT

- genere: 2026-09-23T02:56:14
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
| always_full | 4516 | 7373 | 4853 | 1 | 179397 |
| always_fast | 45.4 | 117.9 | 46.14 | 0 | 0 |
| gated | 823.6 | 8268 | 2863 | 0.4587 | 80333 |
| gated_lr | 4676 | 7413 | 3724 | 0.6606 | 119964 |

- savings: latence 81.8% / tokens 55.2% vs always_full

## WASM (median speedups)

| ratio | median |
|---|---|
| importheavy_vs_js_pkg | 0.392 |
| importheavy_vs_js_alu | 0.07365 |
| freestanding_vs_js_alu | 0.3248 |

- import-heavy package WASM is 2.55x SLOWER than its own JS (median 0.39x) — env host-import overhead dominates; 0-import freestanding WASM is 0.32x vs JS ALU.

## WASM batch (median speedup js/wasm per N)

| N | speedup |
|---|---|
| 256 | 0.54 |
| 4096 | 1.245 |
| 65536 | 1.036 |
| 1000000 | 1.053 |

- crossover N=4096 | batch WASM beats JS (>1.05x median) from N=4096 — boundary cost amortized.

## Multi-conf / verdict negatif

- quality_ok: True
- gate: 81.8% latency / 55.2% tokens vs always_full; false-instant conf=1.0 lr=0.0 vs always_fast=1.0

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
- `test_reports.py` exit=0 first='OK golden: wasm stable, e2e savings ok, eval n=241 lr>=0.80' last='2 tests passed'
- `test_properties.py` exit=0 first='test_fuzz OK (14 prompts)' last='ALL GREEN'
- `test_discover.py` exit=0 first='OK 89 ids package' last='OK 61 kernels, all max_rel_err < 0.001'
- `test_showcase.js` exit=0 first='json ok 21 kernels; W1 48x32' last='ALL GREEN'
- `cov.py` exit=0 first='OK test_champions_match_ref' last='cov ok'
- `gen_showcase.py` exit=0 first='bench block regenere (1795 octets)' last='bench block regenere (1795 octets)'
- `changelog.py` exit=0 first='CHANGELOG.md (0 lignes)' last='CHANGELOG.md (0 lignes)'
- `demo_agent.py` exit=0 first='instant p=0.648 conf=0.307 cx=0.425 874.4us  salut qui es-tu aide' last='stats instant=3 slow=0'
- `wasm_bench.js` exit=0 first='wasm_bench  n=100000 samples=100 warmup=5 passes=2  node=v24.13.0' last='report â†’ wasm_bench_report.json | checksum 1269556570.5185847'
- `wasm_batch_bench.js` exit=0 first='wasm_batch_bench  passes=2  node=v24.13.0' last='report â†’ wasm_batch_report.json | checksum 8185846.975385929'

## Next actions

1. Gate par defaut = logistic_regression (F1=0.8444) > retrained (F1=0.6061); faux-instant 0.1739 vs 0.5455
2. WASM batch: preferrer batch (N>=4096) — scalar ~0.3x, batch ~1-2x vs JS

## Changelog

- 2026-09-22T23:00:38 | GREEN | tests_ok=13/13 | delta: latency_savings_pct: 85.7->87.9; wasm_median_js_pkg: 0.4365->0.3989; wasm_median_js_alu: 0.08964->0.06764; wasm_median_freestanding: 0.3991->0.3401
- 2026-09-23T00:23:07 | RED | tests_ok=10/13 | delta: status: GREEN->RED; tests_ok: 13->10; latency_savings_pct: 87.9->82.8; wasm_median_js_pkg: 0.3989->0.5226; wasm_median_js_alu: 0.06764->0.1025; wasm_median_freestanding: 0.3401->0.3366
- 2026-09-23T00:29:14 | RED | tests_ok=13/15 | delta: tests_ok: 10->13; latency_savings_pct: 82.8->75.1; wasm_median_js_pkg: 0.5226->0.3838; wasm_median_js_alu: 0.1025->0.07015; wasm_median_freestanding: 0.3366->0.3539; wasm_batch_crossover_n: 4096->65536
- 2026-09-23T00:52:12 | RED | tests_ok=13/15 | delta: latency_savings_pct: 75.1->84.3; wasm_median_js_pkg: 0.3838->0.3724; wasm_median_js_alu: 0.07015->0.08101; wasm_median_freestanding: 0.3539->0.2757; wasm_batch_crossover_n: 65536->4096
- 2026-09-23T00:52:39 | RED | tests_ok=14/15 | delta: tests_ok: 13->14
- 2026-09-23T00:54:59 | RED | tests_ok=14/15 | delta: latency_savings_pct: 84.3->73.1; wasm_median_js_pkg: 0.3724->0.359; wasm_median_js_alu: 0.08101->0.06152; wasm_median_freestanding: 0.2757->0.2595
- 2026-09-23T00:59:02 | RED | tests_ok=11/15 | delta: tests_ok: 14->11; latency_savings_pct: 73.1->-; token_savings_pct: 55.2->-; wasm_median_js_pkg: 0.359->0.4836; wasm_median_js_alu: 0.06152->0.07279; wasm_median_freestanding: 0.2595->0.2466
- 2026-09-23T01:00:53 | RED | tests_ok=12/15 | delta: tests_ok: 11->12; latency_savings_pct: -->86.6; token_savings_pct: -->55.2; wasm_median_js_pkg: 0.4836->0.3483; wasm_median_js_alu: 0.07279->0.08464; wasm_median_freestanding: 0.2466->0.287
- 2026-09-23T01:04:18 | RED | tests_ok=13/15 | delta: tests_ok: 12->13; latency_savings_pct: 86.6->92.7; wasm_median_js_pkg: 0.3483->0.4176; wasm_median_js_alu: 0.08464->0.07536; wasm_median_freestanding: 0.287->0.2468
- 2026-09-23T01:04:39 | RED | tests_ok=13/15 | delta: wasm_median_js_pkg: 0.4176->0.3832; wasm_median_js_alu: 0.07536->0.07715; wasm_median_freestanding: 0.2468->0.4241
- 2026-09-23T01:13:10 | RED | tests_ok=14/15 | delta: tests_ok: 13->14; latency_savings_pct: 92.7->86; wasm_median_js_pkg: 0.3832->0.4279; wasm_median_js_alu: 0.07715->0.04988; wasm_median_freestanding: 0.4241->0.2877; wasm_batch_crossover_n: 4096->65536
- 2026-09-23T01:15:01 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 14->15; latency_savings_pct: 86->91.8; wasm_median_js_pkg: 0.4279->0.4476; wasm_median_js_alu: 0.04988->0.1067; wasm_median_freestanding: 0.2877->0.3347; wasm_batch_crossover_n: 65536->4096
- 2026-09-23T01:17:29 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 91.8->55.6; wasm_median_js_pkg: 0.4476->0.3952; wasm_median_js_alu: 0.1067->0.06893; wasm_median_freestanding: 0.3347->0.2461
- 2026-09-23T01:23:07 | RED | tests_ok=12/15 | delta: status: GREEN->RED; tests_ok: 15->12; latency_savings_pct: 55.6->49.3; wasm_median_js_pkg: 0.3952->0.5257; wasm_median_js_alu: 0.06893->0.09304; wasm_median_freestanding: 0.2461->0.2818
- 2026-09-23T01:31:54 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 12->15; latency_savings_pct: 49.3->88.7; wasm_median_js_pkg: 0.5257->0.3581; wasm_median_js_alu: 0.09304->0.08839; wasm_median_freestanding: 0.2818->0.3029
- 2026-09-23T01:48:32 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 88.7->81.6; wasm_median_js_pkg: 0.3581->0.399; wasm_median_js_alu: 0.08839->0.08836; wasm_median_freestanding: 0.3029->0.3512
- 2026-09-23T02:15:01 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 81.6->79.8; wasm_median_js_pkg: 0.399->0.3416; wasm_median_js_alu: 0.08836->0.07861; wasm_median_freestanding: 0.3512->0.3537
- 2026-09-23T02:20:47 | RED | tests_ok=14/15 | delta: status: GREEN->RED; tests_ok: 15->14; latency_savings_pct: 79.8->74.3; wasm_median_js_pkg: 0.3416->0.4206; wasm_median_js_alu: 0.07861->0.08647; wasm_median_freestanding: 0.3537->0.355
- 2026-09-23T02:51:02 | RED | tests_ok=14/15 | delta: latency_savings_pct: 74.3->89.2; wasm_median_js_pkg: 0.4206->0.3884; wasm_median_js_alu: 0.08647->0.08028; wasm_median_freestanding: 0.355->0.3392
- 2026-09-23T02:56:14 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 14->15; latency_savings_pct: 89.2->81.8; wasm_median_js_pkg: 0.3884->0.392; wasm_median_js_alu: 0.08028->0.07365; wasm_median_freestanding: 0.3392->0.3248
