"""Install, upgrade, launch, and uninstall the generated Inno Setup package."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from PySide6.QtCore import QSettings

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from conftest import make_pdf  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def process_ids() -> set[int]:
    result = subprocess.run(["powershell", "-NoProfile", "-Command",
                             "@(Get-Process PPView -ErrorAction SilentlyContinue | ForEach-Object Id) -join ','"],
                            capture_output=True, text=True, check=True)
    return {int(value) for value in result.stdout.strip().split(",") if value.strip()}


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Installer smoke test requires Windows.")
    root = Path(__file__).resolve().parents[1]
    from ppview import __version__

    setup = root / "dist" / f"PPView-Setup-v{__version__}-x64.exe"
    require(setup.is_file(), f"Installer is missing: {setup}")
    settings = QSettings("papagori", "PPView")
    previous_had_language = settings.contains("language")
    previous_language = settings.value("language")
    settings.setValue("language", previous_language or "fr")
    language_to_preserve = settings.value("language")

    test_root = Path(tempfile.mkdtemp(prefix="ppview-installer-smoke-"))
    install_dir = test_root / "PPView"
    start_menu = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "PPView.lnk"
    desktop = Path(os.environ["USERPROFILE"]) / "Desktop" / "PPView.lnk"
    app_process = None
    try:
        args = [str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                f"/DIR={install_dir}", "/TASKS=desktopicon"]
        subprocess.run(args, check=True, timeout=180)
        exe = install_dir / "PPView.exe"
        require(exe.is_file(), "Fresh installation did not place PPView.exe")
        require(start_menu.is_file(), "Start Menu shortcut was not created")
        require(desktop.is_file(), "Selected desktop shortcut was not created")

        # Launch through the actual Start Menu shortcut and verify a new app process.
        before = process_ids()
        os.startfile(str(start_menu))
        deadline = time.monotonic() + 30
        launched = set()
        while time.monotonic() < deadline:
            launched = process_ids() - before
            if launched:
                break
            time.sleep(0.25)
        require(bool(launched), "Start Menu shortcut did not launch PPView")
        subprocess.run(["taskkill", "/PID", str(next(iter(launched))), "/T", "/F"],
                       capture_output=True, check=False)

        # Test the installed executable with a document, then close it cleanly.
        pdf = test_root / "installer-smoke.pdf"
        pdf.write_bytes(make_pdf(2))
        app_process = subprocess.Popen([str(exe), str(pdf)], cwd=install_dir)
        time.sleep(4)
        require(app_process.poll() is None, "Installed app exited while opening the smoke PDF")

        # Run setup over the same installation directory to exercise upgrade behavior.
        app_process.terminate()
        app_process.wait(timeout=10)
        subprocess.run(args, check=True, timeout=180)
        require(exe.is_file(), "Reinstallation removed the application")
        settings.sync()
        require(settings.value("language") == language_to_preserve,
                "Upgrade changed the stored application language preference")

        uninstaller = next(install_dir.glob("unins*.exe"), None)
        require(uninstaller is not None, "No standard Inno Setup uninstaller was registered")
        subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                       check=True, timeout=180)
        require(not exe.exists(), "Uninstallation left PPView.exe installed")
        settings.sync()
        require(settings.value("language") == language_to_preserve,
                "Uninstallation removed or changed the application language preference")
        print("Installer smoke passed: fresh install, Start Menu launch, desktop shortcut, "
              "document launch, same-directory reinstall, uninstall, and language preference retention")
    finally:
        if app_process and app_process.poll() is None:
            app_process.terminate()
            try:
                app_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app_process.kill()
        if previous_had_language:
            settings.setValue("language", previous_language)
        else:
            settings.remove("language")
        settings.sync()
        shutil.rmtree(test_root, ignore_errors=True)


if __name__ == "__main__":
    main()
