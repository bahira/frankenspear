# frankenspear — Intuition Instant Layer

Routeur neuro-symbolique : noyau d'attribution instant/slow d'un prompt,
champions closed-form + SLM (numpy pur) + gate logistique, kernels WASM reels.

## Lancer

```
pip install numpy
npm install
python run_all.py      # 13 etapes, attendu "13/13 etapes OK"
```

## Metriques cles (holdout n=48, e2e n=109)

| gate | F1 | faux-instant |
|---|---|---|
| logistic_regression (defaut) | 0.844 | 0.174 |
| gate_retrained @0.65 | 0.606 | 0.546 |
| len baseline (<12 mots) | 0.657 | 0.511 |

E2E `gated_lr` : ~45-50% latence / ~55% tokens vs always_full, false-instant 0.00.
WASM : scalar ~0.3x (host boundary), batch >1x des N=4096.

## Fichiers

- `intuition.py` — noyau : champions, features 16d, SpearEmb+TinyPolicy, LogisticGate, `IntuitionInstant.route/route_batch`
- `eval_harness.py` / `e2e_bench.py` — holdout + scenarios e2e (JSON reports)
- `wasm_bench.js` / `wasm_batch_bench.js` — scalar vs batch vs JS ALU
- `showcase.html` — site live (WASM reel, pas de mock)
- `make_report.py` → `REPORT.md`/`REPORT.json` / `export_csv.py` → `metrics.csv`
- `test_*.py` / `test_showcase.js` — suite verte
- `docs/plans/` — plan d'implementation

## CI

GitHub Actions : `windows-latest`, `python run_all.py` (voir badge en haut).
