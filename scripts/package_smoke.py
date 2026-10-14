"""Launch the packaged Windows app with a generated PDF and verify its window."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

if sys.platform != "win32":
    raise SystemExit("The packaged executable smoke test requires Windows.")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from conftest import make_pdf  # noqa: E402

user32 = ctypes.windll.user32
EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
EnumWindows.restype = wintypes.BOOL
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextW = user32.GetWindowTextW
IsWindowVisible = user32.IsWindowVisible
PostMessageW = user32.PostMessageW
GetClientRect = user32.GetClientRect
GetDC = user32.GetDC
ReleaseDC = user32.ReleaseDC
gdi32 = ctypes.windll.gdi32
GetPixel = gdi32.GetPixel
WM_CLOSE = 0x0010


def window_for_pid(pid: int):
    found = []

    @EnumWindowsProc
    def visit(hwnd, _lparam):
        owner = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and IsWindowVisible(hwnd):
            size = GetWindowTextLengthW(hwnd)
            if size:
                buffer = ctypes.create_unicode_buffer(size + 1)
                GetWindowTextW(hwnd, buffer, size + 1)
                found.append((hwnd, buffer.value))
        return True

    EnumWindows(visit, 0)
    return found[0] if found else None


def main():
    root = Path(__file__).resolve().parents[1]
    exe = root / "dist" / "PPView" / "PPView.exe"
    if not exe.is_file():
        raise FileNotFoundError(exe)
    package = exe.parent
    for required in ("_internal/pypdfium2_raw/pdfium.dll", "_internal/PySide6/Qt6Core.dll",
                     "_internal/PySide6/Qt6Gui.dll", "_internal/PySide6/Qt6Widgets.dll"):
        if not (package / required).is_file():
            raise FileNotFoundError(package / required)
    archive = root / "dist" / "PPView-windows-x64.zip"
    required_zip = {"PPView/PPView.exe", "PPView/_internal/pypdfium2_raw/pdfium.dll",
                    "PPView/_internal/PySide6/Qt6Core.dll", "PPView/_internal/PySide6/Qt6Gui.dll",
                    "PPView/_internal/PySide6/Qt6Widgets.dll"}
    with zipfile.ZipFile(archive) as bundle:
        missing = required_zip - set(bundle.namelist())
        if missing:
            raise RuntimeError(f"Portable ZIP is missing required runtime files: {sorted(missing)}")
    with tempfile.TemporaryDirectory(prefix="ppview-packaged-") as folder:
        pdf = Path(folder) / "packaged-smoke.pdf"
        pdf.write_bytes(make_pdf(2))
        env = os.environ.copy()
        env["PATH"] = str(Path(os.environ["WINDIR"]) / "System32") + os.pathsep + str(Path(os.environ["WINDIR"]))
        process = subprocess.Popen([str(exe), str(pdf)], cwd=exe.parent, env=env)
        hwnd = None
        try:
            deadline = time.monotonic() + 30
            title = ""
            while time.monotonic() < deadline and process.poll() is None:
                result = window_for_pid(process.pid)
                if result:
                    hwnd, title = result
                    if "packaged-smoke.pdf" in title:
                        break
                time.sleep(0.2)
            if process.poll() is not None:
                raise RuntimeError(f"PPView.exe exited with code {process.returncode}")
            if not hwnd or "packaged-smoke.pdf" not in title:
                raise RuntimeError(f"PPView did not load the smoke PDF; window title: {title!r}")
            time.sleep(3)
            if process.poll() is not None:
                raise RuntimeError("PPView.exe exited after loading the smoke PDF")
            rect = wintypes.RECT()
            GetClientRect(hwnd, ctypes.byref(rect))
            dc = GetDC(hwnd)
            blue_pixels = 0
            try:
                # The reproducible fixture has a large saturated-blue vector
                # rectangle; find it in the actual packaged window surface.
                for y in range(0, rect.bottom, 5):
                    for x in range(0, rect.right, 5):
                        color = GetPixel(dc, x, y)
                        red, green, blue = color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF
                        if blue > 180 and red < 40 and green < 40:
                            blue_pixels += 1
            finally:
                ReleaseDC(hwnd, dc)
            if blue_pixels < 50:
                raise RuntimeError(f"Packaged window did not show rendered blue PDF content ({blue_pixels} sampled pixels)")
            safe_title = title.encode("ascii", "replace").decode("ascii")
            print(f"Packaged app opened and rendered the PDF ({blue_pixels} blue samples): {safe_title}")
            print("Portable ZIP contains PPView.exe, PDFium, and Qt Core/Gui/Widgets DLLs")
        finally:
            if process.poll() is None:
                if hwnd:
                    PostMessageW(hwnd, WM_CLOSE, 0, 0)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
