import subprocess, time
t0 = time.perf_counter_ns()
CMDS = [
    ["python","typecheck.py"],["python","intuition.py"],["python","eval_harness.py","--self-check"],
    ["python","multi_conf.py"],["python","e2e_bench.py"],["python","test_slow_path.py"],
    ["python","test_intuition.py"],["python","test_reports.py"],["python","test_properties.py"],
    ["python","test_discover.py"],["node","wasm_bench.js"],["node","wasm_batch_bench.js"],
    ["node","test_showcase.js"],["python","cov.py"],["python","gen_showcase.py"],
    ["python","changelog.py"],["python","export_csv.py"],["python","demo_agent.py"],
    ["python","make_report.py"],["python","readme_sync.py"],["python","jev_bench.py"],
]
fails = 0
for i, c in enumerate(CMDS, 1):
    t1 = time.perf_counter_ns()
    r = subprocess.run(c, capture_output=True, text=True, timeout=240, cwd=".")
    ok = 1 if r.returncode == 0 else 0
    fails += 1 - ok
    ms = (time.perf_counter_ns() - t1) // 1000
    print(str(i) + "." + (" OK" if ok else "FAIL") + " " + str(ms) + "ms " + str(c[-1])[:35])
    if not ok and r.stdout:
        print("   stdout:", r.stdout[-150:])
    if not ok and r.stderr:
        print("   stderr:", r.stderr[-150:])
print(str(len(CMDS) - fails) + "/" + str(len(CMDS)) + " OK, total " + str((time.perf_counter_ns()-t0)//1000000) + "s")
