# Third-party notices

PPView is distributed under GNU GPL version 3 or later. The Windows package bundles the following components; their notices and license texts are included here for convenience. The actual versions bundled are the versions selected by `pyproject.toml` and the lock-free build at build time.

| Component | License | Use |
|---|---|---|
| Python | PSF License | Runtime |
| PySide6 / Qt for Python | LGPLv3 / GPLv3 / commercial dual licensing | Desktop GUI |
| Qt libraries | LGPLv3 (with module-specific notices) | GUI runtime |
| pypdfium2 | Apache-2.0 | Python bindings |
| PDFium | BSD-3-Clause and third-party notices | PDF parsing/rendering |
| PyInstaller | GPLv2-or-later with bootloader exception | Executable packaging; not required to run from source |

The complete GNU LGPLv3 text is included at [LICENSES/LGPL-3.0.txt](LICENSES/LGPL-3.0.txt). PDFium contains additional third-party code; the matching pypdfium2 license texts are copied from the installed distribution and included alongside the bundled PDFium binary. PySide6/Qt obligations vary by deployment and module; the package contains Qt license references and the LGPLv3 text. Preserve the distributed licenses and notices with the application. No dependency is used under AGPL.
