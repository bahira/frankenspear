import json
r = json.load(open("REPORT.json", encoding="utf-8"))
for t in r["tests"]:
    if not t["ok"]:
        print(t)
