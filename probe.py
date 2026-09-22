import json, numpy as np, intuition as I
d = json.load(open("slm-weights-q8.json", encoding="utf-8"))
s = d["scale"]
dec = lambda v: [dec(x) for x in v] if isinstance(v, list) else ({k: dec(x) for k, x in v.items()} if isinstance(v, dict) else v / s)
d = {k: dec(v) for k, v in d.items() if k != "scale"}
W = np.asarray(d["W"]); mu = np.asarray(d["mu"]); sg = np.asarray(d["sigma"])
W1 = np.asarray(d["W1"]); b1 = np.asarray(d["b1"]); W2 = np.asarray(d["W2"]); b2 = np.asarray(d["b2"])
for t in ("salut", "écris une fonction gelu", "exécute le bash", "quantum chsh grover concurrence", "quoi est-ce que tanh"):
    f = np.asarray(I.features_from_text(t), np.float64)
    xn = np.where(sg > 1e-5, (f - mu) / np.where(sg > 1e-5, sg, 1), 0)
    z = xn @ W
    parts = [xn] + [np.asarray(k2(z), np.float64) for k2 in [I.silu_alu, I.gauss_kernel, I.gelu_quintic, I.tanh_pade]]
    zz = np.concatenate(parts)
    a = I.tanh_pade(zz @ W1 + b1)
    p = float(I.sigmoid_alu(a @ W2 + b2)[0])
    conf = float(I.gaussian_cdf_fast(4.0 * abs(p - 0.5) - 1.0))
    path = "instant" if (p < 0.5 and conf >= 0.65) else "slow"
    print(t, round(p, 3), round(conf, 3), path)
lr = d["lr"]
for t in ("salut", "écris une fonction gelu"):
    f = np.asarray(I.features_from_text(t), np.float64)
    z = lr["b"] + float(((f - np.asarray(lr["mu"])) / np.where(np.asarray(lr["sd"]) > 0, np.asarray(lr["sd"]), 1)) @ np.asarray(lr["w"]))
    pt = float(I.sigmoid_alu(np.clip(z, -30, 30)))
    print("lr", t, round(pt, 3), "instant" if pt >= 0.5 else "slow")
