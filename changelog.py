"""CHANGELOG.md depuis REPORT.json (snapshots + tags). python changelog.py"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    rep = json.loads((HERE / "REPORT.json").read_text(encoding="utf-8"))
    lines = ["# CHANGELOG", ""]
    snaps = rep.get("snapshots") or []
    for s in reversed(snaps[-8:]):
        d = s.get("delta", "") or ""
        lines.append(f"- {s.get('ts', '')} | {s.get('status', '')} | "
                     f"tests {s.get('tests_ok', '')}/{s.get('tests_total', '')} | {d}")
    try:
        rel = json.loads(__import__("subprocess").run(
            ["gh", "release", "list", "--repo", "bahira/frankenspear"],
            capture_output=True, text=True).stdout or "[]")
        for r in rel[:5]:
            lines.append(f"- {r.get('publishedAt', '')} | release {r.get('tagName', '')}")
    except Exception:
        pass
    (HERE / "CHANGELOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"CHANGELOG.md ({len(lines) - 2} lignes)")


if __name__ == "__main__":
    main()
