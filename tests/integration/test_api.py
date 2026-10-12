import pytest
from fastapi.testclient import TestClient


def test_health():
    from backend.main import app

    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_review_e2e():
    from backend.main import app

    c = TestClient(app)
    diff = "diff --git a/app.py b/app.py\n@@ -1 +1,2 @@\n line1\n+    eval(x)\n"
    r = c.post("/api/review", json={"pr_url": "https://github.com/o/r/pull/1", "diff": diff})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    import time

    for _ in range(100):
        s = c.get(f"/api/sessions/{sid}").json()
        if s.get("status") == "done":
            break
        time.sleep(0.2)
    assert s.get("status") == "done"
    assert s["result"]["claims"]
