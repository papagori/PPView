"""PPView: local PDF and PDF-compatible Illustrator previewer."""
import re

# PEP 440 form is the single source used by Python package metadata.
__version__ = "0.3.0b1"
_version_match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:b(\d+))?", __version__)
if _version_match is None:  # pragma: no cover - protects release packaging
    raise RuntimeError(f"Unsupported PPView release version: {__version__}")
_major, _minor, _patch, _beta = _version_match.groups()
__display_version__ = (f"{_major}.{_minor}.{_patch}-beta.{_beta}" if _beta
                       else f"{_major}.{_minor}.{_patch}")
__windows_version_info__ = (int(_major), int(_minor), int(_patch), int(_beta or 0))
