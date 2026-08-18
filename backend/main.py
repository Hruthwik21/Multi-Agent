"""
PolyMind — FastAPI Backend
--------------------------
Exposes:
  POST /api/discuss  — Start a discussion session
  GET  /api/stream/{session_id} — SSE stream of agent messages
  GET  /health — Health check
"""
import asyncio
import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .discussion_engine import run_discussion
from .models import AgentMessage, DiscussionRequest

# Load environment variables from .env file
load_dotenv()

# ── In-memory session store ─────────────────────────────────────────────────
# Maps session_id -> asyncio.Queue of AgentMessage | None (None = done)
sessions: dict[str, asyncio.Queue] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup/shutdown logic."""
    print("🚀 PolyMind backend starting...")
    yield
    print("🛑 PolyMind backend shutting down...")
    sessions.clear()


app = FastAPI(
    title="PolyMind API",
    description="Multi-AI agent discussion platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow frontend (file:// or localhost) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend from /
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    """Serve the main frontend HTML file."""
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "PolyMind API is running. Frontend not found."}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gemini_key_set": bool(os.getenv("GEMINI_API_KEY")),
    }


@app.post("/api/discuss")
async def start_discussion(request: DiscussionRequest):
    """
    Start a new discussion session.
    Returns a session_id to use with the SSE /api/stream endpoint.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    rounds = max(1, min(request.rounds, 5))  # clamp between 1 and 5

    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    sessions[session_id] = queue

    # Run the discussion in the background, pushing messages to the queue
    async def run_and_enqueue():
        try:
            async for msg in run_discussion(request.query, rounds=rounds):
                await queue.put(msg)
        except Exception as e:
            error_msg = AgentMessage(
                agent="system",
                agent_name="System",
                content=f"Error: {str(e)}",
                round=-99,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            await queue.put(error_msg)
        finally:
            await queue.put(None)  # Signal completion

    asyncio.create_task(run_and_enqueue())

    return {
        "session_id": session_id,
        "query": request.query,
        "rounds": rounds,
        "stream_url": f"/api/stream/{session_id}",
    }


@app.get("/api/stream/{session_id}")
async def stream_discussion(session_id: str):
    """
    SSE endpoint — streams agent messages as they arrive.
    Each event is a JSON-encoded AgentMessage.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    queue = sessions[session_id]

    async def event_generator() -> AsyncIterator[str]:
        try:
            while True:
                msg = await asyncio.wait_for(queue.get(), timeout=120.0)
                if msg is None:
                    # Discussion complete
                    yield f"event: done\ndata: {json.dumps({'session_id': session_id})}\n\n"
                    break

                payload = {
                    "session_id": session_id,
                    "agent": msg.agent,
                    "agent_name": msg.agent_name,
                    "content": msg.content,
                    "round": msg.round,
                    "timestamp": msg.timestamp,
                }
                yield f"event: agent_message\ndata: {json.dumps(payload)}\n\n"

        except asyncio.TimeoutError:
            yield f"event: error\ndata: {json.dumps({'error': 'Timeout waiting for agent response'})}\n\n"
        finally:
            sessions.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
