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

# Make pixel sampling use the packaged app's per-monitor physical client size.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    pass

from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage, QPainter

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
GetDC.argtypes = [wintypes.HWND]
GetDC.restype = wintypes.HDC
ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
ReleaseDC.restype = ctypes.c_int
gdi32 = ctypes.windll.gdi32
GetPixel = gdi32.GetPixel
GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
GetPixel.restype = wintypes.DWORD
WM_CLOSE = 0x0010


def verify_executable_icon(exe: Path):
    """Verify the packaged PE icon group and every embedded PNG payload."""
    import struct
    import pefile

    ico_path = exe.parents[2] / "assets" / "logo" / "ppview.ico"
    ico = ico_path.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", ico)
    if (reserved, kind) != (0, 1):
        raise RuntimeError("Source logo is not a Windows ICO")
    source_icons = {}
    for index in range(count):
        width, height, _colors, _reserved, _planes, _bpp, length, offset = struct.unpack_from("<BBBBHHII", ico, 6 + index * 16)
        source_icons[(width or 256, height or 256)] = ico[offset:offset + length]
    required_sizes = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}
    if count != len(required_sizes) or not required_sizes.issubset(source_icons):
        raise RuntimeError(f"Source ICO is missing sizes: {sorted(required_sizes - source_icons.keys())}")

    pe = pefile.PE(str(exe), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
    resources = {entry.id: entry for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries}

    def resource_data(entry):
        if hasattr(entry, "data"):
            return entry.data
        if hasattr(entry, "directory") and entry.directory.entries:
            return resource_data(entry.directory.entries[0])
        return None

    group_type = resources.get(pefile.RESOURCE_TYPE['RT_GROUP_ICON'])
    icon_type = resources.get(pefile.RESOURCE_TYPE['RT_ICON'])
    if not group_type or not icon_type:
        raise RuntimeError("PPView.exe is missing RT_GROUP_ICON or RT_ICON resources")
    groups = [resource_data(entry) for entry in group_type.directory.entries]
    icons = {entry.id: pe.get_data(resource_data(entry).struct.OffsetToData, resource_data(entry).struct.Size)
             for entry in icon_type.directory.entries}
    groups = [entry for entry in groups if entry is not None]
    if not groups:
        raise RuntimeError("PPView.exe has no icon group resource")
    matched = False
    for group in groups:
        payload = pe.get_data(group.struct.OffsetToData, group.struct.Size)
        reserved, kind, group_count = struct.unpack_from("<HHH", payload)
        if (reserved, kind) != (0, 1):
            continue
        embedded = {}
        for index in range(group_count):
            width, height, _colors, _reserved, _planes, _bpp, length, icon_id = struct.unpack_from("<BBBBHHIH", payload, 6 + index * 14)
            size = (width or 256, height or 256)
            icon_data = icons.get(icon_id)
            if icon_data is None or len(icon_data) != length:
                raise RuntimeError(f"PPView.exe icon payload {icon_id} is missing or truncated")
            embedded[size] = icon_data
        if required_sizes.issubset(embedded):
            mismatches = [size for size, data in source_icons.items() if embedded.get(size) != data]
            if mismatches:
                raise RuntimeError(f"Packaged icon payloads differ from source ICO at sizes: {mismatches}")
            matched = True
            break
    if not matched:
        raise RuntimeError("PPView.exe does not embed all expected icon sizes and payloads")

    # Ask Windows' shell extractor as a second check that the resource is usable.
    shell32 = ctypes.windll.shell32
    extract = shell32.ExtractIconExW
    extract.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.HANDLE),
                        ctypes.POINTER(wintypes.HANDLE), wintypes.UINT]
    extract.restype = wintypes.UINT
    large, small = wintypes.HANDLE(), wintypes.HANDLE()
    if not extract(str(exe), 0, ctypes.byref(large), ctypes.byref(small), 1):
        raise RuntimeError("PPView.exe has no extractable Windows icon resource")
    destroy = user32.DestroyIcon
    destroy.argtypes = [wintypes.HANDLE]
    if large.value: destroy(large)
    if small.value: destroy(small)
    print(f"Verified {count} icon images embedded in PPView.exe from {ico_path.name}")


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
    sys.path.insert(0, str(root / "src"))
    from ppview import __version__
    exe = root / "dist" / "PPView" / "PPView.exe"
    if not exe.is_file():
        raise FileNotFoundError(exe)
    verify_executable_icon(exe)
    package = exe.parent
    build_info_path = package / "_internal" / "ppview-build.json"
    import json
    build_info = json.loads(build_info_path.read_text(encoding="utf-8"))
    source_commit = subprocess.run(["git", "-c", f"safe.directory={root.as_posix()}", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                                   text=True, check=True).stdout.strip()
    if build_info.get("version") != __version__ or build_info.get("commit") != source_commit:
        raise RuntimeError(f"Packaged EXE metadata does not match source: {build_info}")
    for required in ("_internal/pypdfium2_raw/pdfium.dll", "_internal/PySide6/Qt6Core.dll",
                     "_internal/PySide6/Qt6Gui.dll", "_internal/PySide6/Qt6Widgets.dll"):
        if not (package / required).is_file():
            raise FileNotFoundError(package / required)
    archive = root / "dist" / "PPView-windows-x64.zip"
    required_zip = {"PPView/PPView.exe", "PPView/_internal/pypdfium2_raw/pdfium.dll",
                    "PPView/_internal/PySide6/Qt6Core.dll", "PPView/_internal/PySide6/Qt6Gui.dll",
                    "PPView/_internal/PySide6/Qt6Widgets.dll", "PPView/_internal/ppview-build.json"}
    with zipfile.ZipFile(archive) as bundle:
        missing = required_zip - set(bundle.namelist())
        if missing:
            raise RuntimeError(f"Portable ZIP is missing required runtime files: {sorted(missing)}")
    with tempfile.TemporaryDirectory(prefix="ppview-packaged-") as folder:
        pdf = Path(folder) / "packaged-smoke.pdf"
        menu_capture = Path(folder) / "french-file-menu.png"
        window_capture = Path(folder) / "packaged-window.png"
        pdf.write_bytes(make_pdf(2))
        env = os.environ.copy()
        env["PATH"] = str(Path(os.environ["WINDIR"]) / "System32") + os.pathsep + str(Path(os.environ["WINDIR"]))
        env["PPVIEW_SMOKE_MENU_CAPTURE"] = str(menu_capture)
        env["PPVIEW_SMOKE_WINDOW_CAPTURE"] = str(window_capture)
        settings = QSettings("papagori", "PPView")
        had_language = settings.contains("language")
        saved_language = settings.value("language")
        settings.setValue("language", "fr")
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
            capture_deadline = time.monotonic() + 5
            while time.monotonic() < capture_deadline and not (menu_capture.is_file() and window_capture.is_file()):
                if process.poll() is not None:
                    raise RuntimeError("PPView closed before capturing the French File menu")
                time.sleep(0.1)
            if not menu_capture.is_file() or not window_capture.is_file():
                raise RuntimeError("Packaged app did not capture its open French File menu")
            capture_path = root / "dist" / "PPView-v0.1.5-fr-menu.png"
            screenshot = QImage(str(window_capture))
            menu_image = QImage(str(menu_capture))
            metadata = json.loads(menu_capture.with_suffix(".json").read_text(encoding="utf-8"))
            screenshot.setDevicePixelRatio(1)
            menu_image.setDevicePixelRatio(1)
            painter = QPainter(screenshot)
            painter.drawImage(metadata["x"], metadata["y"], menu_image)
            painter.end()
            if not screenshot.save(str(capture_path)):
                raise RuntimeError("Could not save combined packaged-app screenshot")
            safe_title = title.encode("ascii", "replace").decode("ascii")
            print(f"Packaged app opened and rendered the PDF ({blue_pixels} blue samples): {safe_title}")
            print("Portable ZIP contains PPView.exe, PDFium, and Qt Core/Gui/Widgets DLLs")
            print(f"French toolbar and File menu screenshot saved to {capture_path}")
        finally:
            if process.poll() is None:
                if hwnd:
                    PostMessageW(hwnd, WM_CLOSE, 0, 0)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=5)
            if had_language:
                settings.setValue("language", saved_language)
            else:
                settings.remove("language")


if __name__ == "__main__":
    main()
