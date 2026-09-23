"""One-shot: run all benches + tests, then refresh REPORT.md. python run_all.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CMDS = [
    ["python", "typecheck.py"],
    ["python", "intuition.py"],
    ["python", "eval_harness.py", "--self-check"],
    ["python", "multi_conf.py"],
    ["python", "e2e_bench.py"],
    ["python", "test_slow_path.py"],
    ["python", "test_intuition.py"],
    ["python", "test_reports.py"],
    ["python", "test_properties.py"],
    ["python", "test_discover.py"],
    ["node", "wasm_bench.js"],
    ["node", "wasm_batch_bench.js"],
    ["node", "test_showcase.js"],
    ["python", "cov.py"],
    ["python", "gen_showcase.py"],
    ["python", "changelog.py"],
    ["python", "export_csv.py"],
    ["python", "demo_agent.py"],
    ["python", "make_report.py"],
    ["python", "readme_sync.py"],
    ["python", "jev_bench.py"],
]

fails = 0
for cmd in CMDS:
    r = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, timeout=600)
    out = ((r.stdout or "") + "\n" + (r.stderr or "")).strip().splitlines()
    tail = out[-1] if out else ""
    ok = r.returncode == 0
    fails += 0 if ok else 1
    print(f"{'OK ' if ok else 'FAIL'} {' '.join(cmd[1:])} | {tail[:100]}")
print(f"\n{len(CMDS)-fails}/{len(CMDS)} etapes OK")
sys.exit(1 if fails else 0)
