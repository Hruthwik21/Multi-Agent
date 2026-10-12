"""Redis SessionStore (prod / cache). Falls back gracefully when redis is absent."""
from __future__ import annotations

import json
from typing import Any


class RedisStore:
    def __init__(self, url: str):
        self.url = url
        self._client = None
        try:
            import redis.asyncio as aioredis  # type: ignore

            self._client = aioredis.from_url(url, decode_responses=True)
        except Exception:
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    async def save_session(self, session: dict[str, Any]) -> None:
        if not self._client:
            return
        await self._client.set(f"session:{session.get('id','')}", json.dumps(session, default=str), ex=86400)

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        if not self._client:
            return None
        raw = await self._client.get(f"session:{session_id}")
        return json.loads(raw) if raw else None

    async def save_report(self, session_id: str, html: str) -> None:
        if not self._client:
            return
        await self._client.set(f"report:{session_id}", html, ex=86400)

    async def get_report(self, session_id: str) -> str | None:
        if not self._client:
            return None
        return await self._client.get(f"report:{session_id}")
