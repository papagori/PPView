"""Write version and source commit metadata for the frozen application."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ppview import __display_version__, __version__, __windows_version_info__  # noqa: E402


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "ppview-build.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    build_dir = ROOT / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-c", f"safe.directory={ROOT.as_posix()}", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()
    output.write_text(json.dumps({"version": __version__, "display_version": __display_version__,
                                  "commit": commit}, indent=2) + "\n",
                      encoding="utf-8")
    (ROOT / "installer" / "version.iss").write_text(
        f'#define AppVersion "{__display_version__}"\n'
        f'#define AppNumericVersion "{".".join(map(str, __windows_version_info__))}"\n', encoding="utf-8")
    if len(__windows_version_info__) != 4 or any(part > 65535 for part in __windows_version_info__):
        raise ValueError(f"Version cannot be represented in Windows metadata: {__version__}")
    version_tuple = ", ".join(str(part) for part in __windows_version_info__)
    (build_dir / "version_info.txt").write_text(
        "# UTF-8\nVSVersionInfo(\n"
        f"  ffi=FixedFileInfo(filevers=({version_tuple}), prodvers=({version_tuple}), "
        "mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),\n"
        "  kids=[\n"
        "    StringFileInfo([StringTable('040904B0', [\n"
        "      StringStruct('CompanyName', 'Matthieu Tuffet'),\n"
        "      StringStruct('FileDescription', 'PPView local PDF and AI viewer'),\n"
        "      StringStruct('FileVersion', '" + __display_version__ + "'),\n"
        "      StringStruct('InternalName', 'PPView'),\n"
        "      StringStruct('OriginalFilename', 'PPView.exe'),\n"
        "      StringStruct('ProductName', 'PPView'),\n"
        "      StringStruct('ProductVersion', '" + __display_version__ + "'),\n"
        "      StringStruct('LegalCopyright', 'Copyright 2026 Matthieu Tuffet; GPLv3'),\n"
        "    ])]),\n"
        "    VarFileInfo([VarStruct('Translation', [1033, 1200])])\n"
        "  ]\n)\n", encoding="utf-8")
    print(f"Build metadata: PPView {__display_version__} (package {__version__}), commit {commit}")


if __name__ == "__main__":
    main()
