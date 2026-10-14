# PPView

PPView 0.1.4 is a lightweight, local desktop utility for previewing PDF and PDF-compatible Adobe Illustrator files before sending them to a commercial printer. It renders the accessible PDF page content with PDFium and helps you spot missing or misplaced visible content. PPView is a preview utility, not a PDF/Illustrator editor or professional preflight application.

**Nothing in PPView modifies the source document.** All processing is local; the application has no account, telemetry, cloud processing, or upload feature.

## Screenshots

![PPView 0.1.4 running on Windows with a rendered two-page PDF](assets/screenshots/PPView-v0.1.4.png)

This screenshot was captured from the packaged Windows executable using a local test PDF.

## Branding

The header uses the icon-only document inspection mark with the localized application title and subtitle. The vector lockup, icon, splash preview, and multi-resolution Windows icon are in [`assets/logo`](assets/logo). PNG previews are included there for review. `scripts/generate_logo_assets.py` regenerates the previews and `ppview.ico` from the SVG artwork; the Windows build embeds that ICO in `PPView.exe` and bundles the SVG used by the app window and header.

## Supported files and limitations

- PDF documents, detected and opened from their content.
- Adobe Illustrator `.ai` files when they contain usable PDF-compatible content. PPView renders actual pages through PDFium, never an embedded thumbnail.
- AI files without usable PDF-compatible content cannot be previewed. PPView does not parse the proprietary Illustrator format.
- An AI file's PDF representation can differ from its editable Illustrator document. A PDF page is not necessarily one Illustrator artboard.
- Opening and rendering successfully does not show that a document is print ready. v0.1 checks basic access, page dimensions, and whether pages render. Advanced preflight checks are planned for v0.2.

## Use

Open PPView, drag one or more PDF or AI files anywhere in the window, or choose **File > Open Files** / press **Ctrl+O** to select multiple files. New files are appended, duplicate canonical paths are ignored, and the newest file becomes active. Use **File > Open Folder** to browse from a directory, or show the hidden-by-default **Browser** sidebar to browse local drives and folders. Select multiple files there and choose **Open Selected Files**. The browser starts with collapsed local and connected drive roots, uses lazy filesystem loading, and remembers the last browsed directory and preferred sidebar width. Switch documents from the toolbar selector; use **Close Document** or **Clear All** to remove documents. Fit Page is applied when a document opens. Drag with the left or middle mouse button to pan; ordinary wheel scrolls, and Ctrl+wheel zooms around the pointer. Double-click the preview to fit the page. Enter a zoom percentage directly, use the compact slider, or scroll over the zoom control. The toolbar provides Fit Page, Fit Width, Zoom Out, Zoom In, and page navigation. The Information panel separates document details from basic rendering checks; these do not establish print-production compliance. Choose English, Japanese, or French from the toolbar language selector; the choice is saved, with the Windows language used on first launch when supported. The initial language follows Windows when no saved selection exists. The footer links to the author website, GitHub repository, and GPLv3 license.

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

日本語の詳細は [README.ja.md](README.ja.md) を参照してください。フランス語の説明は [README.fr.md](README.fr.md) にあります。

日本語の説明は [README.ja.md](README.ja.md) を参照してください。


## Languages and appearance

PPView provides English, Japanese, and French UI translations, with instant switching from the toolbar. The application uses a high-contrast navy and blue theme and includes a compact PPView SVG mark. Its Windows application and executable icon is generated from the original SVG at multiple resolutions.
