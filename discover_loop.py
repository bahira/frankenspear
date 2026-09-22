"""Discover missing kernels: package (node) -> numpy ports -> discovered.json."""
import json
import re
import subprocess
import numpy as np

import intuition
from champions_extra import EXTRA

ROOT = str(__import__("pathlib").Path(__file__).resolve().parent)


def _node_pkg():
    js = ("const p=require('spear-kernels');"
          "console.log(JSON.stringify({ids:p.kernelIds,k:p.kernels}));")
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True,
                         encoding="utf-8", cwd=ROOT)
    return json.loads(out.stdout.strip())


def all_ids():
    """Full kernelId list exposed by the spear-kernels package (89 entries)."""
    return _node_pkg()["ids"]


def _balance(s):
    # ponytail: package emits off-by-one parens on some js fields; pad/truncate to match
    o, c = s.count("("), s.count(")")
    if o > c:
        return s + ")" * (o - c)
    if c > o:
        return s[: len(s) - (c - o)]
    return s


def _js_eval(formula_js, args):
    call = f"{_balance(formula_js)}({', '.join(repr(a) for a in args)})"
    js = f"const f={_balance(formula_js)};console.log(JSON.stringify({call}));"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True,
                         encoding="utf-8", cwd=ROOT)
    return json.loads(out.stdout.strip())


_TERNARY = re.compile(r"\(([^()?]+)\?([^()?]+):([^()?]+)\)")


def _np_from_py(py_str):
    # ponytail: torch->numpy name map + JS-ternary rewrite; extend if specs drift
    s = py_str
    s = (s.replace("import torch", "")
         .replace("torch.maximum", "np.maximum")
         .replace("torch.minimum", "np.minimum")
         .replace("torch.relu", "_relu")
         .replace("torch.tanh", "np.tanh")
         .replace("torch.exp", "np.exp")
         .replace("torch.log", "np.log")
         .replace("torch.sqrt", "np.sqrt")
         .replace("torch.abs", "np.abs")
         .replace("torch.cos", "np.cos")
         .replace("torch.sin", "np.sin")
         .replace("torch.atan", "np.arctan")
         .replace("torch.clamp", "np.clip"))
    s = _TERNARY.sub(r"(\2 if \1 else \3)", s)
    code = s[s.index("def spear_fn"):]
    ns = {"np": np, "_relu": lambda x: np.maximum(x, 0.0)}
    exec(code, ns)
    return ns["spear_fn"]


SAMPLES1 = [-2.0, -0.5, 0.0, 1.0, 3.0]
SAMPLES2 = [(0.6, 2.0), (0.1, 9.0), (0.45, 1.0), (0.9, 0.5), (0.33, 3.0)]


def discover():
    pkg = _node_pkg()
    known = set(intuition.CHAMPIONS) | set(intuition.FAST)
    results = []
    for kid in pkg["ids"]:
        if kid in known:
            continue
        entry = {"id": kid, "added": False, "numpy": None, "max_rel_err_vs_js": None}
        fn = None
        if kid in EXTRA:
            fn = EXTRA[kid]
        else:
            meta = pkg["k"].get(kid, {})
            py = (meta.get("precise") or {}).get("py") or (meta.get("fast") or {}).get("py")
            if py:
                try:
                    fn = _np_from_py(py)
                except Exception:
                    fn = None
        if fn is None:
            results.append(entry)
            continue
        entry["added"] = True
        meta = pkg["k"][kid]
        slot = meta.get("precise") or meta.get("fast") or {}
        jsf = slot.get("js")
        if jsf:
            head = jsf.split("=>", 1)[0]
            try:
                nargs = fn.__code__.co_argcount
            except Exception:
                nargs = head.count(",") + 1 if "=>" in jsf else 1
            samples = SAMPLES2 if nargs >= 2 else SAMPLES1
            errs = []
            for s in samples:
                a = s if isinstance(s, tuple) else (s,)
                try:
                    jv = float(_js_eval(jsf, a))
                    nv = float(fn(*a))
                    errs.append(abs(nv - jv) / max(abs(jv), 1e-12))
                except Exception:
                    pass
            if errs:
                entry["max_rel_err_vs_js"] = max(errs)
        entry["numpy"] = getattr(fn, "__name__", repr(fn))
        results.append(entry)
    return results


if __name__ == "__main__":
    res = discover()
    with open(ROOT + r"\discovered.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    for r in res:
        print(r["id"], r["added"], r["max_rel_err_vs_js"])
