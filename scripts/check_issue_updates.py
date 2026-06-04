#!/usr/bin/env python
"""Check whether a GitHub Issue has comments newer than a local checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

from github_issue_comments import (
    ScriptError,
    checkpoint_from_comment,
    fail_json,
    fetch_comments_after,
    fetch_latest_comments,
    load_state,
    normalize_comment,
    print_json,
    save_updates,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub repository, shaped as OWNER/REPO.")
    parser.add_argument("--issue", required=True, type=int, help="GitHub Issue number.")
    parser.add_argument("--state-file", required=True, help="Local JSON checkpoint file.")
    parser.add_argument("--updates-file", help="Overwrite this JSON file with only the comments found in this check.")
    parser.add_argument("--limit", type=int, default=5, help="Maximum new-comment sample size to return.")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum comment pages to inspect when checking from a checkpoint.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.limit < 1:
            raise ScriptError("--limit must be at least 1", 2)
        if args.max_pages < 1:
            raise ScriptError("--max-pages must be at least 1", 2)

        state = load_state(args.state_file, args.repo, args.issue)
        since_id = state.get("last_seen_comment_id") if state else None
        since_updated_at = state.get("last_seen_comment_updated_at") if state else None

        comments, truncated = fetch_comments_after(
            args.repo,
            args.issue,
            int(since_id) if since_id else None,
            args.limit,
            since_updated_at=since_updated_at,
            max_pages=args.max_pages,
        )
        if comments:
            latest_comment = comments[-1]
        elif not state:
            latest_comments = fetch_latest_comments(args.repo, args.issue, 1)
            latest_comment = latest_comments[-1] if latest_comments else None
        else:
            latest_comment = None
        recommended_state = checkpoint_from_comment(args.repo, args.issue, latest_comment) if latest_comment else state

        result = {
            "ok": True,
            "repo": args.repo,
            "issue": args.issue,
            "state_file": str(Path(args.state_file)),
            "updates_file": str(Path(args.updates_file)) if args.updates_file else None,
            "has_updates": bool(comments),
            "new_comment_count_sampled": len(comments),
            "truncated": truncated,
            "previous_checkpoint": state,
            "latest_comment": normalize_comment(latest_comment) if latest_comment else None,
            "new_comments": [normalize_comment(comment) for comment in comments],
            "recommended_checkpoint": recommended_state,
            "state_updated": False,
        }
        if args.updates_file:
            save_updates(args.updates_file, result)
        print_json(result)
    except ScriptError as exc:
        fail_json(exc)


if __name__ == "__main__":
    main()
