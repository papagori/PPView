"""Copy upstream dependency license payloads into a PyInstaller distribution."""
from importlib.metadata import distributions
from pathlib import Path
import shutil
import sys

destination = Path(sys.argv[1]) / "_internal" / "licenses"
destination.mkdir(parents=True, exist_ok=True)
for dist in distributions():
    name = (dist.metadata.get("Name") or "dependency").lower().replace(" ", "-")
    license_files = [p for p in (dist.files or ()) if "licenses" in p.parts]
    for rel in license_files:
        source = Path(dist.locate_file(rel))
        if not source.is_file() or "__pycache__" in rel.parts:
            continue
        filename = source.name.lower()
        legal_name = any(token in filename for token in ("license", "licence", "notice", "copyright", "copying"))
        if not legal_name and source.suffix.lower() not in {".txt", ".md", ".html", ".rst"}:
            continue
        target = destination / name / Path(*rel.parts[rel.parts.index("licenses") + 1:])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    target = destination / "python" / "LICENSE.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(python_license, target)
