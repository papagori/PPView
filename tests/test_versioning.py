import json
import re
import sys

from ppview import __display_version__, __version__, __windows_version_info__


def test_beta_version_forms_are_consistent():
    assert re.fullmatch(r"\d+\.\d+\.\d+b\d+", __version__)
    assert __version__ == "0.3.0b1"
    assert __display_version__ == "0.3.0-beta.1"
    assert __windows_version_info__ == (0, 3, 0, 1)


def test_build_metadata_keeps_package_display_and_windows_versions(tmp_path, monkeypatch):
    from scripts import write_build_info

    output = tmp_path / "ppview-build.json"
    monkeypatch.setattr(sys, "argv", ["write_build_info.py", str(output)])
    write_build_info.main()

    metadata = json.loads(output.read_text(encoding="utf-8"))
    assert metadata["version"] == __version__
    assert metadata["display_version"] == __display_version__
    assert metadata["commit"]

    installer = (write_build_info.ROOT / "installer" / "version.iss").read_text(encoding="utf-8")
    assert f'AppVersion "{__display_version__}"' in installer
    assert 'AppNumericVersion "0.3.0.1"' in installer

    windows = (write_build_info.ROOT / "build" / "version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(0, 3, 0, 1), prodvers=(0, 3, 0, 1)" in windows
    assert f"StringStruct('ProductVersion', '{__display_version__}')" in windows
