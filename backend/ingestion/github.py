"""GitHub PR fetcher -> ReviewContext.

Supports: real GitHub API (PyGithub + httpx for raw diff) and offline mocks.
URL formats: https://github.com/<owner>/<repo>/pull/<number>
"""
from __future__ import annotations

import re
from typing import Optional

import httpx

from backend.config import get_settings
from backend.errors import IngestionError
from backend.ingestion.ast_parser import chunk_code, filter_by_changed
from backend.ingestion.diff import added_line_numbers, parse_diff
from backend.ingestion.language import detect_language, overall_language
from backend.models import ChangedFile, ReviewContext

PR_RE = re.compile(r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)")


def parse_pr_url(pr_url: str) -> tuple[str, str, int]:
    m = PR_RE.search(pr_url)
    if not m:
        raise IngestionError(f"Invalid GitHub PR URL: {pr_url}")
    return m.group("owner"), m.group("repo").removesuffix(".git"), int(m.group("number"))


async def fetch_pr_context(pr_url: str, github_token: Optional[str] = None) -> ReviewContext:
    settings = get_settings()
    token = github_token or settings.github_token
    owner, repo, number = parse_pr_url(pr_url)
    try:
        from github import Github  # type: ignore

        gh = Github(token) if token else Github()
        repo_obj = gh.get_repo(f"{owner}/{repo}")
        pr = repo_obj.get_pull(number)
        title = pr.title or ""
        body = pr.body or ""
        # raw diff
        diff_url = f"https://patch-diff.githubusercontent.com/raw/{owner}/{repo}/pull/{number}.diff"
        headers = {"Accept": "text/plain"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(diff_url, headers=headers, follow_redirects=True)
            diff_text = r.text if r.status_code == 200 else ""
        if len(diff_text) > settings.max_diff_chars:
            diff_text = diff_text[: settings.max_diff_chars]
        changed: list[ChangedFile] = []
        for f in pr.get_files():
            content = ""
            try:
                content = repo_obj.get_contents(f.filename, ref=pr.head.sha).decoded_content.decode(
                    "utf-8", "ignore")
            except Exception:
                content = ""
            lang = detect_language(f.filename, content)
            chunks = filter_by_changed(chunk_code(content, lang),
                                       added_line_numbers(f.patch or ""))
            changed.append(ChangedFile(path=f.filename, language=lang,
                                       patch=f.patch or "", full_content=content,
                                       ast_chunks=chunks))
        # also ensure files present in diff but missing from API are covered
        if not changed and diff_text:
            for h in parse_diff(diff_text):
                changed.append(ChangedFile(path=h.path, language=detect_language(h.path),
                                           patch=h.patch))
        ci = None
        try:
            commit = repo_obj.get_commit(pr.head.sha)
            runs = commit.get_check_runs()
            statuses = [c.conclusion for c in runs]
            ci = "passing" if statuses and all(s in ("success", "neutral") for s in statuses) else (
                "failing" if any(s == "failure" for s in statuses) else None)
        except Exception:
            ci = None
        comments: list[str] = []
        try:
            for c in pr.get_review_comments():
                comments.append(c.body or "")
        except Exception:
            pass
        langs = [c.language for c in changed]
        return ReviewContext(pr_title=title, pr_body=body or "", repo=f"{owner}/{repo}",
                             diff=diff_text, changed_files=changed, ci_status=ci,
                             existing_comments=comments[:20],
                             language=overall_language(langs))  # type: ignore[arg-type]
    except IngestionError:
        raise
    except Exception as e:
        raise IngestionError(f"Failed to fetch PR {pr_url}: {e}") from e


def context_from_diff(pr_url: str, diff_text: str, title: str = "Local diff review") -> ReviewContext:
    """Offline path: build ReviewContext directly from a unified diff (used by API + tests)."""
    owner, repo, number = ("local", "local", 0)
    try:
        owner, repo, number = parse_pr_url(pr_url)
    except IngestionError:
        pass
    hunks = parse_diff(diff_text)
    changed: list[ChangedFile] = []
    for h in hunks:
        lang = detect_language(h.path, h.patch)
        # reconstruct pseudo content from added lines for chunking
        pseudo = "\n".join(
            ln[1:] for ln in h.patch.splitlines()
            if ln.startswith("+") and not ln.startswith("+++")
        )
        chunks = chunk_code(pseudo, lang)
        changed.append(ChangedFile(path=h.path, language=lang, patch=h.patch,
                                   full_content=pseudo, ast_chunks=chunks))
    langs = [c.language for c in changed]
    repo_name = f"{owner}/{repo}" if owner != "local" else "local/local"
    return ReviewContext(pr_title=title, pr_body="", repo=repo_name, diff=diff_text,
                         changed_files=changed, ci_status=None, existing_comments=[],
                         language=overall_language(langs))  # type: ignore[arg-type]
