"""GitHub poster: POST review/comment with retries on 5xx."""
from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.config import get_settings
from backend.ingestion.github import parse_pr_url


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def post_comment(pr_url: str, body: str, github_token: str | None = None) -> str:
    s = get_settings()
    token = github_token or s.github_token
    if not token:
        return "skipped (no GITHUB_TOKEN)"
    owner, repo, number = parse_pr_url(pr_url)
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json={"body": body})
        r.raise_for_status()
        return str(r.json().get("html_url", r.status_code))
