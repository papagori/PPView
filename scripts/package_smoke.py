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

# Make the helper see the packaged app's per-monitor physical client size.
# Otherwise Windows DPI virtualization returns logical coordinates and PrintWindow
# captures only part of a high-DPI window.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    pass

from PySide6.QtGui import QImage

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
GetWindowRect = user32.GetWindowRect
GetDC = user32.GetDC
ReleaseDC = user32.ReleaseDC
gdi32 = ctypes.windll.gdi32
PrintWindow = user32.PrintWindow
GetPixel = gdi32.GetPixel
CreateCompatibleDC = gdi32.CreateCompatibleDC
CreateCompatibleBitmap = gdi32.CreateCompatibleBitmap
SelectObject = gdi32.SelectObject
BitBlt = gdi32.BitBlt
GetDIBits = gdi32.GetDIBits
DeleteObject = gdi32.DeleteObject
DeleteDC = gdi32.DeleteDC
SRCCOPY = 0x00CC0020
BI_RGB = 0
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


def capture_window(hwnd, output: Path):
    """Save the actual packaged window surface for visual QA."""
    rect = wintypes.RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    screen_dc = GetDC(hwnd)
    memory_dc = CreateCompatibleDC(screen_dc)
    bitmap = CreateCompatibleBitmap(screen_dc, width, height)
    previous = SelectObject(memory_dc, bitmap)
    try:
        if not PrintWindow(hwnd, memory_dc, 2) and not BitBlt(memory_dc, 0, 0, width, height, screen_dc, 0, 0, SRCCOPY):
            raise RuntimeError("Could not capture packaged window surface")

        class BitmapInfoHeader(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]

        class BitmapInfo(ctypes.Structure):
            _fields_ = [("bmiHeader", BitmapInfoHeader), ("bmiColors", wintypes.DWORD * 3)]

        info = BitmapInfo()
        info.bmiHeader.biSize = ctypes.sizeof(BitmapInfoHeader)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        pixels = ctypes.create_string_buffer(width * height * 4)
        if not GetDIBits(memory_dc, bitmap, 0, height, pixels, ctypes.byref(info), 0):
            raise RuntimeError("Could not read packaged window pixels")
        image = QImage(pixels, width, height, width * 4, QImage.Format.Format_RGB32).copy()
        output.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(output)):
            raise RuntimeError(f"Could not save visual smoke capture to {output}")
    finally:
        SelectObject(memory_dc, previous)
        DeleteObject(bitmap)
        DeleteDC(memory_dc)
        ReleaseDC(hwnd, screen_dc)


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
            capture_path = root / "dist" / "PPView-v0.1.3-smoke.png"
            capture_window(hwnd, capture_path)
            safe_title = title.encode("ascii", "replace").decode("ascii")
            print(f"Packaged app opened and rendered the PDF ({blue_pixels} blue samples): {safe_title}")
            print("Portable ZIP contains PPView.exe, PDFium, and Qt Core/Gui/Widgets DLLs")
            print(f"Visual smoke capture saved to {capture_path}")
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
