#!/usr/bin/env python
"""Verify dependencies for the GitHub Issue Comment Monitor skill."""

from __future__ import annotations

import json
import os
import py_compile
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    ROOT / "scripts" / "github_issue_comments.py",
    ROOT / "scripts" / "check_issue_updates.py",
    ROOT / "scripts" / "get_latest_comments.py",
]


def main() -> int:
    results = {
        "ok": True,
        "required": [],
        "optional": [],
        "warnings": [],
    }

    for script in SCRIPTS:
        try:
            py_compile.compile(str(script), doraise=True)
            results["required"].append({"name": str(script.relative_to(ROOT)), "ok": True})
        except py_compile.PyCompileError as exc:
            results["ok"] = False
            results["required"].append({"name": str(script.relative_to(ROOT)), "ok": False, "error": str(exc)})

    has_token = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    gh_path = shutil.which("gh")
    auth_ok = has_token or bool(gh_path)
    results["optional"].append({"name": "GITHUB_TOKEN or GH_TOKEN", "ok": has_token})
    results["optional"].append({"name": "gh CLI fallback", "ok": bool(gh_path), "path": gh_path})
    if not auth_ok:
        results["warnings"].append("GitHub API access needs GITHUB_TOKEN/GH_TOKEN or an authenticated gh CLI for real issue checks.")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
