"""SessionStore ABC — persistence of sessions, claims, reports."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SessionStore(ABC):
    @abstractmethod
    async def save_session(self, session: dict[str, Any]) -> None: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def save_report(self, session_id: str, html: str) -> None: ...

    @abstractmethod
    async def get_report(self, session_id: str) -> str | None: ...
