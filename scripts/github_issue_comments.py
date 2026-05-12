"""Small GitHub Issue comment helpers used by this skill's scripts."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_ROOT = "https://api.github.com"


class ScriptError(Exception):
    def __init__(self, message: str, exit_code: int = 1, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.exit_code = exit_code
        self.details = details or {}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_repo(value: str) -> tuple[str, str]:
    match = re.fullmatch(r"([^/\s]+)/([^/\s]+)", value.strip())
    if not match:
        raise ScriptError("--repo must be shaped like OWNER/REPO", 2, {"repo": value})
    return match.group(1), match.group(2)


def load_state(path: str | None, repo: str, issue: int) -> dict[str, Any] | None:
    if not path:
        return None
    state_path = Path(path)
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScriptError("state file is not valid JSON", 2, {"path": str(state_path), "error": str(exc)})

    state_repo = data.get("repo")
    state_issue = data.get("issue")
    if state_repo and state_repo != repo:
        raise ScriptError("state file belongs to a different repository", 2, {"path": str(state_path), "state_repo": state_repo, "repo": repo})
    if state_issue and int(state_issue) != int(issue):
        raise ScriptError("state file belongs to a different issue", 2, {"path": str(state_path), "state_issue": state_issue, "issue": issue})
    return data


def save_state(path: str, state: dict[str, Any]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_updates(path: str, updates: dict[str, Any]) -> None:
    updates_path = Path(path)
    updates_path.parent.mkdir(parents=True, exist_ok=True)
    updates_path.write_text(json.dumps(updates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def checkpoint_from_comment(repo: str, issue: int, comment: dict[str, Any] | None) -> dict[str, Any]:
    checkpoint: dict[str, Any] = {
        "repo": repo,
        "issue": issue,
        "checked_at": now_iso(),
    }
    if comment:
        checkpoint.update(
            {
                "last_seen_comment_id": comment.get("id"),
                "last_seen_comment_author": (comment.get("user") or {}).get("login"),
                "last_seen_comment_created_at": comment.get("created_at"),
                "last_seen_comment_updated_at": comment.get("updated_at"),
                "last_seen_comment_url": comment.get("html_url"),
            }
        )
    return checkpoint


def normalize_comment(comment: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": comment.get("id"),
        "author": (comment.get("user") or {}).get("login"),
        "created_at": comment.get("created_at"),
        "updated_at": comment.get("updated_at"),
        "url": comment.get("html_url"),
        "api_url": comment.get("url"),
        "body": comment.get("body") or "",
    }


def api_get(path: str, params: dict[str, Any] | None = None) -> tuple[Any, dict[str, str]]:
    params = {key: value for key, value in (params or {}).items() if value is not None}
    query = urllib.parse.urlencode(params)
    url = f"{API_ROOT}{path}"
    if query:
        url = f"{url}?{query}"

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return _api_get_with_token(url, token)
    return _api_get_with_gh(path, params)


def _api_get_with_token(url: str, token: str) -> tuple[Any, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "gh-issue-comment-monitor-skill",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            headers = {key.lower(): value for key, value in response.headers.items()}
            return data, headers
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ScriptError("GitHub API request failed", 3, {"status": exc.code, "url": url, "body": body})
    except urllib.error.URLError as exc:
        raise ScriptError("GitHub API request could not connect", 3, {"url": url, "error": str(exc)})


def _api_get_with_gh(path: str, params: dict[str, Any]) -> tuple[Any, dict[str, str]]:
    command = ["gh", "api", "--method", "GET", path]
    for key, value in params.items():
        command.extend(["-F", f"{key}={value}"])
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8", timeout=45)
    except FileNotFoundError:
        raise ScriptError("set GITHUB_TOKEN/GH_TOKEN or install and authenticate GitHub CLI", 2)
    except subprocess.TimeoutExpired:
        raise ScriptError("gh api request timed out", 3, {"path": path})
    if completed.returncode != 0:
        raise ScriptError("gh api request failed", 3, {"stderr": completed.stderr.strip(), "path": path})
    try:
        return json.loads(completed.stdout), {}
    except json.JSONDecodeError as exc:
        raise ScriptError("gh api returned invalid JSON", 3, {"error": str(exc), "path": path})


def fetch_issue(repo: str, issue: int) -> dict[str, Any]:
    owner, name = parse_repo(repo)
    data, _headers = api_get(f"/repos/{owner}/{name}/issues/{issue}")
    if "pull_request" in data:
        raise ScriptError("target is a pull request, not a GitHub Issue", 2, {"repo": repo, "issue": issue})
    return data


def fetch_comment_page(repo: str, issue: int, page: int, per_page: int = 100, since_updated_at: str | None = None) -> list[dict[str, Any]]:
    owner, name = parse_repo(repo)
    data, _headers = api_get(
        f"/repos/{owner}/{name}/issues/{issue}/comments",
        {"per_page": per_page, "page": page, "since": since_updated_at},
    )
    if not isinstance(data, list):
        raise ScriptError("GitHub comments endpoint returned unexpected data", 3, {"repo": repo, "issue": issue})
    return data


def fetch_latest_comments(repo: str, issue: int, limit: int) -> list[dict[str, Any]]:
    issue_data = fetch_issue(repo, issue)
    total_comments = int(issue_data.get("comments") or 0)
    if total_comments == 0:
        return []
    per_page = 100
    last_page = max(1, (total_comments + per_page - 1) // per_page)
    comments = fetch_comment_page(repo, issue, last_page, per_page=per_page)
    return comments[-limit:]


def fetch_comments_after(
    repo: str,
    issue: int,
    since_comment_id: int | None,
    limit: int,
    since_updated_at: str | None = None,
    max_pages: int = 5,
) -> tuple[list[dict[str, Any]], bool]:
    """Return comments after a checkpoint and whether the scan may be incomplete."""
    if since_updated_at:
        collected: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            page_comments = fetch_comment_page(repo, issue, page, per_page=100, since_updated_at=since_updated_at)
            if not page_comments:
                break
            collected.extend(page_comments)
            if len(page_comments) < 100:
                break
        filtered = [comment for comment in collected if since_comment_id is None or int(comment["id"]) > since_comment_id]
        filtered.sort(key=lambda item: int(item["id"]))
        return filtered[:limit], len(collected) >= max_pages * 100

    if since_comment_id is None:
        return fetch_latest_comments(repo, issue, limit), False

    issue_data = fetch_issue(repo, issue)
    total_comments = int(issue_data.get("comments") or 0)
    if total_comments == 0:
        return [], False

    collected = []
    last_page = max(1, (total_comments + 99) // 100)
    earliest_page = max(1, last_page - max_pages + 1)
    found_checkpoint = False
    for page in range(last_page, earliest_page - 1, -1):
        page_comments = fetch_comment_page(repo, issue, page, per_page=100)
        for comment in reversed(page_comments):
            comment_id = int(comment["id"])
            if comment_id == since_comment_id:
                found_checkpoint = True
                break
            if comment_id > since_comment_id:
                collected.append(comment)
        if found_checkpoint:
            break
    collected.reverse()
    return collected[:limit], not found_checkpoint and earliest_page > 1


def print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def fail_json(exc: ScriptError) -> None:
    print_json({"ok": False, "error": str(exc), "details": exc.details})
    sys.exit(exc.exit_code)
