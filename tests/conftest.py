"""Pytest fixtures."""
import pytest


@pytest.fixture
def sample_diff() -> str:
    return """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1,6 +1,7 @@
 def handle(req):
+    result = eval(req.get('expr'))
     try:
         save(req)
-    except ValueError:
+    except:
         pass
+    # TODO: fix this
"""


@pytest.fixture
def sample_ctx(sample_diff):
    from backend.ingestion.github import context_from_diff

    return context_from_diff("https://github.com/o/r/pull/1", sample_diff)
