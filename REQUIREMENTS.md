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
5. Provide clear script contracts so implementation can be added later without changing the Skill's user-facing behavior.

## Non-Goals For This Commit

- Do not implement the monitoring scripts yet.
- Do not add GitHub write operations.
- Do not build a daemon, scheduler, or background automation.
- Do not persist real user credentials or tokens.

## Future Script Interfaces

The Skill should eventually call scripts shaped like:

```bash
python scripts/check_issue_updates.py --repo OWNER/REPO --issue NUMBER --state-file PATH
python scripts/get_latest_comments.py --repo OWNER/REPO --issue NUMBER --since COMMENT_ID --limit 5
```

The scripts should return JSON, not prose.

## Acceptance Criteria

- The repository contains a valid `SKILL.md`.
- The Skill description clearly triggers on GitHub Issue monitoring and latest-reply workflows.
- A requirements document captures scope, non-goals, and future script contracts.
- The repository is initialized with git and the initial planning commit is created.
