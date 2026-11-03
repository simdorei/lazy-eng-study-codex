from __future__ import annotations

# ruff: noqa: T201 -- stdout is the JSON-RPC protocol for this test fixture.
import json
import os
import sys
import time

mode = os.environ.get("FAKE_MODEL_MODE", "pages")
for line in sys.stdin:
    request = json.loads(line)
    request_id = request.get("id")
    if request_id is None:
        continue
    if request["method"] == "initialize":
        result = {}
    elif mode == "timeout":
        time.sleep(30)
        continue
    elif mode == "exit":
        _ = sys.stderr.write("catalog unavailable\n")
        sys.exit(7)
    elif mode == "invalid":
        print("not JSON", flush=True)
        continue
    elif mode == "error":
        print(json.dumps({"id": request_id, "error": {"message": "sign in required"}}), flush=True)
        continue
    else:
        cursor = request["params"].get("cursor")
        result = {
            "data": [
                {
                    "model": "gpt-10.1-new" if cursor is None else "gpt-8.2-old",
                    "supportedReasoningEfforts": [{"reasoningEffort": "medium"}],
                }
            ],
            "nextCursor": "page2" if cursor is None or mode == "repeat" else None,
        }
        print(json.dumps({"method": "catalog/notice", "params": {}}), flush=True)
    print(json.dumps({"id": request_id, "result": result}), flush=True)
