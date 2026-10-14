"""Run isolated Windows checks for the PDFium/faulthandler report.

This records whether faulthandler's exception filter changes the process outcome;
it deliberately does not disable faulthandler in pytest or the application.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


CASES = {
    "python-only": "print('python-only-ok')",
    "pypdfium-import": "import pypdfium2; print('pdfium-import-ok')",
    "pdfium-init": "import pypdfium2; assert pypdfium2.raw.FPDF_GetLastError() == 0; print('pdfium-init-ok')",
    "qt-only": "from PySide6.QtCore import QCoreApplication; print('qt-only-ok')",
    "qt-and-pdfium": "from PySide6.QtCore import QCoreApplication; import pypdfium2; print('qt-pdfium-ok')",
}


def run(label: str, args: list[str], env: dict[str, str]) -> int:
    print(f"\n=== {label} ===", flush=True)
    result = subprocess.run([sys.executable, *args], env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout.rstrip())
    print(f"exit={result.returncode}")
    return result.returncode


def main() -> int:
    env = os.environ.copy()
    env.pop("PYTHONFAULTHANDLER", None)
    env["QT_QPA_PLATFORM"] = "offscreen"
    errors = 0
    for name, code in CASES.items():
        errors += run(name, ["-c", code], env) != 0
        errors += run(f"{name} (faulthandler enabled)",
                      ["-X", "faulthandler", "-c", code], env) != 0

    # Import repeatedly in independent processes to distinguish interpreter
    # cleanup from PDFium's atexit cleanup.
    for iteration in range(5):
        errors += run(f"fresh-process import {iteration + 1}",
                      ["-c", "import pypdfium2"], env) != 0

    repo = Path(__file__).resolve().parents[1]
    pytest_code = "import pytest; raise SystemExit(pytest.main(['-q', 'tests/test_document.py']))"
    errors += run("pytest (default faulthandler behavior)", ["-c", pytest_code], env) != 0
    pytest_without_handler = ("import pytest; raise SystemExit(pytest.main(" 
                              "['-q', '-p', 'no:faulthandler', 'tests/test_document.py']))")
    errors += run("pytest (faulthandler plugin disabled for comparison)",
                  ["-c", pytest_without_handler], env) != 0
    errors += run("pytest (faulthandler explicitly enabled)",
                  ["-X", "faulthandler", "-c", pytest_code], env) != 0

    # The project smoke test renders 50 pages and then exercises normal exit.
    errors += run("repeated render and process cleanup", [str(repo / "scripts" / "pdfium_smoke.py")], env) != 0
    print("\nPackaged behavior is exercised separately by package_smoke.py on Windows.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
