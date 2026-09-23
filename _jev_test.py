import json
import sys
import urllib.request
from typing import Any

API_KEY = "apikey_2211b2c64e65775540cfb0e3494c985e68e7_d2736b39c7428af04adac95889b6767bcbae603675006a88e0a14cec187ea5c9"
SERVER = "https://api.typesafe.ai"


def call_jev(text: str, model: str = "JEV-3.7-Turbo-CTP1925") -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": {
            "state": {"text": text},
            "questions": [
                {"key": "is_trivial", "candidates": ["true", "false"]},
            ],
        },
    }
    req = urllib.request.Request(
        SERVER,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": API_KEY,
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)[:120]}


def main() -> None:
    tests = [
        "salut qui es-tu aide",
        "ecris une fonction gelu fibonacci code",
        "execute lance bash tool run",
    ]
    for t in tests:
        r = call_jev(t)
        print(t[:40], "->", r.get("output", r))


if __name__ == "__main__":
    main()
