import pytest


def test_parse_diff(sample_diff):
    from backend.ingestion.diff import parse_diff

    files = parse_diff(sample_diff)
    assert len(files) == 1
    assert files[0].path == "app.py"
    assert len(files[0].added_lines) >= 2


def test_language_detection():
    from backend.ingestion.language import detect_language

    assert detect_language("a.py") == "python"
    assert detect_language("a.ts") == "typescript"
    assert detect_language("a.js") == "javascript"


def test_ast_chunk_python():
    from backend.ingestion.ast_parser import chunk_python

    chunks = chunk_python("def foo():\n    return 1\n")
    assert chunks and chunks[0].name == "foo"


def test_ranker_drops_refuted(sample_ctx):
    from backend.models import Claim, VerificationStatus
    from backend.synthesis import ranker

    async def _noop(*a, **k):
        return "[]"

    c1 = Claim(id="a", issue="x", file="app.py", line=1, severity="high",
               category="bug", evidence="e", confidence=0.9, agent="t",
               verification_status=VerificationStatus.REFUTED)
    c2 = Claim(id="b", issue="y", file="app.py", line=2, severity="low",
               category="style", evidence="e", confidence=0.5, agent="t",
               verification_status=VerificationStatus.VERIFIED)
    ranked = ranker.rank_and_dedupe([c1, c2])
    assert [c.id for c in ranked] == ["b"]


def test_sandbox_blocks_traversal(sample_ctx):
    import asyncio

    from backend.errors import ToolError
    from backend.tools.read_file import read_file

    with pytest.raises(ToolError):
        asyncio.run(read_file(sample_ctx, "../../etc/passwd"))


def test_mock_llm_produces_claims(sample_ctx):
    import asyncio

    from backend.agents.bug_hunter import BugHunterAgent

    claims = asyncio.run(BugHunterAgent().review(sample_ctx))
    assert isinstance(claims, list) and len(claims) >= 1


def test_arbiter_marks_docs_unverifiable(sample_ctx):
    import asyncio

    from backend.agents.arbiter import Arbiter
    from backend.models import Claim

    c = Claim(id="d", issue="docstring missing", file="app.py", line=1,
              severity="nit", category="docs", evidence="e", confidence=0.8, agent="t")
    out = asyncio.run(Arbiter().verify([c], sample_ctx))
    assert out[0].verification_status.value == "unverifiable"


def test_metrics():
    from eval.metrics import evaluate

    m = evaluate([{"file": "a.py", "line": 10, "category": "bug"}],
                 [{"file": "a.py", "line": 12, "category": "bug"}])
    assert m["recall"] == 1.0


def test_engine_review_once(sample_diff):
    import asyncio

    from backend.engine import ReviewEngine

    claims, comment = asyncio.run(
        ReviewEngine().review_once("https://github.com/o/r/pull/1", sample_diff))
    assert len(claims) >= 1
    assert "PolyMind" in comment
