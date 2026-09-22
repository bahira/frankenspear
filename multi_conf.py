"""MULTI-SOURCE CONFIDENCE — heterogeneous signal fusion + hold-out ablation.

Formula (single, readable, calibrated on train by NLL of P(correct)):

    conf_multi_source(text) = sigmoid_alu( k*(w1*s1 + w2*s2 + w3*s3) - b )

    s1 = 2|p-0.5|                  TinyPolicy margin (as before)
    s2 = 1 - mean_ij  concurrence_pure(sqrt(1-pi), sqrt(pi), sqrt(1-pj), sqrt(pj)) / 2
         4 sub-model votes (one per 4-dim feature block) -> pairwise quantum disagreement
    s3 = 2|p_base-0.5|              distance-to-threshold of length-baseline LR
    (w1,w2,w3) simplex, k, b        grid-calibrated on the calibration slice of train

Ablation on hold-out (no eval_harness in repo -> homemade split, seed=0):
    scalar |p-0.5|  vs  current Phi(4|p-0.5|-1)  vs  conf_multi_source
"""
from __future__ import annotations

import numpy as np

from intuition import (
    TinyPolicy,
    SpearEmb,
    concurrence_pure,
    features_from_text,
    gaussian_cdf_fast,
    sigmoid_alu,
)

BLOCKS = ((0, 4), (4, 8), (8, 12), (12, 16))
BASE_COLS = (0, 5, 15)  # length-ish: log-len, spaces, newlines

OBJ = ("fibonacci", "gelu", "lorentz", "script", "fonction", "bash", "docker",
       "quantum", "chsh", "kernel", "api", "sql", "pipeline", "tests", "qfi", "kelly")
FILL = ("vite", "stp", "please", "aujourd'hui", "franchement", "maintenant", "bien")

T1 = (
    "exécute {o} s'il te plaît",
    "lance le bash {o} {f}",
    "écris une fonction {o}",
    "calcule {o} et ajoute le résultat",
    "run {o} tool {f}",
    "fais {o} {f}",
    "crée le script {o}",
    "execute {o} maintenant",
    "write the {o} code please",
    "ajoute le test {o} {f}",
)
T0 = (
    "quoi est-ce que {o} ?",
    "comment {o} fonctionne-t-il ?",
    "salut, merci pour tout {f}",
    "pourquoi {o} est important ?",
    "quelqu'un a un avis sur {o} ?",
    "merci d'avance {f}",
    "je pensais à {o} hier",
    "what is {o} exactly ?",
    "combien de temps pour {o} ?",
    "thanks for the {o} explanation",
)


def make_dataset(n=800, seed=0):
    """Synthetic labelled texts: 1 = needs tool/code action, 0 = question/chat.

    Ambiguity noise: '?' flips + keyword overlap (heavy), so no method hits ~100%
    and the scalar gate is not at ceiling on hold-out.
    """
    rng = np.random.RandomState(seed)
    texts, y = [], []
    for _ in range(n // 2):
        texts.append(rng.choice(T1).format(o=rng.choice(OBJ), f=rng.choice(FILL)))
        y.append(1)
        texts.append(rng.choice(T0).format(o=rng.choice(OBJ), f=rng.choice(FILL)))
        y.append(0)
    for i, t in enumerate(texts):
        if rng.rand() < 0.25:
            t = t.replace("?", "")
        elif rng.rand() < 0.25:
            t = t + " ?"
        if rng.rand() < 0.30:
            t = t + " " + rng.choice(("quoi", "comment", "exécute", "lance", "écris"))
        texts[i] = t
    idx = rng.permutation(len(texts))
    return [texts[i] for i in idx], np.asarray(y, np.float32)[idx]


def _pair_agreement(votes):
    """1 - mean pairwise concurrence disagreement of the sub-model votes."""
    v = np.atleast_2d(np.asarray(votes, float))
    v = np.clip(v, 0.0, 1.0)
    vi, vj = v[:, :, None], v[:, None, :]
    dis = 0.5 * concurrence_pure(np.sqrt(1.0 - vi), np.sqrt(vi),
                                 np.sqrt(1.0 - vj), np.sqrt(vj))
    iu = np.triu_indices(v.shape[1], 1)
    out = 1.0 - dis[:, iu[0], iu[1]].mean(1)
    return float(out[0]) if np.ndim(votes) == 1 else out


def _fit_lr(X, y, epochs=400, lr=0.5, l2=1e-3):
    n, d = X.shape
    w, b = np.zeros(d), 0.0
    for _ in range(epochs):
        p = sigmoid_alu(X @ w + b)
        g = p - y
        w -= lr * (X.T @ g / n + l2 * w)
        b -= lr * float(g.mean())
    return w, b


def _nll(c, y):
    c = np.clip(np.asarray(c, float), 1e-4, 1.0 - 1e-4)
    y = np.asarray(y, float)
    return float(-(y * np.log(c) + (1.0 - y) * np.log(1.0 - c)).mean())


KS = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0)
BS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)


def _calibrate(S, corr):
    """Grid over simplex w / k / b minimizing NLL of P(correct) on calib slice."""
    corr = np.asarray(corr, float)
    best = (np.inf, (1.0, 0.0, 0.0, 1.0, 1.0))
    for w1 in np.arange(0.0, 1.01, 0.1):
        for w2 in np.arange(0.0, 1.0 - w1 + 1e-9, 0.1):
            w = np.round(np.array([w1, w2, 1.0 - w1 - w2]), 2)
            s = S @ w
            for k in KS:
                for b in BS:
                    n = _nll(sigmoid_alu(k * s - b), corr)
                    if n < best[0]:
                        best = (n, (float(w[0]), float(w[1]), float(w[2]), float(k), float(b)))
    w1v, w2v, w3v, kv, bv = best[1]
    w3v = 0.0 if abs(w3v) < 1e-9 else w3v
    return best[0], (w1v, w2v, w3v, kv, bv)


class MultiConfModel:
    """Train-split bundle: main TinyPolicy + 4 block sub-models + length LR + fusion."""

    def __init__(self, seed=0, n=800):
        self.seed = seed
        texts, y = make_dataset(n, seed)
        ntr = int(0.6 * n)
        Xtr = np.array([features_from_text(t) for t in texts[:ntr]], np.float32)
        self.Xte = np.array([features_from_text(t) for t in texts[ntr:]], np.float32)
        self.yte = y[ntr:]
        rng = np.random.RandomState(seed)
        perm = rng.permutation(len(Xtr))
        nfit = int(0.7 * len(perm))
        Xf, yf = Xtr[perm[:nfit]], y[perm[:nfit]]
        self.Xcal, self.ycal = Xtr[perm[nfit:]], y[perm[nfit:]]
        Xc, yc = self.Xcal, self.ycal

        self.emb = SpearEmb.fit(Xf, seed=seed)
        self.policy = TinyPolicy.init(self.emb.transform(Xf).shape[1], h=32, seed=seed)
        self.policy.fit(self.emb.transform(Xf), yf, epochs=150)

        self.sub = []
        for k, (a, b) in enumerate(BLOCKS):
            mu = Xf[:, a:b].mean(0)
            sd = Xf[:, a:b].std(0) + 1e-6
            m = TinyPolicy.init(b - a, h=8, seed=seed + 1 + k)
            m.fit((Xf[:, a:b] - mu) / sd, yf, epochs=120)
            self.sub.append((mu, sd, m))

        Xb = Xf[:, list(BASE_COLS)]
        self.base_mu, self.base_sd = Xb.mean(0), Xb.std(0) + 1e-6
        self.base_w, self.base_b = _fit_lr((Xb - self.base_mu) / self.base_sd, yf)

        Sc, Pc = self.signals_batch(Xc)
        self.calib_nll = {}
        corr = ((Pc >= 0.5) == yc).astype(float)
        self.calib_nll["scalar"] = _nll(Sc[:, 0], corr)
        n, (w1, w2, w3, k, b) = _calibrate(Sc, corr)
        self.w = np.array([w1, w2, w3])
        self.k, self.b = k, b
        self.calib_nll["multi"] = n

    def _lr_p(self, Xb):
        return sigmoid_alu(((np.asarray(Xb, float) - self.base_mu) / self.base_sd)
                           @ self.base_w + self.base_b)

    def signals_batch(self, X):
        X = np.atleast_2d(np.asarray(X, np.float32))
        P = self.policy.predict_proba(self.emb.transform(X))[:, 0]
        s1 = 2.0 * np.abs(P - 0.5)
        votes = np.empty((len(X), len(BLOCKS)))
        for k, (a, b) in enumerate(BLOCKS):
            mu, sd, m = self.sub[k]
            votes[:, k] = m.predict_proba((X[:, a:b] - mu) / sd)[:, 0]
        s2 = _pair_agreement(votes)
        s3 = 2.0 * np.abs(self._lr_p(X[:, list(BASE_COLS)]) - 0.5)
        return np.stack([s1, s2, s3], axis=1), P

    def signals(self, text):
        return self.signals_batch(features_from_text(text))[0][0]

    def conf(self, s):
        return float(sigmoid_alu(self.k * (float(np.asarray(s, float) @ self.w)) - self.b))


_MODEL = None


def get_model() -> "MultiConfModel":
    global _MODEL
    if _MODEL is None:
        _MODEL = MultiConfModel(seed=0, n=800)
    return _MODEL


def conf_multi_source(text: str) -> float:
    """Fused multi-source confidence in [0,1]."""
    return float(get_model().conf(get_model().signals(text)))


def conf_scalar(text: str) -> float:
    """Ablation arm 1: raw |p-0.5| scalar threshold."""
    return float(get_model().signals(text)[0])


def conf_current(text: str) -> float:
    """Ablation arm 2: intuition.py current Phi(4|p-0.5|-1)."""
    return float(gaussian_cdf_fast(4.0 * abs(conf_scalar(text) / 2.0 - 0.5) - 1.0))


# ---------- ablation metrics ----------

def _topk(conf, k):
    return np.argsort(-np.asarray(conf), kind="mergesort")[:k]


def risk_at_coverage(conf, correct, cov):
    k = max(1, int(round(cov * len(correct))))
    idx = _topk(conf, k)
    return 1.0 - float(np.mean(correct[idx])), int(np.sum(1 - correct[idx])), k


def coverage_at_budget(conf, correct, budget):
    order = np.argsort(-np.asarray(conf), kind="mergesort")
    errs = np.cumsum(1.0 - np.asarray(correct, float)[order])
    ok = np.nonzero(errs <= budget + 1e-9)[0]
    return float((ok[-1] + 1) / len(correct)) if len(ok) else 0.0


def ece(conf, correct, bins=10):
    conf = np.asarray(conf, float)
    correct = np.asarray(correct, float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    out = 0.0
    for i in range(bins):
        m = (conf >= edges[i]) & ((conf < edges[i + 1]) if i < bins - 1 else (conf <= edges[i + 1]))
        if m.any():
            out += float(m.mean()) * abs(float(conf[m].mean()) - float(correct[m].mean()))
    return out


def ablation(cov=0.30, fixed_budget=0.05, verbose=True):
    m = get_model()
    S, P = m.signals_batch(m.Xte)
    correct = ((P >= 0.5) == m.yte)
    n = len(correct)
    methods = {
        "scalar |p-0.5|": S[:, 0],
        "current Phi(4|p-0.5|-1)": gaussian_cdf_fast(2.0 * S[:, 0] - 1.0),
        "conf_multi_source": sigmoid_alu(m.k * (S @ m.w) - m.b),
    }
    _, false_scalar, k30 = risk_at_coverage(methods["scalar |p-0.5|"], correct, cov)
    b0 = float(false_scalar)
    b5 = float(round(fixed_budget * n))
    rows = {}
    for name, conf in methods.items():
        risk, false_n, _ = risk_at_coverage(conf, correct, cov)
        rows[name] = dict(
            r10=risk_at_coverage(conf, correct, 0.10)[0],
            r30=risk, false_n=false_n,
            r50=risk_at_coverage(conf, correct, 0.50)[0],
            cov_b0=coverage_at_budget(conf, correct, b0),
            cov_b5=coverage_at_budget(conf, correct, b5),
            ece=ece(conf, correct))
    if verbose:
        print(f"hold-out n={n}  acc={correct.mean():.3f}  coverage={cov:.0%}  "
              f"budget b0={b0:.0f} (false@30 du scalaire)  b5={b5:.0f} (5% du hold-out)")
        print(f"{'method':28} {'r@10':>7} {'r@30':>7} {'r@50':>7} "
              f"{'false@30':>8} {'cov@b0':>7} {'cov@b5':>7} {'ECE':>7}")
        for name, r in rows.items():
            print(f"{name:28} {r['r10']:6.1%} {r['r30']:6.1%} {r['r50']:6.1%} "
                  f"{r['false_n']:8d} {r['cov_b0']:6.1%} {r['cov_b5']:6.1%} {r['ece']:7.3f}")
        s, mu = rows["scalar |p-0.5|"], rows["conf_multi_source"]
        d_r30 = (s["r30"] - mu["r30"]) * 100
        d_cb0 = (mu["cov_b0"] - s["cov_b0"]) * 100
        d_cb5 = (mu["cov_b5"] - s["cov_b5"]) * 100
        win = d_r30 > 0 or (d_cb0 > 0 and d_r30 >= 0)
        print(f"\nformula: conf = sigmoid_alu({m.k}*( "
              f"{m.w[0]}*s1 + {m.w[1]}*s2 + {m.w[2]}*s3) - {m.b})")
        print(f"calib NLL train: scalar={m.calib_nll['scalar']:.4f} "
              f"multi={m.calib_nll['multi']:.4f}")
        print(f"VERDICT: {'GAIN' if win else 'PAS DE GAIN'} vs scalaire — "
              f"risk@30 {d_r30:+.1f} pts, cov@b0 {d_cb0:+.1f} pts "
              f"(cov@b5 {d_cb5:+.1f} pts, secondaire)")
        if not win:
            print("=> multi-source NE BAT PAS le scalaire: garder la formule "
                  "la plus simple Phi(4|p-0.5|-1).")
    return rows


def diagnose():
    """Per-signal hold-out informativeness (does each source carry evidence?)."""
    m = get_model()
    S, P = m.signals_batch(m.Xte)
    correct = ((P >= 0.5) == m.yte)
    print("per-signal hold-out: risk@cov30 and mean signal ok/bad")
    for i, name in enumerate(("s1 margin", "s2 concurrence", "s3 length-LR")):
        r, _, _ = risk_at_coverage(S[:, i], correct, 0.3)
        print(f"  {name:14} risk@30={r:6.1%}  mean_ok={S[correct, i].mean():.3f}"
              f"  mean_bad={S[~correct, i].mean():.3f}")


def self_check():
    m = get_model()
    texts, y = make_dataset(200, 7)
    assert len(texts) == 200 and set(np.unique(y)) == {0.0, 1.0}

    S, P = m.signals_batch(np.array([features_from_text(t) for t in texts], np.float32))
    assert S.shape == (200, 3) and np.all(S >= 0) and np.all(S <= 1), "signals out of [0,1]"
    assert np.all((P >= 0) & (P <= 1))

    a_unan = _pair_agreement(np.full(4, 0.3))
    a_split = _pair_agreement(np.array([0.0, 1.0, 0.0, 1.0]))
    assert abs(a_unan - 1.0) < 1e-12, a_unan
    assert a_split < 0.5, a_split

    c = np.array([conf_multi_source(t) for t in texts])
    assert np.all(c >= 0.0) and np.all(c <= 1.0), "conf_multi out of [0,1]"
    assert 0.0 < c.mean() < 1.0

    correct = ((P >= 0.5) == y)
    scalar, current = S[:, 0], gaussian_cdf_fast(2.0 * S[:, 0] - 1.0)
    k = max(1, int(0.3 * len(texts)))
    ov = len(set(_topk(scalar, k)) & set(_topk(current, k))) / k
    assert ov >= 0.95, f"scalar/current ranking must match, overlap={ov:.2f}"
    assert ece(scalar, correct) >= 0.0

    rs, _, _ = risk_at_coverage(scalar, correct, 0.3)
    rm, _, _ = risk_at_coverage(c, correct, 0.3)
    assert 0 <= rs <= 1 and 0 <= rm <= 1
    print(f"self-check OK  (top-30% overlap scalar/current={ov:.2f}, "
          f"risk@30 scalar={rs:.1%} multi={rm:.1%})")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    self_check()
    print()
    diagnose()
    print()
    ablation()
    print()
    for t in ("exécute le bash fibonacci", "quoi est-ce que gelu ?",
              "écris une fonction lorentz", "salut, merci pour tout"):
        print(f"  signals={get_model().signals(t).round(3)} "
              f"multi={conf_multi_source(t):.3f} scalar={conf_scalar(t):.3f}  {t}")
    print("\nre-run: python multi_conf.py")
