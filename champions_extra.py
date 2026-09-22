"""Numpy ports of spear-kernels package formulas (precise slot), not in intuition.py."""
import numpy as np


def mish(x):
    x = np.asarray(x, dtype=np.float64)
    e = np.exp(np.clip(x, -50.0, 50.0))
    return x * np.tanh(np.log(np.maximum(1e-30, 1.0 + e)))


def softplus(x):
    x = np.asarray(x, dtype=np.float64)
    e = np.exp(np.clip(x, -50.0, 50.0))
    return 1.002747 * np.log(np.maximum(1e-30, 1.010159 + e)) - 0.008384


def _safe_div(d, eps=1e-4):
    return np.where(np.abs(d) < eps, np.where(d >= 0, eps, -eps), d)


def bessel_j0(x):
    x = np.asarray(x, dtype=np.float64)
    num = (3.154708 + np.minimum(3.154708, x)) + (np.minimum(3.396868, x) * np.minimum(2.050039, x))
    den = _safe_div(np.maximum(4.359564, x))
    return np.clip(-0.6162005993906633 * (num / den), -1e4, 1e4) + 1.48653822658716


def lambert_w(x):
    x = np.asarray(x, dtype=np.float64)
    return x * np.maximum(0.0, np.exp(np.clip(x, -50.0, 50.0)))


def kelly_criterion(p, b):
    p = np.asarray(p, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    term = np.clip((1.000014 - p) / _safe_div(b), -1e4, 1e4)
    return 1.000326 * np.maximum(0.0003, p - term) - 0.000194


def rsi_momentum(g, l):
    g = np.asarray(g, dtype=np.float64)
    l = np.asarray(l, dtype=np.float64)
    return 100.0 * np.clip(g / _safe_div(g + l), -1e4, 1e4)


def logsumexp2(b, a):
    b = np.asarray(b, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    inner = np.maximum(b, np.maximum(a, b)) - 0.863454
    return 0.9884453418513615 * np.maximum(np.minimum(b, a), inner) + 0.9463635441197152


def smoothstep(x):
    x = np.asarray(x, dtype=np.float64)
    return -1.9883720211312108 * (x * x * (x - 1.503545)) + 0.0005544574268407132


EXTRA = {
    "mish": mish,
    "softplus": softplus,
    "bessel_j0": bessel_j0,
    "lambert_w": lambert_w,
    "kelly_criterion": kelly_criterion,
    "rsi_momentum": rsi_momentum,
    "logsumexp2": logsumexp2,
    "smoothstep": smoothstep,
}
