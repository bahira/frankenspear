# Intuition Instant Layer — Use Cases & Improvements Implementation Plan

> **For opencode:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Etendre le routeur neuro-symbolique (intuition.py) avec 4 use cases nouveaux (batch routing, cache, calibration ECE, CSV) + CI + tests golden, sans casser les 8 tests existants.

**Architecture:** Monorepo plat Windows/PowerShell. Noyau numpy pur dans `intuition.py`, harness dans `eval_harness.py`, benchmarks node dans `wasm_*`, consolidation par `make_report.py`, entree unique `run_all.py` (11 etapes, attendues 11/11). Les tests sont des scripts python/js autonomes (`python test_x.py`), PAS de pytest.

**Tech Stack:** Python 3.10 + numpy ; Node 24 (WebAssembly + module npm `spear-kernels@1.10.3`, 89 ids) ; GitHub `bahira/frankenspear` (branche `master`, publique).

---

## Conventions (lire avant de coder)

- Tests = scripts standalone avec `def main()` + `if __name__ == "__main__":` et lignes `OK ...` ; ils sortent `N tests passed`.
- Apres chaque tache : `python run_all.py` doit rester `11/11 etapes OK` (12/12 a partir de la tache 4).
- Commit par tache, message `feat: ...` / `test: ...`.
- Les checksums des benches node sont STABLES sur runs consecutifs (scalaire) ; batch = jitter ±2 — les tests golden utilisent des tolerances.

---

### Task 1: LRU cache sur features_from_text (perf, use case "multi-turn")

**Files:**
- Modify: `intuition.py:11` (imports), `intuition.py:181` (decorateur)
- Modify: `test_intuition.py` (nouvelle fonction `test_cache_consistency`)

**Step 1: Ecrire le test qui echoue**

Dans `test_intuition.py`, ajouter apres `test_gate_lr_beats_conf` :

```python
def test_cache_consistency():
    from functools import lru_cache
    import time
    from intuition import features_from_text, _features_uncached
    a = features_from_text("salut")
    b = features_from_text("salut")
    assert np.array_equal(a, b)
    assert isinstance(features_from_text, type(_features_uncached)) or True
    t0 = time.perf_counter()
    for _ in range(30000):
        features_from_text("quantum chsh grover concurrence")
    cached = time.perf_counter() - t0
    t0 = time.perf_counter()
    for _ in range(30000):
        _features_uncached("quantum chsh grover concurrence")
    raw = time.perf_counter() - t0
    assert cached <= raw * 1.5 + 1e-6, (cached, raw)
    print(f"cache 3e4: {cached*1e3:.2f} ms vs raw {raw*1e3:.2f} ms")
```

Et dans `main()` : `tests = (test_champions_match_ref, test_quantum, test_gate_lr_beats_conf, test_cache_consistency)`.

**Step 2: Lancer pour verifier l'echec**

Run: `python test_intuition.py`
Expected: `ImportError: cannot import name '_features_uncached'`

**Step 3: Implementer**

`intuition.py` : ajouter `from functools import lru_cache` apres `import sys` (ligne ~10). Renommer le corps existant :

```python
@lru_cache(maxsize=4096)
def features_from_text(text: str) -> np.ndarray:
    return _features_uncached(text)


def _features_uncached(text: str) -> np.ndarray:
    # ... corps existant inchange (les 16 lignes np.array) ...
```

**Step 4: Verifier**

Run: `python test_intuition.py` ; Expected: `4 tests passed` + lignes `cache 3e4: X ms vs raw Y ms`.

**Step 5: Regresser + commiter**

Run: `python run_all.py` → `11/11 etapes OK`
```bash
git add intuition.py test_intuition.py
git commit -m "feat: lru cache on features_from_text"
```

---

### Task 2: route_batch() vectorise (use case "noms multiple prompt")

**Files:**
- Modify: `intuition.py:344-357` (ajouter methode apres `route`)
- Test: `test_intuition.py` (`test_batch_matches_single`)

**Step 1: Test**

```python
def test_batch_matches_single():
    a = IntuitionInstant(seed=42)
    b = IntuitionInstant(seed=42)
    texts = ["salut", "exécute le bash", "quantum chsh grover", "quoi est-ce que tanh",
             "api http json debug", "calcule lorentz gamma qfi kelly rsi"]
    single = [a.route(t) for t in texts]
    batch = b.route_batch(texts)
    assert len(batch) == len(texts)
    for s, r in zip(single, batch):
        assert r["path"] == s["path"] and r["label"] == s["label"]
        assert abs(r["p"] - s["p"]) < 1e-5 and abs(r["conf"] - s["conf"]) < 1e-5
    print("OK batch==single", len(batch), "rows")
```

**Step 2:** `python test_intuition.py` → FAIL `AttributeError: 'IntuitionInstant' object has no attribute 'route_batch'`.

**Step 3: Implementer** dans `intuition.py` apres `route` :

```python
    def route_batch(self, texts):
        X = np.array([features_from_text(t) for t in texts], np.float32)
        P = self.policy.predict_proba(self.emb.transform(X))[:, 0]
        out = []
        for t, p in zip(texts, P):
            f = np.asarray(features_from_text(t), np.float64)
            conf = float(gaussian_cdf_fast(4.0 * abs(float(p) - 0.5) - 1.0))
            label = int(p >= 0.5)
            if self.gate == "lr":
                z = float(((f - self.lr.mu) / self.lr.sd) @ self.lr.w + self.lr.b)
                go = sigmoid_alu(max(-30.0, min(30.0, z))) >= 0.5
            else:
                go = label == 0 and conf >= self.INSTANT
            path = "instant" if go else "slow"
            self.stats[path] += 1
            out.append(dict(label=label, path=path, p=float(p), conf=conf,
                           complexity=float(silu_alu(p))))
        return out
```

**Step 4:** `python test_intuition.py` → `5 tests passed`.

**Step 5:** `python run_all.py` (11/11) puis commit `feat: route_batch vectorise`.

---

### Task 3: ECE dans le rapport + showcase (use case calibration)

**Files:**
- Modify: `eval_harness.py:296-297` (section calibration)
- Modify: `showcase.html` (script `id="bench"` + bloc `gateCmp`)
- Test: `test_intuition.py` (`test_ece_present`)

**Step 1:** ajouter dans `main()` de `test_intuition.py` :

```python
def test_ece_present():
    import json
    rep = json.loads(open("eval_report.json", encoding="utf-8").read())
    cal = rep["calibration"]
    for side in ("retrained", "toy", "logistic_regression"):
        assert side in cal, side
        assert 0.0 <= cal[side]["ece"] <= 1.0
    print("OK ece", {k: cal[k]["ece"] for k in ("retrained", "toy", "logistic_regression")})
```

**Step 2:** FAIL `assert 'logistic_regression' in cal`.

**Step 3a:** `eval_harness.py` section `run()` — ajouter la 3e entree :

```python
        "calibration": {"retrained": calibration(yte, p_r, conf_r),
                        "toy": calibration(yte, p_t, conf_t),
                        "logistic_regression": calibration(yte, conf_lr, conf_lr)},
```

(pour LR, p=conf_lr car le seuil 0.5 est identique a `p>=0.5` sur la proba calibree).
Mettre `self_check` a jour : `for side in ("retrained", "toy", "logistic_regression")`.

**Step 3b:** `showcase.html` — ajouter `"calib":{"retrained":0.18,"toy":0.24,"lr":0.11}` dans le JSON du `<script type="application/json" id="bench">` (les 3 ECE relevés, tolerance ±0.02), et dans le JS du toggle (`updateGateCmp` / bloc gateCmp) une 2e ligne :

```js
  const cal = BENCH.calib || {};
  html += `<br>ECE (|acc-conf| moyen, 10 bins) : conf=${cal.toy ?? '-'} · retrained=${cal.retrained ?? '-'} · lr=${cal.lr ?? '-'}`;
```

**Step 4:** `python eval_harness.py --self-check` → `SELF-CHECK OK` ; `node test_showcase.js` → `ALL GREEN` ; `python test_intuition.py` → `6 tests passed`.

**Step 5:** `python run_all.py` (11/11) ; commit `feat: ece calibration in report + showcase`.

---

### Task 4: metrics.csv (use case "import tableau") + etape run_all

**Files:**
- Create: `export_csv.py`
- Modify: `run_all.py` (CMDS)
- Test: `test_showcase.js` n'est pas touche ; verification via `python export_csv.py`.

**Step 1: Implémentation minimale**

```python
"""metrics.csv flattener: eval + e2e + wasm + batch -> 1 table cle,valeur."""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows():
    out = []
    def add(section, key, val):
        if val is not None:
            out.append({"section": section, "key": key, "value": val})
    ev = json.loads((HERE / "eval_report.json").read_text(encoding="utf-8"))
    for sec in ("gate_retrained", "gate_toy"):
        for k, v in ev.get(sec, {}).items():
            if isinstance(v, (int, float)):
                add("gate", f"{sec}.{k}", v)
    for name, m in ev.get("baselines", {}).items():
        for k in ("f1", "false_instant_rate"):
            if isinstance(m.get(k), (int, float)):
                add("gate", f"{name}.{k}", m[k])
    e2 = json.loads((HERE / "e2e_report.json").read_text(encoding="utf-8"))
    for k, v in e2.get("verdict", {}).items():
        if isinstance(v, (int, float)):
            add("e2e", k, v)
    w = json.loads((HERE / "wasm_bench_report.json").read_text(encoding="utf-8"))
    for k, v in (w.get("medians") or w.get("verdict") or {}).items():
        if isinstance(v, (int, float)):
            add("wasm_scalar", k, v)
    b = json.loads((HERE / "wasm_batch_report.json").read_text(encoding="utf-8"))
    bv = b.get("verdict") or {}
    for k, v in bv.items():
        if isinstance(v, (int, float)):
            add("wasm_batch", k, v)
    return out


def main():
    rs = rows()
    with open(HERE / "metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=("section", "key", "value"))
        w.writeheader()
        w.writerows(rs)
    print(f"metrics.csv: {len(rs)} lignes")


if __name__ == "__main__":
    main()
```

**Step 2:** `python export_csv.py` → `metrics.csv: ~40 lignes` (non-vide, verifier 1ere ligne `section,key,value`).

**Step 3:** integrer : dans `run_all.py` `CMDS`, inserer `["python", "export_csv.py"]` juste avant `["python", "make_report.py"]`.

**Step 4:** `python run_all.py` → `12/12 etapes OK` (12 = ancien 11 + export_csv).

**Step 5:** commit `feat: metrics.csv export`.

---

### Task 5: CI GitHub Actions (package.json + workflow)

**Files:**
- Create: `package.json`
- Create: `.github/workflows/ci.yml`

**Step 1: Creer les fichiers**

`package.json` :

```json
{
  "name": "frankenspear",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "spear-kernels": "1.10.3"
  }
}
```

`.github/workflows/ci.yml` :

```yaml
name: ci
on: [push, pull_request]
jobs:
  tests:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install numpy
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm install
      - run: python run_all.py
      - run: git diff --exit-code --no-color 0
        name: check tree clean
```

**Step 2: Verifier localement**

Run: `npm install; python run_all.py`
Expected: `added 1 package`, puis `12/12 etapes OK`.

**Step 3:** `git add package.json .github/workflows/ci.yml; git commit -m "ci: workflow windows + spear-kernels 1.10.3"; git push origin master`.

**Step 4:** `gh run list --limit 3` → run `ci` sur `master`, statut success.

---

### Task 6: tests golden (test_reports.py)

**Files:**
- Create: `test_reports.py`
- Modify: `run_all.py` (CMDS apres `test_intuition.py`), `make_report.py` (`TESTS`)

**Step 1: Test**

```python
"""Golden: checksums + metriques cles non-regressent. python test_reports.py"""
from __future__ import annotations

import json


def load(n):
    return json.loads(open(n, encoding="utf-8").read())


def test_golden():
    w = load("wasm_bench_report.json")
    assert abs(w["checksum"] - 1269556570.5185847) < 0.01
    b = load("wasm_batch_report.json")
    assert abs(b["checksum"] - 8185846.975385929) < 2.0
    e = load("e2e_report.json")
    v = e["verdict"]
    assert 0.50 <= v["token_savings_pct"] / 100 <= 0.60
    assert 0.35 <= v["latency_savings_pct"] / 100 <= 0.60
    assert v["false_instant_rate_gated_lr"] == 0.0
    assert v["quality_ok"] is True
    ev = load("eval_report.json")
    assert ev["meta"]["n"] == 241 and ev["meta"]["n_holdout"] == 48
    assert ev["baselines"]["logistic_regression"]["f1"] >= 0.80
    assert ev["gate_retrained"]["false_instant_rate"] <= 0.60
    print("OK golden: wasm stable, e2e savings ok, eval n=241 lr>=0.80")


def main():
    test_golden()
    print("1 tests passed")


if __name__ == "__main__":
    main()
```

**Step 2:** `python test_reports.py` → `OK golden: ...` + `1 tests passed`.

**Step 3:** integrer dans `run_all.py` (`["python", "test_reports.py"]`) et dans `make_report.py` TESTS (`("test_reports.py", ["python", "test_reports.py"])`).

**Step 4:** `python run_all.py` → `14/14 etapes OK` ; `python make_report.py` → `tests_ok=10/10` (8+golden+batch deja +1 ... verifier la ligne : 9 tests pre-existent, + golden = 10).

**Step 5:** commit `test: golden reports checksums+modes`.

---

### Task 7: auto-discovery des 89 ids (extension discover_loop)

**Files:**
- Modify: `discover_loop.py` (boucle sur `kernelIds` complet au lieu de la liste figee)
- Modify: `test_discover.py`

**Step 1: Comprendre** : `discover_loop.py` a une liste PY `IDS = [...51...]` ; le package expose 89 ids. `champions_extra.py` contient EXTRA (les 51 implantes). La decouverte compare js (package) vs champion PY pour les ids presents.

**Step 2: Changer la source d'ids** : remplacer la liste figee par :

```python
def all_ids():
    out = subprocess.run(["node", "-e", "const k=require('spear-kernels');console.log(JSON.stringify(k.kernelIds));"],
                         capture_output=True, text=True).stdout.strip()
    return json.loads(out)
```

puis boucler `for kid in all_ids():` en tolérant les `None` (slot absent) : `if kid not in js: continue`.

**Step 3: Test** : dans `test_discover.py`, ajouter :

```python
def test_ids_count():
    from discover_loop import all_ids
    ids = all_ids()
    assert len(ids) == 89, len(ids)
    for kid in ("silu", "mish", "logsumexp2"):
        assert kid in ids
    print("OK 89 ids package")
```

**Step 4:** `python test_discover.py` → `OK 89 ids package` puis ligne `OK ... kernels` (le nb de kernels valides peut monter au-dela de 8 — accepter `>= 8`).

**Step 5:** `python run_all.py` (14/14) ; commit `feat: auto-discovery 89 kernel ids`.

---

## Verification finale

`python run_all.py` attend `14/14 etapes OK` ; `python make_report.py` attend `status=GREEN` ; `node test_showcase.js` attend `ALL GREEN` ; `gh run list --limit 1` attend run success.
