import json
import subprocess
import numpy as np
from discover_loop import discover, _js_eval

TOL = 1e-4

PTS = {
    "mish": [-3.0, -0.5, 0.0, 1.0, 2.5],
    "softplus": [-3.0, -0.5, 0.0, 1.0, 2.5],
    "bessel_j0": [-3.0, -0.5, 0.0, 1.0, 2.5],
    "lambert_w": [-3.0, -0.5, 0.0, 1.0, 2.5],
    "smoothstep": [-3.0, -0.5, 0.0, 1.0, 2.5],
}
PTS2 = {
    "kelly_criterion": [(0.6, 2.0), (0.1, 9.0), (0.45, 1.0), (0.9, 0.5), (0.33, 3.0)],
    "rsi_momentum": [(12.0, 3.0), (0.5, 0.0), (45.0, 17.0), (1.0, 2.0), (0.0, 4.0)],
    "logsumexp2": [(1.0, 2.0), (-1.0, 0.5), (3.0, 3.0), (0.0, -2.0), (0.2, 0.7)],
}


def _js(formula, args):
    return _js_eval(formula, args)


def test_discovered_kernels():
    from champions_extra import EXTRA
    res = {r["id"]: r for r in discover()}
    assert set(EXTRA) <= set(res)
    for kid, fn in EXTRA.items():
        pts = PTS.get(kid) or PTS2.get(kid)
        assert pts, kid
        jsf = None
        pkg = json.loads(subprocess.run(
            ["node", "-e", "const p=require('spear-kernels');console.log(JSON.stringify(p.kernels));"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=r"C:\Users\Yuri\Documents\frankenspear").stdout.strip())
        jsf = pkg[kid]["precise"]["js"]
        errs = []
        for p in pts:
            a = (p,) if isinstance(p, float) else tuple(p)
            jv = float(_js(jsf, a))
            nv = float(fn(*a))
            errs.append(abs(nv - jv) / max(abs(jv), 1e-12))
        mre = max(errs)
        assert mre < TOL, f"{kid}: max_rel_err={mre}"
        assert res[kid]["added"] is True
    print("OK", len(EXTRA), "kernels, all max_rel_err <", TOL)


if __name__ == "__main__":
    test_discovered_kernels()
