"""Frozen data contracts — Claim, ReviewSession, ReviewContext (Pydantic v2)."""
from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NIT = "nit"


class Category(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERF = "perf"
    STYLE = "style"
    TEST = "test"
    DOCS = "docs"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    REFUTED = "refuted"
    UNVERIFIABLE = "unverifiable"
    PENDING = "pending"


class Claim(BaseModel):
    id: str = Field(..., description="Stable hash of (file, line, issue)")
    issue: str = Field(..., max_length=500)
    file: str
    line: Optional[int] = None
    severity: Severity
    category: Category
    evidence: str = Field(..., description="Code excerpt or reasoning")
    suggested_fix: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    agent: str
    verification_status: VerificationStatus = VerificationStatus.PENDING
    verification_tool: Optional[str] = None
    verification_output: Optional[str] = None

    @staticmethod
    def make_id(file: str, line: Optional[int], issue: str) -> str:
        h = hashlib.sha256(f"{file}:{line}:{issue}".encode()).hexdigest()
        return h[:12]


class ASTChunk(BaseModel):
    kind: Literal["function", "class", "method", "block"]
    name: str
    start_line: int
    end_line: int
    code: str


class ChangedFile(BaseModel):
    path: str
    language: str = "unknown"
    patch: str = ""
    full_content: str = ""
    ast_chunks: list[ASTChunk] = []


class ReviewContext(BaseModel):
    pr_title: str = ""
    pr_body: str = ""
    repo: str = ""
    diff: str = ""
    changed_files: list[ChangedFile] = []
    ci_status: Optional[str] = None
    existing_comments: list[str] = []
    language: Literal["python", "typescript", "javascript", "mixed", "unknown"] = "unknown"


class ReviewSession(BaseModel):
    id: str
    pr_url: str
    repo: str = ""
    pr_number: int = 0
    base_sha: str = ""
    head_sha: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: Literal["pending", "running", "done", "failed"] = "pending"
    claims: list[Claim] = []
    final_comment: Optional[str] = None
    cost_usd: float = 0.0
    tokens_used: int = 0
    latency_ms: int = 0
    error: Optional[str] = None
