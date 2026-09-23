import subprocess, time
CMDS = [
    ['python','test_discover.py'],
    ['python','e2e_bench.py'],
    ['node','wasm_bench.js'],
    ['node','wasm_batch_bench.js'],
    ['node','test_showcase.js'],
    ['python','make_report.py','--quiet'],
]
t0 = time.perf_counter_ns()
for c in CMDS:
    t1 = time.perf_counter_ns()
    r = subprocess.run(c, capture_output=True, text=True, timeout=300, cwd=".")
    ms = (time.perf_counter_ns() - t1) // 1000
    print(c[-1][:20], "rc", r.returncode, ms, "ms")
print("total", (time.perf_counter_ns() - t0) // 1000, "ms")
