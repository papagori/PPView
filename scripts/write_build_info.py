"""Write version and source commit metadata for the frozen application."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppview import __version__  # noqa: E402


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "ppview-build.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()
    output.write_text(json.dumps({"version": __version__, "commit": commit}, indent=2) + "\n",
                      encoding="utf-8")
    print(f"Build metadata: PPView {__version__}, commit {commit}")


if __name__ == "__main__":
    main()
