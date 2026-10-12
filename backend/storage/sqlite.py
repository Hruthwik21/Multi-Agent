"""SQLite SessionStore (dev default). Thread-safe via check_same_thread=False + lock."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


class SQLiteStore:
    def __init__(self, path: str = "./polymind.db"):
        clean = path.replace("sqlite:///", "").replace("sqlite://", "")
        self.path = clean or "./polymind.db"
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, check_same_thread=False)

    def _init(self) -> None:
        with self._lock, self._connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            con.execute(
                "CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, html TEXT NOT NULL)"
            )

    async def save_session(self, session: dict[str, Any]) -> None:
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO sessions (id, data) VALUES (?, ?)",
                (session.get("id", ""), json.dumps(session, default=str)),
            )

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as con:
            row = con.execute("SELECT data FROM sessions WHERE id=?", (session_id,)).fetchone()
        return json.loads(row[0]) if row else None

    async def save_report(self, session_id: str, html: str) -> None:
        with self._lock, self._connect() as con:
            con.execute("INSERT OR REPLACE INTO reports (id, html) VALUES (?, ?)", (session_id, html))

    async def get_report(self, session_id: str) -> str | None:
        with self._lock, self._connect() as con:
            row = con.execute("SELECT html FROM reports WHERE id=?", (session_id,)).fetchone()
        return row[0] if row else None
