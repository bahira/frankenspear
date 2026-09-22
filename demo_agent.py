from __future__ import annotations
import time
from intuition import IntuitionInstant

def main() -> None:
    layer = IntuitionInstant(seed=42)
    prompts = [
        "salut qui es-tu aide",
        "ecris une fonction gelu fibonacci code",
        "quantum chsh grover concurrence kernel",
    ]
    for p in prompts:
        t0 = time.perf_counter_ns()
        r = layer.route(p)
        us = (time.perf_counter_ns() - t0) / 1000
        print(f"{r['path']:7s} p={r['p']:.3f} conf={r['conf']:.3f} cx={r['complexity']:.3f} {us:.1f}us  {p}")
    print(f"stats instant={layer.stats['instant']} slow={layer.stats['slow']}")

if __name__ == "__main__":
    main()
