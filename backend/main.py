"""FastAPI app: POST /api/review, GET /api/stream/{id}, GET /api/report/{id}, GET /health."""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.config import get_settings
from backend.engine import ReviewEngine
from backend.logging_setup import get_logger, setup_logging
from backend.storage.sqlite import SQLiteStore
from backend.synthesis.github_poster import post_comment

settings = get_settings()
setup_logging(settings.log_level)
log = get_logger(component="api")

app = FastAPI(title="PolyMind v2 — Code Review Council", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = SQLiteStore(settings.database_url)
engine = ReviewEngine()
_jobs: dict[str, dict] = {}


class ReviewRequest(BaseModel):
    pr_url: str
    diff: Optional[str] = None
    post_to_github: bool = False


@app.get("/health")
async def health():  # type: ignore[no-untyped-def]
    s = get_settings()
    return {"status": "ok", "llm": "live" if s.has_llm_key else "mock",
            "model": s.gemini_model, "version": "2.0.0"}


@app.post("/api/review")
async def start_review(req: ReviewRequest):  # type: ignore[no-untyped-def]
    session_id = uuid.uuid4().hex[:8]
    _jobs[session_id] = {"pr_url": req.pr_url, "diff": req.diff,
                         "post": req.post_to_github, "events": [],
                         "status": "pending", "result": None}
    asyncio.create_task(_run_job(session_id))
    return {"session_id": session_id, "stream_url": f"/api/stream/{session_id}"}


async def _run_job(session_id: str) -> None:
    job = _jobs[session_id]
    job["status"] = "running"
    t0 = time.time()
    try:
        async for ev in engine.run(job["pr_url"], job["diff"]):
            job["events"].append({"event": ev.event, "data": ev.data})
            if ev.event == "done":
                job["result"] = ev.data
                if job["post"]:
                    try:
                        url = await post_comment(job["pr_url"], ev.data.get("comment", ""))
                        job["result"]["posted_url"] = url
                    except Exception as e:
                        job["result"]["post_error"] = str(e)[:500]
                await store.save_session({"id": session_id, "pr_url": job["pr_url"],
                                          "claims": ev.data.get("claims", []),
                                          "comment": ev.data.get("comment", "")})
                await store.save_report(session_id, _report_html(
                    session_id, job["pr_url"], ev.data.get("claims", []),
                    ev.data.get("comment", "")))
        job["status"] = "done"
        job["latency_ms"] = int((time.time() - t0) * 1000)
    except Exception as e:
        log.error("job-failed", session_id=session_id, error=str(e)[:500])
        job["status"] = "failed"
        job["events"].append({"event": "error", "data": {"message": str(e)[:500]}})


@app.get("/api/stream/{session_id}")
async def stream(session_id: str):  # type: ignore[no-untyped-def]
    if session_id not in _jobs:
        saved = await store.get_session(session_id)
        if not saved:
            raise HTTPException(404, "unknown session")
        return JSONResponse(saved)

    async def gen():  # type: ignore[no-untyped-def]
        import json

        seen = 0
        while True:
            job = _jobs[session_id]
            while seen < len(job["events"]):
                ev = job["events"][seen]
                seen += 1
                yield {"event": ev["event"], "data": json.dumps(ev["data"], default=str)}
            if job["status"] in ("done", "failed"):
                break
            await asyncio.sleep(0.2)

    return EventSourceResponse(gen())


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):  # type: ignore[no-untyped-def]
    if session_id in _jobs:
        return _jobs[session_id]
    saved = await store.get_session(session_id)
    if not saved:
        raise HTTPException(404, "unknown session")
    return saved


@app.get("/api/report/{session_id}", response_class=HTMLResponse)
async def get_report(session_id: str):  # type: ignore[no-untyped-def]
    html = await store.get_report(session_id)
    if html:
        return HTMLResponse(html)
    if session_id in _jobs and _jobs[session_id].get("result"):
        r = _jobs[session_id]["result"]
        return HTMLResponse(_report_html(session_id, _jobs[session_id]["pr_url"],
                                         r.get("claims", []), r.get("comment", "")))
    raise HTTPException(404, "report not ready")


@app.post("/webhook/github")
async def webhook(payload: dict):  # type: ignore[no-untyped-def]
    # GitHub App webhook (minimal): pull_request opened/synchronize -> start review
    try:
        pr = payload.get("pull_request", {})
        url = pr.get("html_url", "")
        if not url:
            return {"ok": False, "reason": "no pull_request.html_url"}
        session_id = uuid.uuid4().hex[:8]
        _jobs[session_id] = {"pr_url": url, "diff": None, "post": True,
                             "events": [], "status": "pending", "result": None}
        asyncio.create_task(_run_job(session_id))
        return {"ok": True, "session_id": session_id}
    except Exception as e:
        raise HTTPException(400, str(e))


def _report_html(session_id: str, pr_url: str, claims: list, comment: str) -> str:
    rows = "".join(
        f"<tr><td>{c.get('file','')}:{c.get('line','')}</td><td>{c.get('severity','')}</td>"
        f"<td>{c.get('issue','')}</td><td>{c.get('verification_status','')}</td></tr>"
        for c in claims)
    return (f"<html><head><title>PolyMind report {session_id}</title></head><body>"
            f"<h1>PolyMind Review — {session_id}</h1><p>PR: {pr_url}</p>"
            f"<pre>{comment}</pre><table border=1><tr><th>Loc</th><th>Sev</th>"
            f"<th>Issue</th><th>Status</th></tr>{rows}</table></body></html>")


# serve frontend static (index.html etc.) at /
try:
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
except Exception:
    pass
