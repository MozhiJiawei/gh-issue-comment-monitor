---
name: gh-issue-comment-monitor
description: Monitor GitHub Issue comment activity and fetch only the latest relevant replies through bundled scripts. Use when Codex is collaborating through GitHub Issues, the user asks to check an issue again, read the latest reply, monitor an issue, fetch new comments, or avoid repeatedly loading full issue history.
---

# GitHub Issue Comment Monitor

## Overview

Use this skill to keep GitHub Issue based collaboration lightweight. Prefer the bundled scripts instead of repeatedly expanding the full issue discussion into the conversation.

## Workflow

1. Identify the target issue from the user request, current thread context, or a provided GitHub Issue URL.
2. Use the monitor script to check whether the issue has comments newer than the last recorded checkpoint.
3. Use the latest-comment script to fetch only new or latest comments needed for the current reply.
4. Summarize the new information and continue the task without replaying the entire issue history.
5. Update the checkpoint only after the new comments have been processed successfully. Use `--update-state` on the fetch script when it is safe to mark the returned comments as handled.

## Commands

Check whether an issue has replies after the local checkpoint without marking them handled:

```powershell
python scripts/check_issue_updates.py --repo OWNER/REPO --issue NUMBER --state-file PATH --updates-file UPDATES_JSON
```

Fetch comments after a known comment id:

```powershell
python scripts/get_latest_comments.py --repo OWNER/REPO --issue NUMBER --since COMMENT_ID --limit 5
```

Fetch comments after the local checkpoint and advance the checkpoint after successful processing:

```powershell
python scripts/get_latest_comments.py --repo OWNER/REPO --issue NUMBER --state-file PATH --updates-file UPDATES_JSON --limit 5 --update-state
```

Run dependency and smoke validation from the skill root:

```powershell
python verify_dependencies.py
```

## Script Contract

- `check_issue_updates.py` reports whether new comments exist, returns a bounded sample of new comments, and never updates the checkpoint file.
- `get_latest_comments.py` returns latest comments or comments after a checkpoint. When `--state-file` is provided, it uses `last_seen_comment_id` and `last_seen_comment_updated_at`; when `--update-state` is also provided, it writes the next local checkpoint.
- `--updates-file` always overwrites the target JSON file with only this run's new or returned comments. It must not become a cumulative issue archive.
- Both scripts preserve comment id, author, created time, updated time, URL, API URL, and body.
- Both scripts emit machine-readable JSON by default so Codex can consume the result without parsing prose.
- Both scripts use `GITHUB_TOKEN` or `GH_TOKEN` for GitHub REST API access. If no token is present, they fall back to `gh api`.
- Scripts never mutate GitHub Issues.

## State File

Treat the state file as a local per-issue checkpoint. It should not contain comment bodies. Store it under the host workspace `.tmp/` tree when this skill is called from a registered workspace, for example:

```powershell
$state = ".tmp/gh-issue-comment-monitor/MozhiJiawei-Mozhi-s-AgentWorkspace-3.json"
```

The JSON checkpoint records:

- `repo`
- `issue`
- `last_seen_comment_id`
- `last_seen_comment_author`
- `last_seen_comment_created_at`
- `last_seen_comment_updated_at`
- `last_seen_comment_url`
- `checked_at`

## Updates File

Use an updates file as the only file an agent should read for Issue replies during the current turn. This file is overwritten on each check/fetch and contains only the comments returned by that script invocation:

```powershell
$updates = ".tmp/gh-issue-comment-monitor/MozhiJiawei-Mozhi-s-AgentWorkspace-3-updates.json"
```

Never append older comments to the updates file. If no new replies exist, the file should show an empty `comments` or `new_comments` array.

## Context Discipline

When using this skill, load only:

- The issue metadata needed to identify the thread.
- New comments since the previous checkpoint.
- Earlier comments only when the latest reply explicitly depends on unresolved prior context.

Avoid fetching the full issue history when the user asks for the latest reply unless the script reports no checkpoint or the task requires reconstruction.

If `truncated` is `true`, say that the script hit its bounded scan limit and rerun with a larger `--max-pages` only if the task needs older unprocessed replies.
