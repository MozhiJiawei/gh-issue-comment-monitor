#!/usr/bin/env python
"""Fetch latest GitHub Issue comments, or comments after a checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from github_issue_comments import (
    ScriptError,
    checkpoint_from_comment,
    fail_json,
    fetch_comments_after,
    load_state,
    normalize_comment,
    print_json,
    save_state,
    save_updates,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub repository, shaped as OWNER/REPO.")
    parser.add_argument("--issue", required=True, type=int, help="GitHub Issue number.")
    parser.add_argument("--since", type=int, help="Return comments after this comment id.")
    parser.add_argument("--since-updated-at", help="Optional updated_at checkpoint to avoid scanning older pages.")
    parser.add_argument("--state-file", help="Read checkpoint from, and optionally write checkpoint to, this JSON file.")
    parser.add_argument("--updates-file", help="Overwrite this JSON file with only the comments returned by this run.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of comments to return.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum comment pages to inspect when --since lacks a timestamp.")
    parser.add_argument("--update-state", action="store_true", help="Update --state-file after comments are fetched successfully.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.limit < 1:
            raise ScriptError("--limit must be at least 1", 2)
        if args.max_pages < 1:
            raise ScriptError("--max-pages must be at least 1", 2)
        if args.update_state and not args.state_file:
            raise ScriptError("--update-state requires --state-file", 2)

        state = load_state(args.state_file, args.repo, args.issue) if args.state_file else None
        since_id = args.since if args.since is not None else (state or {}).get("last_seen_comment_id")
        since_updated_at = args.since_updated_at or (state or {}).get("last_seen_comment_updated_at")

        comments, truncated = fetch_comments_after(
            args.repo,
            args.issue,
            int(since_id) if since_id else None,
            args.limit,
            since_updated_at=since_updated_at,
            max_pages=args.max_pages,
        )
        latest_comment = comments[-1] if comments else None
        next_checkpoint = checkpoint_from_comment(args.repo, args.issue, latest_comment) if latest_comment else state

        state_updated = False
        if args.update_state and next_checkpoint:
            save_state(args.state_file, next_checkpoint)
            state_updated = True

        result = {
            "ok": True,
            "repo": args.repo,
            "issue": args.issue,
            "state_file": str(Path(args.state_file)) if args.state_file else None,
            "updates_file": str(Path(args.updates_file)) if args.updates_file else None,
            "since_comment_id": int(since_id) if since_id else None,
            "since_updated_at": since_updated_at,
            "limit": args.limit,
            "truncated": truncated,
            "comments": [normalize_comment(comment) for comment in comments],
            "previous_checkpoint": state,
            "next_checkpoint": next_checkpoint,
            "state_updated": state_updated,
        }
        if args.updates_file:
            save_updates(args.updates_file, result)
        print_json(result)
    except ScriptError as exc:
        fail_json(exc)


if __name__ == "__main__":
    main()
