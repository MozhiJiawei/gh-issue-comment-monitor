#!/usr/bin/env python
"""Verify external dependencies and auth for gh-issue-comment-monitor.

This script checks only user/environment prerequisites: GitHub credentials,
authenticated gh CLI fallback, and optional GitHub API reachability. Repository
files, checkpoint handling, script compilation, and smoke tests are internal
health checks and are intentionally outside this dependency check.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from urllib.request import Request, urlopen


def gh_auth_ok(gh_path: str | None) -> bool:
    if not gh_path:
        return False
    try:
        result = subprocess.run(
            [gh_path, "auth", "status"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except Exception:
        return False
    return result.returncode == 0


def api_reachable() -> bool:
    try:
        request = Request("https://api.github.com", method="HEAD")
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def main() -> int:
    check_network = "--check-network" in sys.argv
    has_token = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    gh_path = shutil.which("gh")
    has_gh_auth = gh_auth_ok(gh_path)

    results = {
        "ok": has_token or has_gh_auth,
        "required": [],
        "optional": [],
        "warnings": [],
    }

    results["required"].append({"name": "GITHUB_TOKEN/GH_TOKEN or authenticated gh CLI", "ok": results["ok"]})
    results["optional"].append({"name": "GITHUB_TOKEN or GH_TOKEN", "ok": has_token})
    results["optional"].append({"name": "gh CLI installed", "ok": bool(gh_path), "path": gh_path})
    results["optional"].append({"name": "gh CLI authenticated", "ok": has_gh_auth})

    if check_network:
        network_ok = api_reachable()
        results["required"].append({"name": "api.github.com reachable", "ok": network_ok})
        results["ok"] = results["ok"] and network_ok

    if not results["ok"]:
        results["warnings"].append("Real issue checks need GITHUB_TOKEN/GH_TOKEN or an authenticated gh CLI.")

    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
