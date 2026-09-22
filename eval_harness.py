"""eval_harness.py — hold-out eval of the intuition.py instant gate + baselines.

Label mapping (intuition.py demo): y=0 trivial/instant-eligible, y=1 needs_tool/full.
Gate: conf >= 0.65 -> instant, else slow. Writes eval_report.json.
"""
from __future__ import annotations

import argparse
import json

import numpy as np

from intuition import (
    IntuitionInstant,
    SpearEmb,
    TinyPolicy,
    features_from_text,
    gaussian_cdf_fast,
)

SEED = 42
THR = 0.65
TEST_FRAC = 0.2

# ---------- corpus: 0 = trivial/instant, 1 = needs_tool/full ----------
GREET = [
    "salut", "salut !", "hello", "hi", "bonjour", "bonsoir", "hey", "coucou",
    "good morning", "good evening", "greetings", "hello there", "bonjour à tous",
    "hi opencode", "salut l'équipe", "hey how are you", "comment ça va ?",
    "ça va ?", "bonjour, comment allez-vous ?", "hello friend", "salut Yuri",
    "hey team", "bonne nuit", "good night", "à plus", "see you",
    "coucou, tu es là ?", "yo", "hey there", "salut salut",
]
TRIVIA = [
    "c'est quoi python", "what is python", "qui es-tu", "who are you",
    "c'est quoi une liste en python", "what time is it", "quelle heure est-il",
    "c'est quoi la capitale de la France", "what is the capital of France",
    "combien font 2+2", "qui a écrit guerre et paix", "who wrote hamlet",
    "c'est quoi json", "what is json", "comment on dit bonjour en anglais",
    "how do you say thanks in french", "c'est quoi une API", "what is an API",
    "quel temps fait-il à Paris", "what color is the sky", "c'est quoi le bouton start",
    "quel est le président", "what is 10 times 3", "c'est quoi une variable",
    "what does HTML stand for", "oui ou non", "ok", "mmh",
]
MATH = [
    "calcule gelu(1.5)", "gelu(1.5)", "tanh(0.8)", "what is tanh of 2",
    "sigmoid(0.5)", "silu(1.2)", "lorentz gamma beta 0.9", "gamma lorentzien à v=0.9c",
    "calcule la concurrence de l'état de bell", "concurrence of bell state",
    "chsh correlation e=0.7 m=0.5 o=0.5 p=0.7", "grover amplitude k=1 m=2 n=4",
    "qfi dephasing n=3 t=0.5 gamma=0.01", "kelly fraction edge 0.1 odds 2",
    "rsi momentum up down", "quantum chsh grover concurrence kernel math",
    "calcule lorentz gamma quantum qfi kelly rsi", "gelu(1.5) tanh lorentz sigmoid silu",
    "probit 0.975", "gaussian cdf of 1.96", "kepler third law calculator",
    "math kernel derivative of x^2", "dérivée de x^2", "2+2", "sqrt(16)",
    "factorielle de 10", "combien font 12*12", "what is 15% of 200",
    "integrale de 0 à 1 de x dx", "derive sin(x)", "tanh pade approximation error",
    "sigmoid vs tanh différence", "quantum entanglement definition",
    "champion gelu fast relu cost", "probit inverse de 0.5",
    "erreur erf de Abramowitz Stegun",
]
THANKS = [
    "merci", "thanks", "merci beaucoup", "thank you so much", "ok merci",
    "super, merci !", "parfait", "perfect", "top", "nice", "bien joué", "good job",
]
EMPTY = ["", "   ", "\n", "\t "]

CODE = [
    "écris une fonction python qui trie une liste", "write a function to parse csv",
    "code une classe User en python", "fais un script bash de backup",
    "écris un script qui download une url", "write a recursive fibonacci in c",
    "code me a binary search", "écris une fonction gelu fibonacci code fonction",
    "write unit tests for my module", "écris des tests",
    "génère un script de déploiement", "make a function that merges two sorted arrays",
    "écris une API flask", "code un endpoint REST",
    "write a python decorator for caching", "écris une fonction récursive de factorielle",
    "implement quicksort in go", "écris du code pour parser du json",
    "write a dockerfile for this app", "fais moi un script cron",
    "écris une fonction qui additionne deux nombres",
    "create a react component for a button", "écris un hook useEffect",
    "write sql migration for users table", "code un worker celery",
    "build me a cli tool in rust", "écris un parseur yaml", "write a makefile",
    "fais un script python qui nettoie un csv", "écris une classe Database en java",
    "implement Dijkstra in python", "write a regex to match emails",
    "écris une fonction de hachage sha256", "code un bot discord",
    "create table schema for orders", "écris un plugin vscode",
    "write a github action workflow", "fais une fonction map reduce",
    "écris une binomial coefficient function",
    "generate boilerplate for express server", "écris un client grpc",
    "write a parser for protobuf", "make a function to flatten nested lists",
]
BASH = [
    "exécute ls -la", "lance le bash pwd", "run git status", "exec du -sh",
    "tool: search files for TODO", "exécute la commande npm install",
    "lancer docker compose up", "run the test suite", "execute pytest",
    "lance le build", "run make all", "exécute un curl vers l'api",
    "lance le serveur dev", "run npm run dev", "execute git push origin main",
    "exécute lance bash tool run", "show disk usage with du", "list processes",
    "kill process 1234", "exécute whoami", "lance htop", "run python script.py",
    "execute powershell Get-Process", "lance le grep sur les logs",
    "find files modified today", "exécute df -h", "install dependencies with pip",
    "run the migration script", "deploy to staging", "exécute le job nightly",
    "restart the service", "tail the log file", "exécute chmod +x",
    "lance la compilation", "run benchmarks", "execute the binary",
    "fetch latest commits", "exécute git pull", "lance le daemon", "run cleanup job",
]
TECH = [
    "api http json git docker debug", "debug ce bug de segmentation fault",
    "docker container won't start, fix it", "git merge conflict à résoudre",
    "npm install fails with EACCES", "sql query trop lente, optimise",
    "http 500 error on /login", "mon pipeline ci casse, répare",
    "le build webpack échoue", "debug memory leak in node",
    "pip dependency conflict", "ssh connection refused, debug",
    "ssl certificate expired, fix", "docker build cache busted",
    "kubernetes pod en crashloop", "redis connection timeout",
    "postgres deadlock detected", "nginx 502 bad gateway",
    "cors blocked in browser", "typescript type error TS2345",
    "vue runtime warning", "npm ERR missing script", "git rebase gone wrong",
    "flask debug mode production", "out of memory during build",
    "port 3000 already in use", "permission denied on key",
    "rust borrow checker error",
]
TASKS = [
    "traduis ce paragraphe en anglais et analyse le style",
    "résume ce long article et donne les points clés",
    "compare ces deux approches et recommande une",
    "review ce pull request en détail",
    "analyse ces logs d'erreur et trouve la cause",
    "classe ces 100 avis clients par sentiment",
    "extrais toutes les dates de ce document",
    "réécris ce texte en plus professionnel",
    "optimise ce code pour le rendre plus rapide",
    "migre ce code vers typescript",
    "audite la sécurité de ce endpoint",
    "profile ce script et trouve les goulots",
]
LONG_PFX = [
    "Analyse ce journal de production et identifie les incidents critiques : ",
    "Résume ce rapport financier trimestriel détaillé : ",
    "Review this entire codebase diff and list every bug : ",
    "Explique l'architecture de ce système distribué à partir de ces specs : ",
    "Extrais les métriques clés de ces 500 lignes de logs : ",
    "Traduis et localise ce manuel technique complet en français : ",
    "Débogue cette stack trace complète et propose un fix : ",
    "Compare ces trois propositions techniques et argumente : ",
]
LONG = [p + "ligne de log erreur timeout retry 42 " * 80 for p in LONG_PFX]


def build_corpus():
    texts, y = [], []
    for t in GREET + TRIVIA + MATH + THANKS + EMPTY:
        texts.append(t)
        y.append(0)
    for t in CODE + BASH + TECH + TASKS + LONG:
        texts.append(t)
        y.append(1)
    return texts, np.array(y, np.int64)


def stratified_split(y, frac=TEST_FRAC, seed=SEED):
    rng = np.random.RandomState(seed)
    tr, te = [], []
    for c in (0, 1):
        idx = np.where(y == c)[0]
        rng.shuffle(idx)
        k = int(round(len(idx) * frac))
        te.extend(idx[:k].tolist())
        tr.extend(idx[k:].tolist())
    return np.array(sorted(tr)), np.array(sorted(te))


def gate_scores(emb, policy, X):
    p = policy.predict_proba(emb.transform(X))[:, 0]
    conf = gaussian_cdf_fast(4.0 * np.abs(p - 0.5) - 1.0)
    return p, conf


def metrics_from_pred(y, pred_instant):
    y = np.asarray(y)
    pred = np.asarray(pred_instant, bool)
    instant_ok = y == 0
    tp = float(np.sum(pred & instant_ok))
    fp = float(np.sum(pred & ~instant_ok))
    fn = float(np.sum(~pred & instant_ok))
    tn = float(np.sum(~pred & ~instant_ok))
    n = max(len(y), 1)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(2 * prec * rec / (prec + rec) if prec + rec else 0.0, 4),
        "false_instant_rate": round(fp / (tp + fp) if tp + fp else 0.0, 4),
        "false_instant_fpr": round(fp / (fp + tn) if fp + tn else 0.0, 4),
        "instant_rate": round((tp + fp) / n, 4),
        "accuracy": round((tp + tn) / n, 4),
        "n_instant_pred": int(tp + fp),
        "n_false_instant": int(fp),
    }


def metrics(y, conf, thr):
    return metrics_from_pred(y, np.asarray(conf) >= thr)


def sweep(y, conf, thrs=None):
    thrs = thrs if thrs is not None else np.arange(0.4, 0.95, 0.05)
    keys = ("precision", "recall", "f1", "false_instant_rate", "instant_rate")
    return [
        {"thr": round(float(t), 2), **{k: metrics(y, conf, t)[k] for k in keys}}
        for t in thrs
    ]


def best_thresholds(rows):
    best_f1 = max(rows, key=lambda r: r["f1"])
    safe = [r for r in rows if r["false_instant_rate"] <= 0.05 and r["instant_rate"] > 0]
    best_safe = max(safe, key=lambda r: r["instant_rate"]) if safe else None
    return {
        "max_f1": {"thr": best_f1["thr"], "f1": best_f1["f1"],
                   "false_instant_rate": best_f1["false_instant_rate"],
                   "instant_rate": best_f1["instant_rate"]},
        "safe_fi05": best_safe,
    }


def calibration(y, p, conf, nb=10):
    acc = ((p >= 0.5).astype(int) == y).astype(float)
    order = np.argsort(conf)
    bins, ece = [], 0.0
    for ch in np.array_split(order, nb):
        if not len(ch):
            continue
        mc, ma = float(conf[ch].mean()), float(acc[ch].mean())
        bins.append({"lo": round(float(conf[ch].min()), 4), "hi": round(float(conf[ch].max()), 4),
                     "mean_conf": round(mc, 4), "acc": round(ma, 4), "n": int(len(ch))})
        ece += len(ch) / len(y) * abs(ma - mc)
    return {"bins": bins, "ece": round(float(ece), 4)}


def fit_lr(X, y, epochs=400, lr=0.5, seed=0):
    rng = np.random.RandomState(seed)
    w = np.zeros(X.shape[1])
    b = 0.0
    n = len(X)
    for ep in range(epochs):
        idx = rng.permutation(n)
        for i in range(0, n, 32):
            j = idx[i:i + 32]
            z = np.clip(X[j] @ w + b, -30, 30)
            d = (1.0 / (1.0 + np.exp(-z)) - y[j]) / len(j)
            w -= lr * (X[j].T @ d)
            b -= lr * float(d.sum())
    return w, b


def run() -> dict:
    texts, y = build_corpus()
    tr, te = stratified_split(y)
    X = np.array([features_from_text(t) for t in texts], np.float32)
    Xtr, Xte = X[tr], X[te]
    ytr, yte = y[tr], y[te]

    # retrained gate (imported SpearEmb/TinyPolicy, fit on train only)
    emb_r = SpearEmb.fit(Xtr, seed=SEED)
    pol_r = TinyPolicy.init(emb_r.d_out, h=32, seed=SEED)
    pol_r.fit(emb_r.transform(Xtr), ytr.astype(np.float32), epochs=150, lr=0.05, seed=0)
    p_r, conf_r = gate_scores(emb_r, pol_r, Xte)

    # original toy gate (IntuitionInstant as-is)
    toy = IntuitionInstant(seed=SEED)
    p_t, conf_t = gate_scores(toy.emb, toy.policy, Xte)

    # baselines
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
    w_lr, b_lr = fit_lr((Xtr - mu) / sd, (ytr == 0).astype(np.float64))
    conf_lr = 1.0 / (1.0 + np.exp(-np.clip(((Xte - mu) / sd) @ w_lr + b_lr, -30, 30)))
    n_words = np.array([len(t.split()) for t in (texts[i] for i in te)])

    report = {
        "meta": {
            "n": int(len(y)), "seed": SEED, "n_train": int(len(tr)), "n_holdout": int(len(te)),
            "label_mapping": "0=trivial/instant-eligible, 1=needs_tool/full (intuition.py demo y)",
            "gate_threshold": THR, "split": f"stratified {int((1-TEST_FRAC)*100)}/{int(TEST_FRAC*100)}",
            "crit_cost": "false_instant_rate = P(label=full | pred=instant)",
        },
        "gate_retrained": {"thr": THR, **metrics(yte, conf_r, THR)},
        "gate_toy": {"thr": THR, **metrics(yte, conf_t, THR)},
        "baselines": {
            "always_full": metrics_from_pred(yte, np.zeros(len(te), bool)),
            "always_instant": metrics_from_pred(yte, np.ones(len(te), bool)),
            "len_lt_12_words": metrics_from_pred(yte, n_words < 12),
            "logistic_regression": {"thr": 0.5, **metrics_from_pred(yte, conf_lr >= 0.5)},
        },
        "threshold_sweep": {"retrained": sweep(yte, conf_r), "toy": sweep(yte, conf_t)},
        "calibration": {"retrained": calibration(yte, p_r, conf_r),
                        "toy": calibration(yte, p_t, conf_t),
                        "logistic_regression": calibration(yte, conf_lr, conf_lr)},
        "best_thresholds": {
            "retrained": best_thresholds(sweep(yte, conf_r)),
            "toy": best_thresholds(sweep(yte, conf_t)),
        },
    }
    return report


def self_check(rep: dict, y, tr, te) -> None:
    assert len(y) >= 200, f"corpus too small: {len(y)}"
    assert set(tr).isdisjoint(te), "split leak: train/holdout overlap"
    assert len(tr) + len(te) == len(y), "split incomplete"
    assert set(y[tr].tolist()) == {0, 1} and set(y[te].tolist()) == {0, 1}, "missing class in split"
    req = ("precision", "recall", "f1", "false_instant_rate", "instant_rate")
    for section in ("gate_retrained", "gate_toy"):
        for k in req:
            assert k in rep[section], f"{section} missing {k}"
            assert 0.0 <= rep[section][k] <= 1.0, f"{section}.{k} out of range"
    for name, m in rep["baselines"].items():
        for k in req:
            assert k in m, f"baseline {name} missing {k}"
    assert len(rep["threshold_sweep"]["retrained"]) >= 10, "sweep too short"
    for side in ("retrained", "toy", "logistic_regression"):
        assert rep["calibration"][side]["ece"] >= 0.0, "bad ECE"
        assert len(rep["calibration"][side]["bins"]) >= 5, "too few calib bins"
    for side in ("retrained", "toy"):
        assert "max_f1" in rep["best_thresholds"][side], "missing best threshold"


def print_table(rep: dict) -> None:
    rows = [("gate_retrained@0.65", rep["gate_retrained"]),
            ("gate_toy@0.65", rep["gate_toy"])]
    rows += [(f"{k}", v) for k, v in rep["baselines"].items()]
    print(f"{'model':24} {'prec':>6} {'rec':>6} {'F1':>6} {'falseInst':>10} {'inst_rate':>9}")
    for name, m in rows:
        print(f"{name:24} {m['precision']:6.3f} {m['recall']:6.3f} {m['f1']:6.3f} "
              f"{m['false_instant_rate']:10.3f} {m['instant_rate']:9.3f}")
    for side in ("retrained", "toy"):
        bt = rep["best_thresholds"][side]
        print(f"best {side}: max_f1 thr={bt['max_f1']['thr']} f1={bt['max_f1']['f1']} "
              f"fi={bt['max_f1']['false_instant_rate']} | safe thr="
              f"{bt['safe_fi05']['thr'] if bt['safe_fi05'] else '-'} "
              f"inst={bt['safe_fi05']['instant_rate'] if bt['safe_fi05'] else '-'} | "
              f"ECE={rep['calibration'][side]['ece']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-check", action="store_true")
    args = ap.parse_args()

    rep = run()
    texts, y = build_corpus()
    tr, te = stratified_split(y)
    self_check(rep, y, tr, te)

    with open("eval_report.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    print_table(rep)
    print(f"n={rep['meta']['n']} train={rep['meta']['n_train']} holdout={rep['meta']['n_holdout']} "
          f"-> eval_report.json")
    if args.self_check:
        print("SELF-CHECK OK")


if __name__ == "__main__":
    main()
