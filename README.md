# frankenspear — Intuition Instant Layer

![CI](https://github.com/bahira/frankenspear/actions/workflows/ci/badge.svg)
![Release](https://github.com/bahira/frankenspear/badge/tag/v1.0.svg)

Neuro-symbolic prompt router: 16-dim features -> SLM (SpearEmb + TinyPolicy, numpy pur)
-> gate (confidence ou logistic) -> chemin `instant` (closed-form WASM) ou `slow` (LLM complet).
Noyau sans framework, 100% deterministe, checksums stables, 13 etapes vertes.

## Quickstart

```bash
pip install numpy
npm install            # spear-kernels@1.10.3 (lockfile inclus)
python run_all.py      # 13 etapes -> "13/13 etapes OK"
python make_report.py  # REPORT.md + REPORT.json (statut + changelog)
```

## Resultats

| gate (holdout n=48) | F1 | precision | recall | faux-instant |
|---|---|---|---|---|
| logistic_regression (defaut) | 0.844 | 0.826 | 0.864 | 0.174 |
| gate_retrained @0.65 | 0.606 | 0.455 | 0.909 | 0.546 |
| len baseline (<12 mots) | 0.657 | 0.489 | 1.000 | 0.511 |

E2E (n=109), `gated_lr`: ~45-50% latence et ~55% tokens vs `always_full`, false-instant 0.00.
E2E multi-conf (negative result): pas de gain sur le scalaire -> formule Φ(4|p-0.5|-1) conservee.

WASM vs JS ALU: scalar 0.08x (import-heavy) / 0.35-0.42x (freestanding); batch >1x des
N=4096 (jusqu'a 2.6x) — le cout de boundary est amorti, pas le nombre de specs.

## Architecture

```
prompt -> features_from_text (16d, LRU cache) -> SpearEmb (8+4xact=40d)
       -> TinyPolicy (40->32->1, tanh/sigmoid champions) -> p
       -> gate: conf = Φ(4|p-0.5|-1)  |  lr: P(trivial) (Platt-fit, 16 features)
       -> instant = closed-form WASM   |  slow = LLM complet
```

- 89 ids de kernels package, 51 champions + ports numpy (`champions_extra.py`),
  8 valides par `test_discover.py` (max_rel_err < 1e-4 vs JS de reference)
- `route()` / `route_batch()` (matmul unique), `attributes()` (concurrence/CHSH/γ/QFI/Kelly/RSI)
- `showcase.html`: site live sans framework, 42 modules WASM, toggle conf/lr,
  3 figures + checksums, chiffres sync des JSON de benches

## Structure

```
intuition.py            noyau (champions, SLM, LogisticGate, IntuitionInstant)
slow_path.py            chemin lent (LLM reference, 4 formats)
eval_harness.py         holdout + baselines + calibration ECE
e2e_bench.py            4 scenarios (always_full/fast, gated conf/lr)
wasm_bench.js           scalar: import-heavy vs freestanding vs JS ALU
wasm_batch_bench.js     batch: crossover N=4096
make_report.py          REPORT.md/JSON + changelog des snapshots
run_all.py              entree unique de verification (13 etapes)
export_csv.py           metrics.csv (import tableau)
test_*.py / test_showcase.js   suite de tests (scripts autonomes)
docs/plans/             plan d'implementation (7 taches TDD)
```

## Qualite

- Tests: `test_intuition.py` (6), `test_slow_path.py` (3), `test_reports.py` (golden
  checksums + tolerances), `test_discover.py`, `test_showcase.js` (parite WASM/JS/router)
- CI: GitHub Actions windows-latest, `python run_all.py`, badge en tete
- Determinisme: checksums identiques sur runs consecutifs; jitter e2e = median 5 passes
- License: MIT (texte canonique) — voir `LICENSE`

## Contribution

1. `python run_all.py` doit rester `13/13`  2. ajouter un test autonome `test_*.py` par
regle  3. chiffres du README sync via `python make_report.py`  4. une tache = un commit.

Milestones: M1 fondations/qualite, M2 perf/benches, M3 docs/outreach — voir `issues`.
