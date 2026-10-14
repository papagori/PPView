"""Build metadata shown by the About dialog for support diagnostics."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def build_commit() -> str:
    if getattr(sys, "frozen", False):
        build_file = Path(getattr(sys, "_MEIPASS", "")) / "ppview-build.json"
        try:
            return json.loads(build_file.read_text(encoding="utf-8")).get("commit", "unknown")
        except (OSError, ValueError, AttributeError):
            return "unknown"
    repo_root = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(["git", "-c", f"safe.directory={repo_root.as_posix()}", "rev-parse", "HEAD"], cwd=repo_root,
                                capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
