"""Spear-fable: SpearEmb + TinyPolicy + LogisticGate + temperature scaling."""
from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt


# --- inline champion kernels to avoid circular import ---
def _tanh_pade(x: Any) -> Any:
    y = np.clip(np.asarray(x, float), -4.0, 4.0)
    return (0.994894946 * y + 0.076611228 * y**3) / (1.0 + 0.402171314 * y**2 + 0.005670342 * y**4)

def _sigmoid_alu(x: Any) -> Any:
    return 0.5 + 0.5 * _tanh_pade(0.5 * np.asarray(x, float))

def _silu_alu(x: Any) -> Any:
    x = np.asarray(x, float)
    return x * _sigmoid_alu(x)

def _gauss_kernel(x: Any) -> Any:
    return _tanh_pade(0.6 * np.asarray(x, float))

def _gelu_quintic(x: Any) -> Any:
    x = np.asarray(x, float)
    t = np.clip(0.200055340257 * x + 0.5, 0.0, 1.0)
    return x * t**3 * (6.0 * t * t - 15.0 * t + 10.0) - 0.01104961


class SpearEmb:
    """Random projection + 4 champion activations -> 16+4x8=48-dim embedding.

    Parameters
    ----------
    W : array (d_in x extra)
    mu : array (d_in,)
    sigma : array (d_in,)
    """

    def __init__(self, W: Any, mu: Any, sigma: Any) -> None:
        self.W = np.asarray(W, np.float32)
        self.mu = np.asarray(mu, np.float32)
        self.sigma = np.asarray(sigma, np.float32)
        self.acts = [_silu_alu, _gauss_kernel, _gelu_quintic, _tanh_pade]
        self.d_out = self.W.shape[0] + self.W.shape[1] * len(self.acts)

    @classmethod
    def fit(cls, X: Any, extra: int = 8, seed: int = 42) -> "SpearEmb":
        X = np.atleast_2d(np.asarray(X, np.float32))
        rng = np.random.RandomState(seed)
        W = (rng.randn(X.shape[1], extra) * 0.35).astype(np.float32)
        return cls(W, X.mean(0), X.std(0) + 1e-6)

    def transform(self, X: Any) -> npt.NDArray[Any]:
        X = np.atleast_2d(np.asarray(X, np.float32))
        alive = self.sigma > 1e-5
        Xn = np.where(alive, (X - self.mu) / np.where(alive, self.sigma, 1.0), 0.0)
        z = Xn @ self.W
        parts = [Xn] + [np.asarray(k(z), np.float32) for k in self.acts]
        return np.concatenate(parts, axis=1)


class TinyPolicy:
    """~few hundred-param MLP router 48->32->1. tanh_pade as activation.

    Parameters
    ----------
    W1 : array (d_in x h)
    b1 : array (h,)
    W2 : array (h x 1)
    b2 : array (1,)
    """

    def __init__(self, W1: Any, b1: Any, W2: Any, b2: Any) -> None:
        self.W1, self.b1 = np.asarray(W1, np.float32), np.asarray(b1, np.float32)
        self.W2, self.b2 = np.asarray(W2, np.float32), np.asarray(b2, np.float32)

    @classmethod
    def init(cls, d_in: int, h: int = 32, seed: int = 7) -> "TinyPolicy":
        rng = np.random.RandomState(seed)
        return cls(rng.randn(d_in, h) * (1.2 / np.sqrt(d_in)), np.zeros(h, np.float32),
                   rng.randn(h, 1) * 0.25, np.zeros(1, np.float32))

    def predict_proba(self, X: Any) -> npt.NDArray[Any]:
        X = np.atleast_2d(np.asarray(X, np.float32))
        a = _tanh_pade(X @ self.W1 + self.b1)
        return _sigmoid_alu(a @ self.W2 + self.b2)

    def fit(self, X: Any, y: Any, epochs: int = 120, lr: float = 0.05, seed: int = 0) -> None:
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
                a = _tanh_pade(z)
                pred = _sigmoid_alu(a @ self.W2 + self.b2)
                dL = np.clip((pred - yb) / len(b), -0.01, 0.01)
                self.W2 -= lr_t * (a.T @ dL)
                self.b2 -= lr_t * dL.sum(0)
                da = dL @ self.W2.T
                # d tanh_pade/dz approx via sech^2 of pade output (champion-legal)
                th = _tanh_pade(z)
                dz = da * (1.0 - th * th)
                self.W1 -= lr_t * (xb.T @ dz)
                self.b1 -= lr_t * dz.sum(0)


def _golden_nll(Xn: Any, y: Any, w: Any, b: Any, lo: float = 0.1, hi: float = 3.0, iters: int = 30) -> float:
    """Temperature scaling: golden-section minimization of NLL over [lo, hi]."""
    z = Xn @ w + b

    def nll(T: float) -> float:
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
    """Platt-scale logistic gate on 16 raw features, P(trivial).

    Parameters
    ----------
    mu : array (16,)
    sd : array (16,)
    w : array (16,)
    b : scalar bias
    T : temperature scaling factor (golden-section NLL fit)
    """

    def __init__(self, mu: Any, sd: Any, w: Any, b: float) -> None:
        self.mu, self.sd = np.asarray(mu, np.float64), np.asarray(sd, np.float64)
        self.w, self.b = np.asarray(w, np.float64), float(b)
        self.T = 1.0

    @classmethod
    def fit(cls, X: np.ndarray[Any, Any], y_trivial: np.ndarray[Any, Any],
            epochs: int = 400, lr: float = 0.5, seed: int = 0) -> "LogisticGate":
        from eval_harness import fit_lr  # lazy
        X = np.atleast_2d(np.asarray(X, np.float64))
        mu, sd = X.mean(0), X.std(0) + 1e-6
        y = np.asarray(y_trivial, np.float64)
        w, b = fit_lr((X - mu) / sd, y, epochs=epochs, lr=lr, seed=seed)
        T = _golden_nll((X - mu) / sd, y, w, b, lo=0.1, hi=3.0)
        obj = cls(mu, sd, w, b); obj.T = T; return obj

    def predict_instant_proba(self, text: str) -> float:
        from intuition import features_from_text
        f = np.asarray(features_from_text(text), np.float64)
        z = (((f - self.mu) / self.sd) @ self.w + self.b) / self.T
        return float(_sigmoid_alu(max(-30.0, min(30.0, z))))


def _lr_from_corpus(train_only: bool = True) -> LogisticGate:
    from eval_harness import build_corpus, stratified_split
    from intuition import features_from_text
    texts, y = build_corpus()
    if train_only:
        tr, _ = stratified_split(y)
        texts, y = [texts[i] for i in tr], y[tr]
    X = np.array([features_from_text(t) for t in texts], np.float32)
    return LogisticGate.fit(X, (y == 0).astype(np.float64))
