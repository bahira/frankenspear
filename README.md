# FrankenSpear — Intuition Instant Layer

**Deterministic neuro-symbolic routing for hybrid AI inference.**

![Python](https://img.shields.io/badge/Python-NumPy-3776ab?style=flat-square) ![WASM](https://img.shields.io/badge/Runtime-WebAssembly-654ff0?style=flat-square) ![MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)

![CI](https://github.com/bahira/frankenspear/actions/workflows/ci/badge.svg)
![Release](https://github.com/bahira/frankenspear/badge/tag/v1.0.svg)

Neuro-symbolic prompt router: 16-dimensional features → SLM (SpearEmb + TinyPolicy, pure NumPy) → confidence or logistic gate → `instant` (closed-form WASM) or `slow` (full LLM) path.
Framework-free deterministic core, stable checksums, and a documented 13-stage verification pipeline.

## Quickstart

```bash
pip install numpy
npm install            # spear-kernels@1.10.3 (lockfile included)
python run_all.py      # 13 stages -> "13/13 stages OK"
python make_report.py  # REPORT.md + REPORT.json (status + changelog)
```

## Results

<!-- BEGIN gate -->
('0.8444', '0.8261', '0.8636', '0.1739')
<!-- END gate -->

<!-- BEGIN e2e -->
('51.6', '33.1', '-')
<!-- END e2e -->

<!-- BEGIN wasm -->
freestanding_vs_js_alu=0.1485; importheavy_vs_js_alu=0.0511; importheavy_vs_js_pkg=0.3036
<!-- END wasm -->

## Architecture

```
prompt -> features_from_text (16d, LRU cache) -> SpearEmb (8+4xact=40d)
       -> TinyPolicy (40->32->1, tanh/sigmoid champions) -> p
       -> gate: conf = Φ(4|p-0.5|-1)  |  lr: P(trivial) (Platt-fit, 16 features)
       -> instant = closed-form WASM   |  slow = full LLM
```

- 89 package kernel IDs, 51 champions + NumPy ports (`champions_extra.py`),
  8 validated by `test_discover.py` (max_rel_err < 1e-4 vs reference JS)
- `route()` / `route_batch()` (matmul unique), `attributes()` (concurrence/CHSH/γ/QFI/Kelly/RSI)
- `showcase.html`: framework-free live showcase, 42 modules WASM, toggle conf/lr,
  3 figures + checksums, metrics synchronized from benchmark JSON

## Structure

```
intuition.py            core (champions, SLM, LogisticGate, IntuitionInstant)
slow_path.py            slow path (reference LLM, 4 formats)
eval_harness.py         holdout + baselines + calibration ECE
e2e_bench.py            4 scenarios (always_full/fast, gated conf/lr)
wasm_bench.js           scalar: import-heavy vs freestanding vs JS ALU
wasm_batch_bench.js     batch: crossover N=4096
make_report.py          REPORT.md/JSON + snapshot changelog
run_all.py              single verification entry point (13 stages)
export_csv.py           metrics.csv (spreadsheet import)
test_*.py / test_showcase.js   test suite (standalone scripts)
docs/plans/             implementation plan (7 TDD tasks)
```

## Quality

- Tests: `test_intuition.py` (6), `test_slow_path.py` (3), `test_reports.py` (golden
  checksums + tolerances), `test_discover.py`, `test_showcase.js` (WASM/JS/router parity)
- CI: GitHub Actions windows-latest, `python run_all.py`, badge above
- Determinism: identical checksums across consecutive runs; end-to-end jitter measured as the median of five passes
- License: MIT (canonical text) — see `LICENSE`

## Contributing

1. Keep `python run_all.py` at `13/13`.
2. Add a standalone `test_*.py` for each rule.
3. Synchronize README metrics via `python make_report.py`.
4. Use one commit per task.

Milestones: M1 foundations/quality, M2 perf/benches, M3 docs/outreach — see `issues`.
