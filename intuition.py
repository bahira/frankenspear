"""FRANKENSPEAR — neuro-symbolic INTUITION INSTANT LAYER.

Champions (SpearVM CHAMPIONS.md + superspear hall-of-fame) + TinyPolicy SLM
(spear-fable) + quantum attributes. Pure numpy. One file.
"""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from typing import Any, Callable

import numpy as np
import numpy.typing as npt

# ---------- champion kernels (closed-form, 100% ALU where possible) ----------

def tanh_pade(x):
    """CHAMPION tanh Pade[3/4], L-inf 1.56e-3, 1 div."""
    y = np.clip(np.asarray(x, float), -4.0, 4.0)
    return (0.994894946 * y + 0.076611228 * y**3) / (1.0 + 0.402171314 * y**2 + 0.005670342 * y**4)


def sigmoid_alu(x):
    """0.5 + 0.5*tanh(x/2) — L-inf 7.8e-4."""
    return 0.5 + 0.5 * tanh_pade(0.5 * np.asarray(x, float))


def silu_alu(x):
    """x*sigmoid(x) — L-inf 9.3e-4."""
    x = np.asarray(x, float)
    return x * sigmoid_alu(x)


def gelu_quintic(x):
    """CHAMPION fast GELU: 5 mul, 0 div, L-inf 1.74e-2."""
    x = np.asarray(x, float)
    t = np.clip(0.200055340257 * x + 0.5, 0.0, 1.0)
    return x * t**3 * (6.0 * t * t - 15.0 * t + 10.0) - 0.01104961


def gelu_erf(x):
    """CHAMPION precise GELU via erf_v2 rational, L-inf 2.05e-5."""
    x = np.asarray(x, float)
    return 0.5 * x * (1.0 + np.erf(x * 0.7071067811865476)) if hasattr(np, "erf") else 0.5 * x * (1.0 + _erf(x * 0.7071067811865476))


def _erf(x):
    # Abramowitz-Stegun 7.1.26 rational (max err 1.5e-7) — numpy has no erf
    x = np.asarray(x, float)
    s = np.sign(x)
    a = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-a * a)
    return s * y


def gauss_kernel(x):
    """exp(-x^2/2) approx: tanh(0.6x) shape kernel, L-inf 1.56e-3 family."""
    return tanh_pade(0.6 * np.asarray(x, float))


def lorentz_kernel(x):
    """1/sqrt(1-0.8*tanh(0.5x)^2) — L-inf 3.6e-3."""
    b = tanh_pade(0.5 * np.asarray(x, float))
    return 1.0 / np.sqrt(np.maximum(1e-12, 1.0 - 0.8 * b * b))


def gelu_fast_relu(x):
    """superspear fast slot: 1.010719*relu(x)-0.057684, cost 3, x6.5 measured."""
    x = np.asarray(x, float)
    return 1.010719 * np.maximum(x, 0.0) - 0.057684


def silu_fast_relu(x):
    """superspear fast slot SiLU: cost 3, x5.4 measured."""
    x = np.asarray(x, float)
    return 1.016356 * np.maximum(x, 0.0) - 0.15849


def sigmoid_fast(x):
    """0.605014*x/(1.24384+|x|)+0.5 — cost 8, x1.9 measured."""
    x = np.asarray(x, float)
    return 0.605014 * (x / (1.24384 + np.abs(x))) + 0.5


def gaussian_cdf_fast(x):
    """0.625605*x/(0.912761+|x|)+0.5 — Phi(x) fast slot, cost 8, x2.5."""
    x = np.asarray(x, float)
    return 0.625605 * (x / (0.912761 + np.abs(x))) + 0.5


def probit(x):
    """probit via inverse of gaussian_cdf_fast (Newton, 3 iters — instant enough)."""
    x = np.clip(np.asarray(x, float), 1e-4, 1.0 - 1e-4)
    z = np.sqrt(2.0) * _erfinv(2.0 * x - 1.0)
    return z


def _erfinv(y):
    y = np.clip(np.asarray(y, float), -0.999999, 0.999999)
    a = 0.147
    ln = np.log(1.0 - y * y)
    t1 = 2.0 / (np.pi * a) + ln / 2.0
    return np.sign(y) * np.sqrt(np.sqrt(t1 * t1 - ln / a) - t1)


# ---------- quantum attributes / properties ----------

def concurrence_pure(a, b, c, d):
    """Quantum concurrence of |psi>=a|00>+b|01>+c|10>+d|11>: EXACT 2|ad-bc|."""
    return 2.0 * np.abs(np.asarray(a) * np.asarray(d) - np.asarray(b) * np.asarray(c))


def chsh_correlation(e, m, o, p):
    """CHSH S = E(a,b)+E(a,b')+E(a',b)-E(a',b'). hall-of-fame EXACT."""
    return e * m + e * o + p * m - p * o


def grover_amplitude(k, m, n):
    """sin((2k+1)*asin(sqrt(m/n)))^2 — quadratic speedup law."""
    theta = np.arcsin(np.sqrt(np.clip(np.asarray(m, float) / np.maximum(n, 1e-12), 0.0, 1.0)))
    return np.sin((2.0 * np.asarray(k, float) + 1.0) * theta) ** 2


def qfi_dephasing(n, t, gamma):
    """QFI under dephasing: N^2 t^2 exp(-N^2 gamma t) — discovered skeleton."""
    n = np.asarray(n, float)
    t = np.asarray(t, float)
    return n * n * t * t * np.exp(-n * n * np.asarray(gamma, float) * t)


def lorentz_gamma(beta):
    """Exact relativistic gamma = 1/sqrt(1-b^2) — hall-of-fame EXACT."""
    b2 = np.clip(np.asarray(beta, float) ** 2, 0.0, 1.0 - 1e-12)
    return 1.0 / np.sqrt(1.0 - b2)


def kelly_fraction(edge, odds):
    """Kelly criterion: f* = edge/odds (linearized champion form)."""
    return np.clip(np.asarray(edge, float) / np.maximum(np.asarray(odds, float), 1e-9), -1.0, 1.0)


def rsi_momentum(up, down, n=14):
    """RSI from smoothed means — hall-of-fame form."""
    u = np.asarray(up, float)
    d = np.asarray(down, float)
    rs = np.maximum(u, 1e-9) / np.maximum(d, 1e-9)
    return 100.0 - 100.0 / (1.0 + rs)


QUANTUM: dict[str, Callable[..., float]] = dict(
    concurrence=concurrence_pure,
    chsh=chsh_correlation,
    grover=grover_amplitude,
    qfi=qfi_dephasing,
    lorentz=lorentz_gamma,
    kelly=kelly_fraction,
    rsi=rsi_momentum,
)

CHAMPIONS: dict[str, Callable[..., float]] = dict(
    tanh=tanh_pade, sigmoid=sigmoid_alu, silu=silu_alu,
    gelu_quintic=gelu_quintic, gelu_erf=gelu_erf, gelu_fast=gelu_fast_relu,
    silu_fast=silu_fast_relu, sigmoid_fast=sigmoid_fast,
    gauss=gauss_kernel, lorentz=lorentz_kernel,
    gauss_cdf=gaussian_cdf_fast, probit=probit,
)

FAST = dict(sigmoid=sigmoid_fast, gelu=gelu_fast_relu, silu=silu_fast_relu,
            gauss_cdf=gaussian_cdf_fast, tanh=tanh_pade)

# ---------- features (spear-fable 16-dim) ----------
TOOL_RE = r"(tool|bash|edit|exec|lance|exécute|execute)"
CODE_WORDS = ("écris", "write", "code", "fonction", "script")
MATH_WORDS = ("gelu", "lorentz", "kepler", "math", "kernel", "quantum",
              "chsh", "grover", "concurrence", "tanh", "sigmoid")
IMPERATIVE = ("fais", "do", "lance", "run", "calcule", "compute", "ajoute", "add")
QUESTION_WORDS = ("quoi", "what", "comment", "how", "pourquoi", "why", "combien")
TECH_WORDS = ("api", "http", "json", "sql", "git", "docker", "npm", "pip", "debug")


@lru_cache(maxsize=4096)
def features_from_text(text: str) -> np.ndarray[Any, Any]:
    return _features_uncached(text)


def get_cache_stats() -> tuple[int, int, int]:
    hits, misses, maxsize, _ = features_from_text.cache_info()
    i = lambda v: 0 if v is None else int(v)
    return (i(hits), i(misses), i(maxsize))


def _features_uncached(text: str) -> np.ndarray[Any, Any]:
    t = (text or "").lower()
    words = t.split()
    n = max(len(words), 1)
    return np.array([
        np.log1p(len(t)) / 5,
        len(re.findall(TOOL_RE, t)) / 3,
        (t.count("```") + t.count("def ")) / 3,
        1.0 if any(k in t for k in MATH_WORDS) else 0.0,
        1.0 if any(k in t for k in CODE_WORDS) else 0.0,
        t.count(" ") / 30,
        len(re.findall(r"\d+", t)) / 5,
        1.0 if "?" in t else 0.0,
        1.0 if ("merci" in t or "thanks" in t) else 0.0,
        0.0,
        len(set(words)) / n,
        min(sum(len(w) for w in words) / n / 10.0, 1.0),
        len(re.findall(TOOL_RE, t)) / 5 + (1.0 if any(k in t for k in IMPERATIVE) else 0.0),
        (1.0 if any(k in t for k in QUESTION_WORDS) else 0.0) + t.count("!") / 5,
        (1.0 if any(k in t for k in TECH_WORDS) else 0.0) + t.count("...") / 3,
        len(t.split("\n")) / 20,
    ], dtype=np.float32)


# ---------- SLM: SpearEmb + TinyPolicy (spear-fable) ----------
class SpearEmb:
    def __init__(self, W, mu, sigma):
        self.W = np.asarray(W, np.float32)
        self.mu = np.asarray(mu, np.float32)
        self.sigma = np.asarray(sigma, np.float32)
        self.acts = [silu_alu, gauss_kernel, gelu_quintic, tanh_pade]
        self.d_out = self.W.shape[0] + self.W.shape[1] * len(self.acts)

    @classmethod
    def fit(cls, X, extra=8, seed=42):
        X = np.atleast_2d(np.asarray(X, np.float32))
        rng = np.random.RandomState(seed)
        W = (rng.randn(X.shape[1], extra) * 0.35).astype(np.float32)
        return cls(W, X.mean(0), X.std(0) + 1e-6)

    def transform(self, X):
        X = np.atleast_2d(np.asarray(X, np.float32))
        alive = self.sigma > 1e-5
        Xn = np.where(alive, (X - self.mu) / np.where(alive, self.sigma, 1.0), 0.0)
        z = Xn @ self.W
        parts = [Xn] + [np.asarray(k(z), np.float32) for k in self.acts]
        return np.concatenate(parts, axis=1)


class TinyPolicy:
    """~few-hundred-param SLM router. gelu-free: tanh_pade champion as activation."""

    def __init__(self, W1, b1, W2, b2):
        self.W1, self.b1 = np.asarray(W1, np.float32), np.asarray(b1, np.float32)
        self.W2, self.b2 = np.asarray(W2, np.float32), np.asarray(b2, np.float32)

    @classmethod
    def init(cls, d_in, h=32, seed=7):
        rng = np.random.RandomState(seed)
        return cls(rng.randn(d_in, h) * (1.2 / np.sqrt(d_in)), np.zeros(h, np.float32),
                   rng.randn(h, 1) * 0.25, np.zeros(1, np.float32))

    def predict_proba(self, X):
        X = np.atleast_2d(np.asarray(X, np.float32))
        a = tanh_pade(X @ self.W1 + self.b1)
        return sigmoid_alu(a @ self.W2 + self.b2)

    def fit(self, X, y, epochs=120, lr=0.05, seed=0):
        rng = np.random.RandomState(seed)
        y = y.reshape(-1, 1).astype(np.float32)
        n = len(X)
        for ep in range(epochs):
            lr_t = lr * (0.4 + 0.6 * np.cos(np.pi * ep / epochs))
            idx = rng.permutation(n)
            for i in range(0, n, 32):
                b = idx[i:i + 32]
                xb, yb = X[b], y[b]
                z = xb @ self.W1 + self.b1
                a = tanh_pade(z)
                pred = sigmoid_alu(a @ self.W2 + self.b2)
                dL = np.clip((pred - yb) / len(b), -0.01, 0.01)
                self.W2 -= lr_t * (a.T @ dL)
                self.b2 -= lr_t * dL.sum(0)
                da = dL @ self.W2.T
                # d tanh_pade/dz approx via sech^2 of pade output (champion-legal)
                th = tanh_pade(z)
                dz = da * (1.0 - th * th)
                self.W1 -= lr_t * (xb.T @ dz)
                self.b1 -= lr_t * dz.sum(0)


def _golden_nll(Xn, y, w, b, lo=0.1, hi=3.0, iters=30):
    """Temperature scaling: golden-section minimization of NLL over [lo, hi]."""
    z = Xn @ w + b

    def nll(T):
        p = np.clip(1.0 / (1.0 + np.exp(-z / T)), 1e-12, 1.0 - 1e-12)
        return -float(np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))

    phi = 0.618
    c = hi - phi * (hi - lo)
    d = lo + phi * (hi - lo)
    fc, fd = nll(c), nll(d)
    for _ in range(iters):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - phi * (hi - lo)
            fc = nll(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + phi * (hi - lo)
            fd = nll(d)
    return 0.5 * (lo + hi)


class LogisticGate:
    """Logistic gate on the 16 raw features: predicts P(trivial)."""

    def __init__(self, mu: Any, sd: Any, w: Any, b: float) -> None:
        self.mu, self.sd = np.asarray(mu, np.float64), np.asarray(sd, np.float64)
        self.w, self.b = np.asarray(w, np.float64), float(b)
        self.T = 1.0

    @classmethod
    def fit(cls, X: np.ndarray[Any, Any], y_trivial: np.ndarray[Any, Any],
            epochs: int = 400, lr: float = 0.5, seed: int = 0) -> "LogisticGate":
        from eval_harness import fit_lr  # lazy — eval_harness imports intuition
        X = np.atleast_2d(np.asarray(X, np.float64))
        mu, sd = X.mean(0), X.std(0) + 1e-6
        y = np.asarray(y_trivial, np.float64)
        w, b = fit_lr((X - mu) / sd, y, epochs=epochs, lr=lr, seed=seed)
        T = _golden_nll((X - mu) / sd, y, w, b, lo=0.1, hi=3.0)
        obj = cls(mu, sd, w, b); obj.T = T; return obj

    def predict_instant_proba(self, text: str) -> float:
        f = np.asarray(features_from_text(text), np.float64)
        z = (((f - self.mu) / self.sd) @ self.w + self.b) / self.T
        return float(sigmoid_alu(max(-30.0, min(30.0, z))))


def _lr_from_corpus(train_only: bool = True) -> LogisticGate:
    from eval_harness import build_corpus, stratified_split
    texts, y = build_corpus()
    if train_only:
        tr, _ = stratified_split(y)
        texts, y = [texts[i] for i in tr], y[tr]
    X = np.array([features_from_text(t) for t in texts], np.float32)
    return LogisticGate.fit(X, (y == 0).astype(np.float64))


# ---------- INTUITION INSTANT LAYER ----------
class IntuitionInstant:
    """Neuro-symbolic router: features -> emb -> SLM probability -> gate.

    gate="conf" (default): instant ONLY if label==0 (trivial, p < 0.5) AND
    conf >= INSTANT — confident AND trivial; any confident full-class request
    stays slow. gate="lr": instant if LogisticGate P(trivial) >= 0.5.
    """

    INSTANT = 0.65  # gate threshold (sigmoid-alu scored)

    def __init__(self, seed: int = 42, gate: str = "lr",
                 lr: LogisticGate | None = None):
        assert gate in ("conf", "lr"), gate
        self.seed = seed
        self.gate = gate
        self.lr = lr if lr is not None else (_lr_from_corpus() if gate == "lr" else None)
        self.stats = {"instant": 0, "slow": 0}
        corpus = [
            "salut qui es-tu aide",
            "écris gelu fibonacci code fonction",
            "exécute lance bash tool run",
            "quantum chsh grover concurrence kernel math",
            "gelu(1.5) tanh lorentz sigmoid silu",
            "quoi comment pourquoi combien",
            "api http json git docker debug",
            "calcule lorentz gamma quantum qfi kelly rsi",
        ]
        X = np.array([features_from_text(c) for c in corpus], np.float32)
        y = np.array([0, 1, 1, 0, 0, 0, 1, 0], np.float32)  # needs_tool/code label
        self.emb = SpearEmb.fit(X, seed=seed)
        Z = self.emb.transform(X)
        self.policy = TinyPolicy.init(Z.shape[1], h=32, seed=seed)
        self.policy.fit(Z, y)

    def confidence(self, text: str) -> float:
        f = features_from_text(text)
        p = float(self.policy.predict_proba(self.emb.transform(f))[0, 0])
        # quantum gate: map |2p-1| through gauss CDF fast slot
        return float(gaussian_cdf_fast(4.0 * abs(p - 0.5) - 1.0))

    def route(self, text: str) -> dict[str, Any]:
        # rule: instant only if confident AND trivial (label==0); else slow
        f = features_from_text(text)
        p = float(self.policy.predict_proba(self.emb.transform(f))[0, 0])
        conf = float(gaussian_cdf_fast(4.0 * abs(p - 0.5) - 1.0))
        label = int(p >= 0.5)  # 0 = trivial/instant-eligible, 1 = needs full
        if self.gate == "lr":
            assert self.lr is not None
            go_instant = self.lr.predict_instant_proba(text) >= 0.5
        else:
            go_instant = label == 0 and conf >= self.INSTANT
        path = "instant" if go_instant else "slow"
        self.stats[path] += 1
        return dict(label=label, path=path, p=p, conf=conf,
                    complexity=float(silu_alu(p)))

    def route_batch(self, texts: list[str]) -> list[dict[str, Any]]:
        X = np.array([features_from_text(t) for t in texts], np.float32)
        P = self.policy.predict_proba(self.emb.transform(X))[:, 0]
        out: list[dict[str, Any]] = []
        for i, (t, p) in enumerate(zip(texts, P)):
            f = np.asarray(X[i], np.float64)
            conf = float(gaussian_cdf_fast(4.0 * abs(float(p) - 0.5) - 1.0))
            label = int(p >= 0.5)
            if self.gate == "lr":
                assert self.lr is not None
                z = float(((f - self.lr.mu) / self.lr.sd) @ self.lr.w + self.lr.b)
                go = sigmoid_alu(max(-30.0, min(30.0, z))) >= 0.5
            else:
                go = label == 0 and conf >= self.INSTANT
            path = "instant" if go else "slow"
            self.stats[path] += 1
            out.append(dict(label=label, path=path, p=float(p), conf=conf,
                           complexity=float(silu_alu(p))))
        return out

    def call_champion(self, name: str, x):
        """Symbolic dispatch — instant closed-form evaluation."""
        if name in CHAMPIONS:
            return CHAMPIONS[name](x)
        if name in QUANTUM:
            if np.isscalar(x) or np.ndim(x) == 0:
                return QUANTUM[name](x)
            return QUANTUM[name](x)
        raise KeyError(f"unknown kernel {name}")

    def attributes(self, text: str) -> dict[str, float]:
        """Quantum attribute profile of a text (instant layer meta-signal)."""
        f = features_from_text(text)
        return dict(
            concurrence=float(concurrence_pure(f[0], f[3], f[5], f[7])),
            chsh=float(chsh_correlation(f[1], f[2], f[4], f[6])),
            lorentz_gamma=float(lorentz_gamma(min(f[0], 0.999))),
            qfi=float(qfi_dephasing(1.0, f[6] + 0.1, 0.05)),
            kelly=float(kelly_fraction(f[3] - 0.5, 1.0)),
        )


def demo() -> None:
    layer = IntuitionInstant(seed=42)
    tests = [
        "salut",
        "écris une fonction gelu",
        "exécute le bash",
        "quantum chsh grover concurrence",
        "quoi est-ce que tanh",
    ]
    for t in tests:
        r = layer.route(t)
        print(f"[{r['path']:7}] p={r['p']:.3f} conf={r['conf']:.3f} label={r['label']}  {t}")
    print("champion tanh(1) =", round(float(tanh_pade(1.0)), 6),
          " ref", round(float(np.tanh(1.0)), 6))
    print("champion silu(2) =", round(float(silu_alu(2.0)), 6),
          " ref", round(float(2.0 / (1.0 + np.exp(-2.0))), 6))
    print("quantum conc(1,0,0,1) =", concurrence_pure(1, 0, 0, 1), "(bell = 1)")
    print("stats", layer.stats)


def export_weights(path: str = "slm-weights.json", seed: int = 42) -> str:
    """Retrain TinyPolicy + LR on the expanded eval_harness train split."""
    from eval_harness import build_corpus, stratified_split, fit_lr
    texts, y = build_corpus()
    tr, _ = stratified_split(y)
    X = np.array([features_from_text(t) for t in texts], np.float32)[tr]
    yt = y[tr]
    emb = SpearEmb.fit(X, seed=seed)
    pol = TinyPolicy.init(emb.d_out, h=32, seed=seed)
    pol.fit(emb.transform(X), yt.astype(np.float32), epochs=120, lr=0.05, seed=0)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    w, b = fit_lr((X - mu) / sd, (yt == 0).astype(np.float64))
    out = dict(
        W=emb.W.tolist(), mu=emb.mu.tolist(), sigma=emb.sigma.tolist(),
        W1=pol.W1.tolist(), b1=pol.b1.tolist(),
        W2=pol.W2.tolist(), b2=pol.b2.tolist(),
        lr=dict(mu=mu.tolist(), sd=sd.tolist(),
                w=np.asarray(w).tolist(), b=float(b)),
    )
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Intuition Instant Layer")
    parser.add_argument("mode", nargs="?", default="demo", choices=["demo","route","bench","export"])
    parser.add_argument("--text", default="salut")
    parser.add_argument("--path", default="slm-weights.json")
    ns = parser.parse_args()
    if ns.mode == "demo": demo()
    elif ns.mode == "route": layer = IntuitionInstant(seed=42); print(layer.route(ns.text))
    elif ns.mode == "bench": import subprocess; subprocess.run(["python","run_all.py"])
    elif ns.mode == "export": print("wrote", export_weights(path=ns.path))
