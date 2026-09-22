# REPORT

- genere: 2026-09-23T00:59:02
- statut GLOBAL: RED
- sources JSON lus: 3/4

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
| always_full | - | - | - | - | - |
| always_fast | - | - | - | - | - |
| gated | - | - | - | - | - |
| gated_lr | - | - | - | - | - |

- savings: latence -% / tokens -% vs always_full

## WASM (median speedups)

| ratio | median |
|---|---|
| importheavy_vs_js_pkg | 0.4836 |
| importheavy_vs_js_alu | 0.07279 |
| freestanding_vs_js_alu | 0.2466 |

- import-heavy package WASM is 2.07x SLOWER than its own JS (median 0.48x) — env host-import overhead dominates; 0-import freestanding WASM is 0.25x vs JS ALU.

## WASM batch (median speedup js/wasm per N)

| N | speedup |
|---|---|
| 256 | 0.4103 |
| 4096 | 1.465 |
| 65536 | 1.222 |
| 1000000 | 1.109 |

- crossover N=4096 | batch WASM beats JS (>1.05x median) from N=4096 — boundary cost amortized.

## Multi-conf / verdict negatif

- quality_ok: None
- n/a

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
| test_slow_path.py | 1 | FAIL |
| test_intuition.py | 0 | OK |
| test_reports.py | 0 | OK |
| test_properties.py | 0 | OK |
| test_discover.py | - | FAIL |
| test_showcase.js | 0 | OK |
| cov.py | 1 | FAIL |
| gen_showcase.py | 0 | OK |
| changelog.py | 0 | OK |
| demo_agent.py | 0 | OK |
| wasm_bench.js | - | FAIL |
| wasm_batch_bench.js | 0 | OK |

### Extraits (first/last line)

- `typecheck.py` exit=0 first='Success: no issues found in 8 source files' last='Success: no issues found in 8 source files'
- `eval_harness.py --self-check` exit=0 first='model                      prec    rec     F1  falseInst inst_rate' last='SELF-CHECK OK'
- `multi_conf.py` exit=0 first='self-check OK  (top-30% overlap scalar/current=1.00, risk@30 scalar=0.0% multi=0.0%)' last='re-run: python multi_conf.py'
- `test_slow_path.py` exit=1 first='OK test_paths_exist' last='AssertionError'
- `test_intuition.py` exit=0 first='OK test_champions_match_ref' last='9 tests passed'
- `test_reports.py` exit=0 first='OK golden: wasm stable, e2e savings ok, eval n=241 lr>=0.80' last='2 tests passed'
- `test_properties.py` exit=0 first='test_fuzz OK (14 prompts)' last='ALL GREEN'
- `test_discover.py` exit=None first='TimeoutExpired' last="Command '['python', 'test_discover.py']' timed out after 60 seconds"
- `test_showcase.js` exit=0 first='json ok 21 kernels; W1 48x32' last='ALL GREEN'
- `cov.py` exit=1 first='OK test_champions_match_ref' last='AssertionError'
- `gen_showcase.py` exit=0 first='bench block regenere (1843 octets)' last='bench block regenere (1843 octets)'
- `changelog.py` exit=0 first='CHANGELOG.md (0 lignes)' last='CHANGELOG.md (0 lignes)'
- `demo_agent.py` exit=0 first='instant p=0.648 conf=0.307 cx=0.425 568.6us  salut qui es-tu aide' last='stats instant=3 slow=0'
- `wasm_bench.js` exit=None first='TimeoutExpired' last="Command '['node', 'wasm_bench.js']' timed out after 60 seconds"
- `wasm_batch_bench.js` exit=0 first='wasm_batch_bench  passes=2  node=v24.13.0' last='report â†’ wasm_batch_report.json | checksum 8185846.975385929'

## Next actions

1. Gate par defaut = logistic_regression (F1=0.8444) > retrained (F1=0.6061); faux-instant 0.1739 vs 0.5455
2. WASM batch: preferrer batch (N>=4096) — scalar ~0.3x, batch ~1-2x vs JS

## Changelog

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
- 2026-09-22T22:48:25 | RED | tests_ok=12/13 | delta: status: GREEN->RED; tests_ok: 11->12; latency_savings_pct: 82.8->48.4; wasm_median_js_pkg: 0.335->0.6397; wasm_median_js_alu: 0.06468->0.07187; wasm_median_freestanding: 0.3686->0.2951
- 2026-09-22T22:56:59 | GREEN | tests_ok=13/13 | delta: status: RED->GREEN; tests_ok: 12->13; latency_savings_pct: 48.4->85.7; wasm_median_js_pkg: 0.6397->0.4365; wasm_median_js_alu: 0.07187->0.08964; wasm_median_freestanding: 0.2951->0.3991
- 2026-09-22T23:00:38 | GREEN | tests_ok=13/13 | delta: latency_savings_pct: 85.7->87.9; wasm_median_js_pkg: 0.4365->0.3989; wasm_median_js_alu: 0.08964->0.06764; wasm_median_freestanding: 0.3991->0.3401
- 2026-09-23T00:23:07 | RED | tests_ok=10/13 | delta: status: GREEN->RED; tests_ok: 13->10; latency_savings_pct: 87.9->82.8; wasm_median_js_pkg: 0.3989->0.5226; wasm_median_js_alu: 0.06764->0.1025; wasm_median_freestanding: 0.3401->0.3366
- 2026-09-23T00:29:14 | RED | tests_ok=13/15 | delta: tests_ok: 10->13; latency_savings_pct: 82.8->75.1; wasm_median_js_pkg: 0.5226->0.3838; wasm_median_js_alu: 0.1025->0.07015; wasm_median_freestanding: 0.3366->0.3539; wasm_batch_crossover_n: 4096->65536
- 2026-09-23T00:52:12 | RED | tests_ok=13/15 | delta: latency_savings_pct: 75.1->84.3; wasm_median_js_pkg: 0.3838->0.3724; wasm_median_js_alu: 0.07015->0.08101; wasm_median_freestanding: 0.3539->0.2757; wasm_batch_crossover_n: 65536->4096
- 2026-09-23T00:52:39 | RED | tests_ok=14/15 | delta: tests_ok: 13->14
- 2026-09-23T00:54:59 | RED | tests_ok=14/15 | delta: latency_savings_pct: 84.3->73.1; wasm_median_js_pkg: 0.3724->0.359; wasm_median_js_alu: 0.08101->0.06152; wasm_median_freestanding: 0.2757->0.2595
- 2026-09-23T00:59:02 | RED | tests_ok=11/15 | delta: tests_ok: 14->11; latency_savings_pct: 73.1->-; token_savings_pct: 55.2->-; wasm_median_js_pkg: 0.359->0.4836; wasm_median_js_alu: 0.06152->0.07279; wasm_median_freestanding: 0.2595->0.2466
