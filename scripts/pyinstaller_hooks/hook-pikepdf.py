"""Collect pikepdf plus its separately vendored Windows QPDF DLLs."""
from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all("pikepdf")
spec = find_spec("pikepdf")
if spec and spec.origin:
    wheel_root = Path(spec.origin).resolve().parent.parent
    for library in (wheel_root / "pikepdf.libs").glob("*.dll"):
        binaries.append((str(library), "pikepdf.libs"))
