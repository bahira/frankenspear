"""Tests for slow_path / e2e_bench. Run: python test_slow_path.py (or pytest)."""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from slow_path import detect_llm, estimate_tokens, fast_resolve, full_offline, full_resolve

HERE = Path(__file__).resolve().parent


def test_paths_exist():
    f = fast_resolve("calcule tanh(1.5)")
    assert f["path"] == "fast" and f["tokens"] == 0 and f["latency_ns"] > 0
    assert isinstance(f["answer"], float) and f["source"] == "champion:tanh"

    q = fast_resolve("quantum chsh quick")
    assert q["path"] == "fast" and q["tokens"] == 0 and "attributes" in q["detail"]

    h = fast_resolve("salut")
    assert h["path"] == "fast" and h["tokens"] == 0

    m = fast_resolve("un texte sans kernel ni salutation ici")
    assert m["path"] == "fast" and m["tokens"] == 0 and m["source"] == "meta:route"

    g = full_offline("Explique en détail une migration complète avec plan, "
                     "risques et métriques de succès.")
    assert g["path"] == "full" and g["tokens"] > 0 and g["backend"] == "offline"
    assert g["latency_ns"] > 0 and len(g["answer"]) > 100 and g["live"] is False

    b = full_resolve("n'importe quoi", allow_live=False)
    assert b["path"] == "full" and b["live"] is False and b["tokens"] > 0

    assert detect_llm() in (None, "ollama", "openai", "anthropic")
    assert estimate_tokens("abcd") == 1 and estimate_tokens("a" * 40) == 10


def test_p50_full_gt_fast():
    prompts = [
        "calcule tanh(1.5)", "quantum chsh quick", "salut", "gelu(2.0)",
        "Explique en détail une migration monolith vers microservices avec plan.",
        "Écris un script Python complet avec tests et documentation.",
    ]
    for p in prompts:  # warmup (layer init, caches)
        fast_resolve(p)
        full_offline(p)
    n = 200
    fast_ns: list[int] = []
    full_ns: list[int] = []
    for i in range(n):
        p = prompts[i % len(prompts)]
        t0 = time.perf_counter_ns()
        fast_resolve(p)
        fast_ns.append(time.perf_counter_ns() - t0)
        t0 = time.perf_counter_ns()
        full_offline(p)
        full_ns.append(time.perf_counter_ns() - t0)
    p50_fast = float(np.percentile(fast_ns, 50))
    p50_full = float(np.percentile(full_ns, 50))
    assert p50_full > p50_fast, f"p50 full {p50_full:.0f}ns <= p50 fast {p50_fast:.0f}ns"


def test_report_written():
    import e2e_bench

    out = HERE / "e2e_report.json"
    if out.exists():
        out.unlink()
    report = e2e_bench.run(allow_live=False, out_path=out)
    assert out.exists(), "e2e_report.json non écrit"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["n_prompts"] >= 100
    assert set(data["scenarios"]) == {"always_full", "always_fast", "gated", "gated_lr"}
    assert data["offline"] is True and data["llm_backend"] is None
    for s in data["scenarios"].values():
        assert s["p50_us"] > 0 and s["p99_us"] >= s["p50_us"] and s["n"] >= 100
    assert data["scenarios"]["always_fast"]["token_cost_proxy"] == 0
    assert data["scenarios"]["always_full"]["token_cost_proxy"] > 0
    assert data["paths"]["fast"]["mean_us"] * 3 <= data["paths"]["full"]["mean_us"]
    assert data["scenarios"]["gated"]["mean_us"] <= data["scenarios"]["always_full"]["mean_us"] * 1.02
    assert data["sanity"]["ok"] is True, data["sanity"]["checks"]
    assert report["verdict"]["gate_saves_tokens"] is True


def main() -> None:
    tests = (test_paths_exist, test_p50_full_gt_fast, test_report_written)
    for t in tests:
        t()
        print(f"OK {t.__name__}")
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
