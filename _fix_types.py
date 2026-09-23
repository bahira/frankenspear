import re

def annotate(fp):
    src = open(fp, encoding="utf-8").read()
    lines = src.splitlines()
    # Ensure `from typing import Any` after first import block
    has_any_import = "from typing import Any" in src
    out = []
    for i, ln in enumerate(lines):
        m = re.match(r"^(\s*)def (\w+)\(([^)]*)\)( -> .+?:|:)$", ln)
        if m and ":" not in m.group(3) and m.group(3):
            indent, name, params, ret = m.group(1), m.group(2), m.group(3), m.group(4)
            ret_s = ret.lstrip(" ")
            ps = [p.strip() for p in params.split(",")]
            tp = []
            for p in ps:
                if p in ("self", "cls"):
                    tp.append(p)
                elif "=" in p:
                    tp.append(p)
                elif p.startswith("*"):
                    tp.append(p)
                else:
                    tp.append(p + ": Any")
            out.append(indent + "def " + name + "(" + ", ".join(tp) + ")" + ret_s)
        else:
            out.append(ln)
    src2 = "\n".join(out)
    if "Any:" in src2 and not has_any_import:
        src2 = src2.replace("import numpy as np", "from typing import Any\nimport numpy as np", 1)
        if "from typing import Any" not in src2:
            src2 = src2.replace("import ", "from typing import Any\nimport ", 1)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(src2)

for f in ["export_csv.py","make_report.py","eval_harness.py","multi_conf.py","slow_path.py"]:
    annotate(f)
print("done")
