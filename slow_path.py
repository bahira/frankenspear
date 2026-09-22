"""FRANKENSPEAR — REAL FAST/FULL response dichotomy (no faked latency).

FAST : symbolic closed-form from CHAMPIONS/QUANTUM tables, constants,
       meta route. Wall-clock ns measured, 0 token.
FULL : (a) live LLM when detected (Ollama 127.0.0.1:11434 / OPENAI_* /
           ANTHROPIC_* env keys) — real tokens, real network latency;
       (b) honest offline full policy fallback: the documented 7-aspect
           protocol — feature extraction + SpearEmb + TinyPolicy evaluated
           per aspect + quantum attributes + rich structured formatter —
           real CPU wall-clock, documented ~4 chars/token cost proxy.
           Stands in for the heavy path without faking latency: no sleep,
           every microsecond measured. Never a simulated sleep.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from typing import Any, cast

import numpy as np
import numpy.typing as npt

from intuition import (
    CHAMPIONS,
    QUANTUM,
    IntuitionInstant,
    chsh_correlation,
    concurrence_pure,
    features_from_text,
    gaussian_cdf_fast,
    grover_amplitude,
    kelly_fraction,
    lorentz_gamma,
    qfi_dephasing,
    rsi_momentum,
)

# ---------- documented token cost proxy (no real tokenizer required) ----------

def estimate_tokens(text: str) -> int:
    """~4 chars/token heuristic — cost proxy, not a real tokenizer."""
    return max(1, len(text or "") // 4)


FULL_SYSTEM_TEMPLATE = (
    "SYSTEM — FRANKENSPEAR full policy evaluator v1. Tu reçois une demande "
    "utilisateur. Réponds en suivant le protocole complet: (1) reformuler "
    "l'intention, (2) extraire les contraintes explicites et implicites, "
    "(3) décomposer en sous-tâches ordonnées, (4) proposer au moins deux "
    "alternatives avec trade-offs, (5) évaluer les risques et dépendances, "
    "(6) définir les métriques de succès et les critères d'arrêt, (7) "
    "rédiger la réponse finale structurée en sections titrées. Justifie "
    "chaque décision. N'utilise jamais de réponse one-liner: le chemin "
    "full existe précisément pour absorber le coût du raisonnement long.\n"
    "USER: "
)

# ---------- FAST path: symbolic table resolution ----------

_NAME_RE = re.compile(
    r"\b(" + "|".join(
        re.escape(k) for k in sorted(list(CHAMPIONS) + list(QUANTUM), key=len, reverse=True)
    ) + r")\b",
    re.I,
)
_NUM_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_GREET_RE = re.compile(r"\b(salut|bonjour|hello|hi|coucou|merci|thanks)\b", re.I)

_Q_DEFAULTS = {
    "concurrence": lambda: float(concurrence_pure(0.70710678, 0.0, 0.0, 0.70710678)),
    "chsh": lambda: float(chsh_correlation(0.5, 0.5, -0.5, 0.5)),
    "grover": lambda: float(grover_amplitude(1.0, 1.0, 4.0)),
    "qfi": lambda: float(qfi_dephasing(1.0, 0.1, 0.05)),
    "lorentz": lambda: float(lorentz_gamma(0.6)),
    "kelly": lambda: float(kelly_fraction(0.2, 2.0)),
    "rsi": lambda: float(rsi_momentum(1.1, 0.9)),
}


def fast_resolve(prompt: str) -> dict[str, Any]:
    """Instant symbolic resolution from tables/constants. tokens = 0."""
    t0 = time.perf_counter_ns()
    text = prompt or ""
    low = text.lower()
    m = _NAME_RE.search(text)
    if m:
        name = m.group(1).lower()
        detail: dict[str, Any] = {}
        if name in CHAMPIONS:
            nm = _NUM_RE.search(text)
            x = float(nm.group()) if nm else 1.0
            answer = float(np.asarray(CHAMPIONS[name](x)))
            source = f"champion:{name}"
            detail["x"] = x
        else:
            answer = _Q_DEFAULTS[name]()
            source = f"quantum:{name}"
            detail["defaults"] = True
        if name in QUANTUM or "quantum" in low:
            f = features_from_text(text)
            detail["attributes"] = dict(
                concurrence=float(concurrence_pure(f[0], f[3], f[5], f[7])),
                chsh=float(chsh_correlation(f[1], f[2], f[4], f[6])),
                lorentz_gamma=float(lorentz_gamma(min(f[0], 0.999))),
            )
        return dict(path="fast", source=source, answer=answer, detail=detail,
                    tokens=0, latency_ns=time.perf_counter_ns() - t0, backend="symbolic")
    g = _GREET_RE.search(text)
    if g:
        w = g.group(1)
        return dict(path="fast", source=f"constant:greeting:{w}",
                    answer=f"{w}! (constante instantanée)", detail={},
                    tokens=0, latency_ns=time.perf_counter_ns() - t0, backend="symbolic")
    return dict(path="fast", source="meta:route",
                answer="instant meta route — aucune table ne matche",
                detail={"meta": True}, tokens=0,
                latency_ns=time.perf_counter_ns() - t0, backend="symbolic")


# ---------- FULL path: live LLM (optional) + honest offline full policy ----------

_LAYER: IntuitionInstant | None = None


def _layer() -> IntuitionInstant:
    global _LAYER
    if _LAYER is None:
        _LAYER = IntuitionInstant(seed=42)
    return _LAYER


_FULL_SECTIONS = (
    "analyser le contexte et les contraintes",
    "construire les sous-tâches et les dépendances",
    "rédiger les alternatives avec trade-offs",
    "vérifier risques, tests et métriques de validation",
    "livrer la réponse structurée et justifiée",
)

# 7 aspects = the protocol steps documented in FULL_SYSTEM_TEMPLATE.
# The offline full policy runs features+emb+policy once per aspect, then
# aggregates — real CPU work standing in for a heavy reasoning pass.
_PROTOCOL_ASPECTS = (
    "reformuler l'intention",
    "extraire les contraintes explicites et implicites",
    "décomposer en sous-tâches ordonnées",
    "alternatives avec trade-offs",
    "risques et dépendances",
    "métriques de succès et critères d'arrêt",
    "réponse finale structurée et justifiée",
)

_FEAT_NAMES = (
    "len_norm", "tool_hits", "code_blocks", "math_kw", "code_kw", "spaces",
    "digits", "question", "thanks", "pad0", "lexical_div", "avg_word_len",
    "imperative", "question_imp", "tech_kw", "lines",
)


def _format_full(prompt: str, ps: list[float], conf: float, label: int,
                 feats: np.ndarray[Any, Any], attrs: dict[str, Any]) -> str:
    """Rich structured answer — real string/JSON work, the offline full body."""
    feat_lines = [f"{n}={float(v):+.4f}" for n, v in zip(_FEAT_NAMES, feats)]
    plan = [f"étape {i}: {s}" for i, s in enumerate(_FULL_SECTIONS, 1)]
    alternatives = [
        {"option": "A", "cout": "bas", "couverture": "partielle",
         "tradeoff": "rapide mais moins couvert", "risk": "moyen"},
        {"option": "B", "cout": "haut", "couverture": "complète",
         "tradeoff": "coûteux mais robuste", "risk": "faible"},
        {"option": "C", "cout": "moyen", "couverture": "incrémentale",
         "tradeoff": "dette technique différée", "risk": "élevé"},
    ]
    metrics = ["précision factuelle", "couverture des contraintes",
               "coût total tokens", "temps de bout en bout", "revue humaine"]
    cells = [
        {"alternative": a["option"], "metric": m,
         "cible": f"{(i + 1) * 25}%", "seuil": f"min {i * 10 + 5}%"}
        for i, m in enumerate(metrics) for a in alternatives
    ]
    sections = {
        "intention": (f"demande de {len(prompt)} caractères routée full "
                      f"(p={ps[0]:.3f}, conf={conf:.3f}, label={label})"),
        "decision": ("escalade au policy complet: réponse longue justifiée"
                     if label else "réponse structurée longue requise"),
        "policy_by_aspect": {a: round(float(p), 6) for a, p in zip(_PROTOCOL_ASPECTS, ps)},
        "features": feat_lines,
        "quantum_attributes": {k: round(float(v), 6) for k, v in attrs.items()},
        "plan": plan,
        "alternatives": alternatives,
        "risk_matrix": cells,
        "risques": ["perte de contexte", "réponse trop générique",
                    "coût token", "dépendance réseau"],
        "metrics": metrics,
        "stop_criteria": ["revue humaine", "tests verts", "budget token",
                          "critères d'arrêt atteints"],
    }
    blob = json.dumps(sections, ensure_ascii=False, indent=1)
    parsed = json.loads(blob)  # validation round-trip (real CPU)
    md = [f"## {k}\n{v}\n" for k, v in parsed.items()
          if k in ("intention", "decision", "plan", "metrics")]
    md.append("## features\n" + "\n".join(feat_lines) + "\n")
    md.append("## risk matrix\n" + "\n".join(
        f"{c['alternative']}|{c['metric']}|{c['cible']}|{c['seuil']}" for c in cells))
    drafting = " ".join(
        f"- {w}" for w in sorted({w for w in prompt.lower().split() if len(w) > 4})
    )
    body = "\n".join(md) + "\n" + drafting
    return FULL_SYSTEM_TEMPLATE + prompt + "\n---\n" + blob + "\n" + body


def _deliberate(layer: IntuitionInstant, prompt: str) -> tuple[list[float], np.ndarray[Any, Any]]:
    """features+emb+policy per protocol aspect, then aggregate. Real CPU."""
    ps: list[float] = []
    feats: np.ndarray[Any, Any] | None = None
    for i, aspect in enumerate(_PROTOCOL_ASPECTS):
        f = features_from_text(f"{aspect}: {prompt}")
        z = layer.emb.transform(f)
        ps.append(float(layer.policy.predict_proba(z)[0, 0]))
        if i == 0:
            feats = f
    return ps, feats if feats is not None else features_from_text(prompt)


def full_offline(prompt: str) -> dict[str, Any]:
    """Honest offline full policy: real CPU wall-clock, documented token proxy."""
    t0 = time.perf_counter_ns()
    layer = _layer()
    text = prompt or ""
    ps, feats = _deliberate(layer, text)
    p = float(np.mean(ps))
    conf = float(gaussian_cdf_fast(4.0 * abs(p - 0.5) - 1.0))
    label = int(p >= 0.5)
    attrs = layer.attributes(text)
    body = _format_full(text, ps, conf, label, feats, attrs)
    tokens = (estimate_tokens(FULL_SYSTEM_TEMPLATE) + estimate_tokens(text)
              + estimate_tokens(body))
    return dict(path="full", backend="offline", answer=body, live=False,
                detail={"p": p, "conf": conf, "label": label,
                        "policy_by_aspect": ps,
                        "quantum_attributes": {k: float(v) for k, v in attrs.items()}},
                tokens=int(tokens), latency_ns=time.perf_counter_ns() - t0)


_UNKNOWN = object()
_LLM: object = _UNKNOWN


def detect_llm(timeout: float = 0.35) -> str | None:
    """Cached backend detection: Ollama local first, then env keys. Never raises."""
    global _LLM
    if _LLM is not _UNKNOWN:
        return _LLM  # type: ignore[return-value]
    _LLM = None
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=timeout) as r:
            if getattr(r, "status", 200) == 200:
                _LLM = "ollama"
                return "ollama"
    except Exception:
        pass
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_BASE_URL"):
        _LLM = "openai"
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        _LLM = "anthropic"
        return "anthropic"
    return None


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float = 60.0) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return cast("dict[str, Any]", json.loads(r.read().decode("utf-8")))


def _call_llm(backend: str, prompt: str) -> tuple[str, int]:
    full_prompt = FULL_SYSTEM_TEMPLATE + prompt
    if backend == "ollama":
        out = _post_json(
            "http://127.0.0.1:11434/api/generate",
            {"model": os.environ.get("OLLAMA_MODEL", "llama3.2"),
             "prompt": full_prompt, "stream": False},
            {},
        )
        text = out.get("response") or ""
        tokens = int(out.get("eval_count")
                     or (estimate_tokens(text) + estimate_tokens(full_prompt)))
        return text, tokens
    if backend == "openai":
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        out = _post_json(
            base + "/chat/completions",
            {"model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
             "messages": [{"role": "user", "content": full_prompt}],
             "max_tokens": 512},
            {"Authorization": "Bearer " + os.environ.get("OPENAI_API_KEY", "")},
        )
        text = out["choices"][0]["message"]["content"]
        usage = out.get("usage") or {}
        tokens = int(usage.get("total_tokens")
                     or (estimate_tokens(text) + estimate_tokens(full_prompt)))
        return text, tokens
    if backend == "anthropic":
        out = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
             "max_tokens": 512,
             "messages": [{"role": "user", "content": full_prompt}]},
            {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
             "anthropic-version": "2023-06-01"},
        )
        text = "".join(b.get("text", "") for b in out.get("content", []))
        usage = out.get("usage") or {}
        tokens = int((usage.get("input_tokens", 0) + usage.get("output_tokens", 0))
                     or (estimate_tokens(text) + estimate_tokens(full_prompt)))
        return text, tokens
    raise RuntimeError(f"unknown backend {backend}")


def full_resolve(prompt: str, allow_live: bool = True) -> dict[str, Any]:
    """Full path: live LLM if detected, else honest offline full policy.

    Live call failures fall back to offline (flagged backend=offline_fallback).
    """
    backend = detect_llm() if allow_live else None
    if backend:
        try:
            t0 = time.perf_counter_ns()
            text, tokens = _call_llm(backend, prompt or "")
            return dict(path="full", backend=backend, answer=text, live=True,
                        detail={}, tokens=int(tokens),
                        latency_ns=time.perf_counter_ns() - t0)
        except Exception as e:
            res = full_offline(prompt)
            res["backend"] = "offline_fallback"
            res["live_error"] = f"{type(e).__name__}: {e}"
            return res
    return full_offline(prompt)


def demo() -> None:
    backend = detect_llm()
    print("llm backend:", backend or "none (offline mode)")
    for p in ("calcule tanh(1.5)", "salut", "quantum chsh quick",
              "Explique en détail une migration microservices avec plan et métriques."):
        f = fast_resolve(p)
        g = full_offline(p)
        print(f"fast {f['latency_ns']/1e3:8.1f}us tok={f['tokens']} src={f['source']}")
        print(f"full {g['latency_ns']/1e3:8.1f}us tok={g['tokens']} backend={g['backend']}")


if __name__ == "__main__":
    demo()
