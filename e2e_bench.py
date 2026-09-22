"""E2E benchmark — always_full vs always_fast (bad) vs gated (IntuitionInstant).

Real wall-clock p50/p99 per scenario, full-call rate, token cost proxy
(full = estimated tokens, fast = 0), false-instant rate vs dataset labels.
Writes e2e_report.json. Offline-safe: Ollama/API absence -> offline flag.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from intuition import CHAMPIONS, QUANTUM, IntuitionInstant
from slow_path import detect_llm, fast_resolve, full_offline, full_resolve

HERE = Path(__file__).resolve().parent

TOPICS = (
    "une migration de monolith vers microservices",
    "un refactor du service d'authentification",
    "un pipeline d'entraînement ML en production",
    "une stratégie de contenu pour un SaaS B2B",
    "un audit de sécurité applicative",
    "le design d'une API publique versionnée",
    "l'optimisation d'une base PostgreSQL chargée",
    "un plan de recrutement d'une équipe engineering",
    "la refonte du système de facturation",
    "la mise en place d'un data warehouse",
    "un dispositif de monitoring multi-région",
    "une politique de gestion des dépendances",
    "un plan de sortie de crise post-incident",
    "l'automatisation du release train",
    "une architecture événementielle fiable",
)


def build_dataset() -> list[dict]:
    """Mix of instant-eligible (closed-form answer exists) and full-only prompts."""
    rows: list[dict] = []

    def add(text: str, ok: bool) -> None:
        rows.append({"prompt": text, "instant_ok": bool(ok)})

    for k in sorted(CHAMPIONS):
        for x in ("1.5", "0.25", "2.0"):
            add(f"calcule {k}({x})", True)
    for q in sorted(QUANTUM):
        add(f"quantum {q} quick", True)
    for g in ("salut", "bonjour", "hello", "merci", "thanks", "coucou",
              "salut aide", "bonjour merci", "ok merci", "hi there"):
        add(g, True)
    for k in sorted(CHAMPIONS)[:6]:
        add(f"quoi {k} et pourquoi", True)
    # 36 + 7 + 10 + 6 = 59 instant-eligible
    for t in TOPICS:
        add(f"Explique en détail {t} et propose un plan complet avec étapes, "
            f"risques, budget et métriques de succès.", False)
    for t in TOPICS:
        add(f"Écris un script Python complet pour gérer {t}, avec tests, logging, "
            f"gestion d'erreurs et docstring.", False)
    for t in TOPICS[:10]:
        add(f"Analyse comparative et recommandation détaillée sur {t}: options, "
            f"coûts, planning sur 6 mois.", False)
    for t in TOPICS[:10]:
        add(f"Rédige un cahier des charges complet pour {t}, avec exigences "
            f"fonctionnelles et recette.", False)
    # 50 full-only -> 109 total
    assert len(rows) >= 100
    return rows


def _stats(samples_ns: list[int]) -> dict:
    a = np.asarray(samples_ns, dtype=float) / 1e3  # -> us
    return dict(
        p50_us=round(float(np.percentile(a, 50)), 2),
        p99_us=round(float(np.percentile(a, 99)), 2),
        mean_us=round(float(a.mean()), 2),
    )


def _run_scenario(name: str, rows: list[dict], layer: IntuitionInstant,
                  allow_live: bool) -> dict:
    lat: list[int] = []
    full_calls = 0
    tokens = 0
    n_not_ok = 0
    false_inst = 0
    n_ok = 0
    ok_full = 0
    for row in rows:
        p = row["prompt"]
        t0 = time.perf_counter_ns()
        if name == "always_full":
            res = full_resolve(p, allow_live=allow_live)
            went_full = True
        elif name == "always_fast":
            res = fast_resolve(p)
            went_full = False
        else:  # gated: intuition gate cost included in latency
            r = layer.route(p)
            if r["path"] == "instant":
                res = fast_resolve(p)
                went_full = False
            else:
                res = full_resolve(p, allow_live=allow_live)
                went_full = True
        lat.append(time.perf_counter_ns() - t0)
        if went_full:
            full_calls += 1
        tokens += int(res.get("tokens", 0))
        if row["instant_ok"]:
            n_ok += 1
            if went_full:
                ok_full += 1
        else:
            n_not_ok += 1
            if not went_full:
                false_inst += 1
    out = {
        "n": len(rows),
        "full_rate": round(full_calls / len(rows), 4),
        "token_cost_proxy": tokens,
        "false_instant_rate": round(false_inst / max(n_not_ok, 1), 4),
        "instant_miss_rate": round(ok_full / max(n_ok, 1), 4),
    }
    out.update(_stats(lat))
    return out


def _bench_paths(rows: list[dict], n: int = 250) -> dict:
    """Pure path CPU comparison (offline full — measures path mechanics)."""
    fast_samples: list[int] = []
    full_samples: list[int] = []
    fast_resolve("warmup tanh(1)")
    full_offline("warmup full offline path")
    for i in range(n):
        p = rows[i % len(rows)]["prompt"]
        t0 = time.perf_counter_ns()
        fast_resolve(p)
        fast_samples.append(time.perf_counter_ns() - t0)
        t0 = time.perf_counter_ns()
        full_offline(p)
        full_samples.append(time.perf_counter_ns() - t0)
    fast_s = _stats(fast_samples)
    full_s = _stats(full_samples)
    return {"fast": fast_s, "full": full_s, "n": n}


def run(out_path: Path | str | None = None, allow_live: bool = True,
        rows: list[dict] | None = None, n_path: int = 250) -> dict:
    import gc

    rows = rows or build_dataset()
    layer = IntuitionInstant(seed=42, gate="conf")
    layer_lr = IntuitionInstant(seed=42, gate="lr")
    # warmup: gate, layer init, LLM detection, path caches
    fast_resolve("warmup tanh(1.5)")
    full_resolve("warmup full path", allow_live=allow_live)
    full_offline("warmup offline full")
    layer.route("warmup route gate")
    layer_lr.route("warmup route gate lr")
    backend = detect_llm() if allow_live else None

    scenarios = {}
    for name in ("always_full", "always_fast", "gated", "gated_lr"):
        gc.collect()
        lyr = layer_lr if name == "gated_lr" else layer
        scenarios[name] = _run_scenario(name, rows, lyr, allow_live)
    gc.collect()
    paths = _bench_paths(rows, n=n_path)

    f, g, ff = scenarios["always_full"], scenarios["gated"], scenarios["always_fast"]
    gl = scenarios["gated_lr"]
    lat_saving = 1.0 - g["mean_us"] / max(f["mean_us"], 1e-9)
    tok_saving = 1.0 - g["token_cost_proxy"] / max(f["token_cost_proxy"], 1)

    checks = [
        {"name": "dataset_size_ge_100", "ok": len(rows) >= 100},
        {"name": "fast_mean_x3_lt_full_mean", "ok": paths["fast"]["mean_us"] * 3 <= paths["full"]["mean_us"]},
        {"name": "gated_mean_le_always_full_mean", "ok": g["mean_us"] <= f["mean_us"] * 1.02},
        {"name": "gated_p50_le_always_full_p50", "ok": g["p50_us"] <= f["p50_us"] * 1.02},
        {"name": "always_fast_zero_tokens", "ok": ff["token_cost_proxy"] == 0},
        {"name": "always_full_positive_tokens", "ok": f["token_cost_proxy"] > 0},
    ]
    best_fi = min(g["false_instant_rate"], gl["false_instant_rate"])
    verdict = {
        "gate_saves_latency": g["mean_us"] <= f["mean_us"],
        "gate_saves_tokens": g["token_cost_proxy"] < f["token_cost_proxy"],
        "latency_savings_pct": round(100 * lat_saving, 1),
        "token_savings_pct": round(100 * tok_saving, 1),
        "false_instant_rate_gated": g["false_instant_rate"],
        "false_instant_rate_gated_lr": gl["false_instant_rate"],
        "false_instant_rate_always_fast": ff["false_instant_rate"],
        "quality_ok": best_fi <= 0.25,
    }
    verdict["summary"] = (
        f"gate: {verdict['latency_savings_pct']}% latency / "
        f"{verdict['token_savings_pct']}% tokens vs always_full; "
        f"false-instant conf={verdict['false_instant_rate_gated']} "
        f"lr={verdict['false_instant_rate_gated_lr']} "
        f"vs always_fast={verdict['false_instant_rate_always_fast']}"
        + ("" if verdict["quality_ok"] else " | QUALITY FAIL: faux-instant trop eleves")
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_prompts": len(rows),
        "n_instant_ok": sum(1 for r in rows if r["instant_ok"]),
        "n_full_only": sum(1 for r in rows if not r["instant_ok"]),
        "llm_backend": backend,
        "offline": backend is None,
        "scenarios": scenarios,
        "paths": paths,
        "sanity": {"ok": all(c["ok"] for c in checks), "checks": checks},
        "verdict": verdict,
    }
    out = Path(out_path) if out_path else HERE / "e2e_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    report["report_path"] = str(out)
    return report


def print_table(report: dict) -> None:
    hdr = f"{'scenario':<13}{'p50_us':>10}{'p99_us':>10}{'mean_us':>10}{'full_rate':>10}{'tokens':>10}{'false_inst':>12}{'inst_miss':>10}"
    print(hdr)
    print("-" * len(hdr))
    for name, s in report["scenarios"].items():
        print(f"{name:<13}{s['p50_us']:>10.1f}{s['p99_us']:>10.1f}{s['mean_us']:>10.1f}"
              f"{s['full_rate']:>10.2f}{s['token_cost_proxy']:>10d}"
              f"{s['false_instant_rate']:>12.2f}{s['instant_miss_rate']:>10.2f}")
    p = report["paths"]
    print(f"\npaths (CPU, offline full, n={p['n']}): "
          f"fast mean={p['fast']['mean_us']:.1f}us p50={p['fast']['p50_us']:.1f}us | "
          f"full mean={p['full']['mean_us']:.1f}us p50={p['full']['p50_us']:.1f}us")
    print(f"backend: {report['llm_backend'] or 'none'}  offline={report['offline']}")
    print("sanity:", "PASS" if report["sanity"]["ok"] else "FAIL")
    for c in report["sanity"]["checks"]:
        print(f"  [{'ok' if c['ok'] else 'FAIL'}] {c['name']}")
    print("verdict:", report["verdict"]["summary"])
    print("report:", report.get("report_path"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="FRANKENSPEAR e2e gate benchmark")
    ap.add_argument("--offline", action="store_true",
                    help="force offline full path (ignore detected LLM)")
    ap.add_argument("--out", default=str(HERE / "e2e_report.json"))
    args = ap.parse_args(argv)
    report = run(out_path=args.out, allow_live=not args.offline)
    print_table(report)
    return 0 if report["sanity"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
