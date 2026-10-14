# PPView

PPView 0.1.2 is a lightweight, local desktop utility for previewing PDF and PDF-compatible Adobe Illustrator files before sending them to a commercial printer. It renders the accessible PDF page content with PDFium and helps you spot missing or misplaced visible content. PPView is a preview utility, not a PDF/Illustrator editor or professional preflight application.

**Nothing in PPView modifies the source document.** All processing is local; the application has no account, telemetry, cloud processing, or upload feature.

## Screenshots

Screenshots will be added when captures from the working application are available.

## Supported files and limitations

- PDF documents, detected and opened from their content.
- Adobe Illustrator `.ai` files when they contain usable PDF-compatible content. PPView renders actual pages through PDFium, never an embedded thumbnail.
- AI files without usable PDF-compatible content cannot be previewed. PPView does not parse the proprietary Illustrator format.
- An AI file's PDF representation can differ from its editable Illustrator document. A PDF page is not necessarily one Illustrator artboard.
- Opening and rendering successfully does not show that a document is print ready. v0.1 checks basic access, page dimensions, and whether pages render. Advanced preflight checks are planned for v0.2.

## Use

Open PPView, drag one or more PDF or AI files anywhere in the window, or choose **File > Open Files** / press **Ctrl+O** to select multiple files. New files are appended, duplicate canonical paths are ignored, and the newest file becomes active. Use **File > Open Folder** to browse from a directory, or show the hidden-by-default **File Browser** sidebar to browse local drives and folders. Select multiple files there and choose **Open Selected Files**. The last browsed directory is remembered. Switch documents from the toolbar selector; use **Close Document** or **Clear All** to remove documents. Fit Page is applied when a document opens. Drag with the left or middle mouse button to pan; ordinary wheel scrolls, and Ctrl+wheel zooms around the pointer. Double-click the preview to fit the page. The zoom percentage appears beside the zoom controls. The Information panel separates document details from basic rendering checks; these do not establish print-production compliance. Choose English or Japanese in the panel; the choice is saved. The initial language follows Windows when no saved selection exists. The footer links to the author website, GitHub repository, and GPLv3 license.

You may also pass a file path when launching `PPView.exe`.

## Run from source

Requires Python 3.10 or later. The reproducible Windows build environment uses 64-bit CPython 3.11.5 with the exact packages in `requirements-lock.txt` (PySide6 6.11.0, pypdfium2/PDFium 5.14.0, pytest 8.4.2, PyInstaller 6.22.3).

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m ppview.main
```

## Tests

```powershell
python -m pytest
```

Tests generate small reproducible PDFs locally and use a renamed PDF as an AI-compatible-content fixture; this does not claim validation against genuine Illustrator documents.

## Build the portable Windows executable

On Windows with Python 3.11 installed:

```powershell
./scripts/build_windows.ps1
```

The script recreates the project `.venv`, installs the pinned dependencies, runs pytest and the PDFium open/render/close smoke check, builds the folder distribution at `dist/PPView/` plus `dist/PPView-windows-x64.zip`, then launches the packaged app with a generated PDF and checks the rendered fixture artwork and bundled Qt/PDFium files. GitHub Actions runs tests and creates the same Windows x64 package on pushes to `main`, pull requests, and manual runs; download it from the workflow run's Artifacts section. The package includes the GPL and third-party notices. No Python installation is required to run the packaged application.

## License and dependencies

PPView is licensed under GNU GPLv3; see [LICENSE](LICENSE). The GUI uses PySide6, rendering uses pypdfium2/PDFium, tests use pytest, and Windows packaging uses PyInstaller. See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) and [LICENSES/LGPL-3.0.txt](LICENSES/LGPL-3.0.txt) for dependency notices and Qt's LGPL text. The source install does not download or contact a service at runtime.

## 日本語

日本語の説明は [README.ja.md](README.ja.md) を参照してください。
