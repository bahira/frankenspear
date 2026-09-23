# REPORT

- genere: 2026-09-23T04:59:29
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
| always_full | 5430 | 1.13e+04 | 6060 | 1 | 179397 |
| always_fast | 38.6 | 86.67 | 38.43 | 0 | 0 |
| gated | 985.6 | 9557 | 2902 | 0.4587 | 80333 |
| gated_lr | 3748 | 9928 | 3842 | 0.6606 | 119964 |

- savings: latence 81.8% / tokens 55.2% vs always_full

## WASM (median speedups)

| ratio | median |
|---|---|
| importheavy_vs_js_pkg | 0.4098 |
| importheavy_vs_js_alu | 0.05885 |
| freestanding_vs_js_alu | 0.3274 |

- import-heavy package WASM is 2.44x SLOWER than its own JS (median 0.41x) — env host-import overhead dominates; 0-import freestanding WASM is 0.33x vs JS ALU.

## WASM batch (median speedup js/wasm per N)

| N | speedup |
|---|---|
| 256 | 0.7059 |
| 4096 | 2.808 |
| 65536 | 1.167 |
| 1000000 | 1.018 |

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
- `gen_showcase.py` exit=0 first='bench block regenere (1807 octets)' last='bench block regenere (1807 octets)'
- `changelog.py` exit=0 first='CHANGELOG.md (0 lignes)' last='CHANGELOG.md (0 lignes)'
- `demo_agent.py` exit=0 first='instant p=0.648 conf=0.307 cx=0.425 362.6us  salut qui es-tu aide' last='stats instant=3 slow=0'
- `wasm_bench.js` exit=0 first='wasm_bench  n=100000 samples=100 warmup=5 passes=2  node=v24.13.0' last='report â†’ wasm_bench_report.json | checksum 1269556570.5185847'
- `wasm_batch_bench.js` exit=0 first='wasm_batch_bench  passes=2  node=v24.13.0' last='report â†’ wasm_batch_report.json | checksum 8185846.975385929'

## Next actions

1. Gate par defaut = logistic_regression (F1=0.8444) > retrained (F1=0.6061); faux-instant 0.1739 vs 0.5455
2. WASM batch: preferrer batch (N>=4096) — scalar ~0.3x, batch ~1-2x vs JS

## Changelog

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
- 2026-09-23T03:36:37 | GREEN | tests_ok=15/15 | delta: latency_savings_pct: 81.8->59.9; wasm_median_js_pkg: 0.392->0.3429; wasm_median_js_alu: 0.07365->0.04958; wasm_median_freestanding: 0.3248->0.1785
- 2026-09-23T03:43:10 | RED | tests_ok=14/15 | delta: status: GREEN->RED; tests_ok: 15->14; latency_savings_pct: 59.9->77.6; wasm_median_js_pkg: 0.3429->0.3781; wasm_median_js_alu: 0.04958->0.0614; wasm_median_freestanding: 0.1785->0.3578
- 2026-09-23T03:57:23 | RED | tests_ok=14/15 | delta: latency_savings_pct: 77.6->55.6; wasm_median_js_pkg: 0.3781->0.4539; wasm_median_js_alu: 0.0614->0.05362; wasm_median_freestanding: 0.3578->0.2183
- 2026-09-23T04:41:05 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 14->15; latency_savings_pct: 55.6->79; wasm_median_js_pkg: 0.4539->0.3525; wasm_median_js_alu: 0.05362->0.06199; wasm_median_freestanding: 0.2183->0.2222
- 2026-09-23T04:51:54 | RED | tests_ok=13/15 | delta: status: GREEN->RED; tests_ok: 15->13; latency_savings_pct: 79->42.8; wasm_median_js_pkg: 0.3525->0.6525; wasm_median_js_alu: 0.06199->0.07085; wasm_median_freestanding: 0.2222->0.2841
- 2026-09-23T04:59:29 | GREEN | tests_ok=15/15 | delta: status: RED->GREEN; tests_ok: 13->15; latency_savings_pct: 42.8->81.8; wasm_median_js_pkg: 0.6525->0.4098; wasm_median_js_alu: 0.07085->0.05885; wasm_median_freestanding: 0.2841->0.3274
