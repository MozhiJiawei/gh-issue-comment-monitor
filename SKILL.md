---
name: gh-issue-comment-monitor
description: Monitor GitHub Issue comment activity and fetch only the latest relevant replies through bundled scripts. Use when Codex is collaborating through GitHub Issues, the user asks to check an issue again, read the latest reply, monitor an issue, fetch new comments, or avoid repeatedly loading full issue history.
---

# GitHub Issue Comment Monitor

## Overview

Use this skill to keep GitHub Issue based collaboration lightweight. Prefer running the bundled scripts, once implemented, instead of repeatedly expanding the full issue discussion into the conversation.

## Workflow

1. Identify the target issue from the user request, current thread context, or a provided GitHub Issue URL.
2. Use the monitor script to check whether the issue has comments newer than the last recorded checkpoint.
3. Use the latest-comment script to fetch only new or latest comments needed for the current reply.
4. Summarize the new information and continue the task without replaying the entire issue history.
5. Update the checkpoint only after the new comments have been processed successfully.

## Script Contract

Future implementations should provide scripts under `scripts/` with stable command-line interfaces:

```bash
python scripts/check_issue_updates.py --repo OWNER/REPO --issue NUMBER --state-file PATH
python scripts/get_latest_comments.py --repo OWNER/REPO --issue NUMBER --since COMMENT_ID --limit 5
```

Expected behavior:

- `check_issue_updates.py` reports whether new comments exist and returns the newest comment id, author, timestamp, and URL.
- `get_latest_comments.py` returns the latest comments or only comments after a checkpoint, preserving author, comment id, created/updated time, URL, and body.
- Scripts should support GitHub connector output when available and `gh` CLI fallback when practical.
- Scripts should emit machine-readable JSON by default so Codex can consume the result without parsing human prose.
- Scripts should never mutate GitHub Issues unless explicitly designed and invoked for a write operation.

## Context Discipline

When using this skill, load only:

- The issue metadata needed to identify the thread.
- New comments since the previous checkpoint.
- Earlier comments only when the latest reply explicitly depends on unresolved prior context.

Avoid fetching the full issue history when the user asks for the latest reply unless the script reports no checkpoint or the task requires reconstruction.
