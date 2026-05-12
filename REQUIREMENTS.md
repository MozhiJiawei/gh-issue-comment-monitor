# Requirements: GitHub Issue Comment Monitor Skill

## Goal

Create a Codex Skill that helps agents collaborate through GitHub Issues without repeatedly loading the full issue discussion into the model context. The skill should guide agents to call deterministic scripts for monitoring Issue activity and fetching only the latest relevant comments.

## Problem

During long Issue-driven debugging sessions, repeatedly reading every comment causes rapid context growth. The agent often only needs to know whether a new reply exists and what the newest reply says.

## Target Users

- Codex agents working with a user through GitHub Issues.
- Users who ask short follow-ups such as "再看", "看最新回复", or "结果回复 ISSUE".

## Required Capabilities

1. Monitor whether a GitHub Issue has new replies.
2. Fetch the latest comment result, or comments after a known checkpoint.
3. Preserve enough metadata for reliable follow-up:
   - repository
   - issue number
   - comment id
   - author
   - created or updated time
   - comment URL
   - body
4. Avoid loading full Issue history when only the newest reply is needed.
5. Provide clear script contracts so future agents can use the behavior without loading full Issue history.
6. Keep the AI-facing updates file delta-only; do not maintain a cumulative copy of the full Issue discussion.

## Non-Goals For This Commit

- Do not add GitHub write operations.
- Do not build a daemon, scheduler, or background automation.
- Do not persist real user credentials or tokens.

## Script Interfaces

The Skill calls scripts shaped like:

```bash
python scripts/check_issue_updates.py --repo OWNER/REPO --issue NUMBER --state-file PATH
python scripts/get_latest_comments.py --repo OWNER/REPO --issue NUMBER --since COMMENT_ID --limit 5
```

The scripts should return JSON, not prose.

Both scripts support `--updates-file PATH`, which overwrites the target file with only comments returned by the current run. `get_latest_comments.py` also supports `--state-file PATH --update-state` to advance a local checkpoint after successful processing.

## Acceptance Criteria

- The repository contains a valid `SKILL.md`.
- The Skill description clearly triggers on GitHub Issue monitoring and latest-reply workflows.
- A requirements document captures scope, non-goals, and future script contracts.
- The repository contains executable script implementations for checking issue updates and fetching bounded latest comments.
- The repository provides `python verify_dependencies.py` for workspace integration.
