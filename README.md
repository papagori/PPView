# PPView

PPView 0.2.4 is an independent local desktop viewer for PDFs and Adobe Illustrator `.ai` files that contain PDF-compatible content. It requires no Adobe application, service, account, or scripting API. It renders pages with PDFium and reports a focused set of technical preflight observations. PPView does not edit or repair source files and is not a certified print-production validator.

**Source documents are never modified.** Files stay on the local computer; PPView has no account, telemetry, cloud processing, or upload feature.

## Preflight checks

The Information / Checks panel organizes findings into Document, Images, Fonts, Page Geometry, and Colors. Analysis runs in a worker thread while the preview remains usable. Selecting an image placement navigates to its page and temporarily outlines its approximate placement when coordinates are reliable. The source PDF is never annotated.

- **Document:** QPDF structure access, page count, page content-stream parsing, and PDFium rendering are reported separately. A failure in one content stream can leave the other available findings visible.
- **Images:** PPView follows image `Do` placements, including nested Form XObjects, and reports pixel dimensions, object reference, color space, bit depth, placement dimensions, horizontal and vertical PPI, and effective PPI when measurable. PPI uses the placement transform, including scale and rotation; a conservative principal scale is used for shear. The panel distinguishes unique PDF image objects from placements; one object reused twice counts as one object and two placements. Internal stream availability and decode status are separate. Decode can be verified, failed, skipped for memory limits, or unknown. A successful page render does not imply every image stream decoded successfully. A PDF external-file reference is reported as a possible dependency. A temporary outline shows the approximate transformed placement bounds; clipping paths are not resolved, so it is not a verified visible boundary.
- **Illustrator files:** PPView inspects only the accessible PDF-compatible representation. It does not read Illustrator's private native structures. PDF image data availability does not prove that an image is embedded rather than linked in the native Illustrator document; that status is always unverified.
- **Resolution thresholds:** File > Preflight Settings offers 150, 200, or 300 PPI (default 300). An image below the selected threshold is a warning; below 150 PPI is marked high priority. These are user-selected guidelines, not universal printer requirements. A low-resolution image is not, by itself, evidence that a document is unprintable.
- **Fonts:** PDF font resources are inspected for referenced embedded programs, including composite CID fonts. Type 3 and unreadable structures may be Unknown. A program reference does not guarantee that every glyph will render as intended; successful text extraction is not proof of correct glyph appearance. Outlined artwork is not treated as a missing font.
- **Page geometry:** MediaBox, CropBox, TrimBox, BleedBox, and ArtBox dimensions are reported in millimeters when valid. Document size (MediaBox) and intended trimmed size (TrimBox) can differ. The 0, 2, 3, or 5 mm bleed setting (default 3 mm) compares explicit TrimBox and BleedBox geometry only. It does not establish that visible artwork extends to the bleed edge. Missing or ambiguous box data is Unknown, not proof of missing bleed.
- **Colors:** Basic DeviceGray, DeviceRGB, DeviceCMYK, ICCBased, and other recognized color-space names are reported where encountered. PPView does not convert colors or validate the printer's color-management pipeline, ICC profile accuracy, spot colors, DeviceN, transparency, or overprint behavior. RGB is not automatically an error.
- **Unknown:** A result is Unknown when a structure, image decode, transformation, or color space cannot be established reliably. Unknown is never silently counted as Passed.

Successful opening or previewing does not guarantee print readiness. Complex transparency, spot colors, overprint, image clipping, and printer-specific profiles remain out of scope. Illustrator compatibility refers only to the PDF representation embedded in an `.ai` file; that representation may differ from the editable Illustrator document, and a PDF page is not necessarily one artboard.

## Use

Open files with drag-and-drop, **File > Open Files** / **Ctrl+O**, or the integrated Browser. The Information / Checks panel displays document information and findings. Use the toolbar to fit, zoom, pan, and navigate pages; multiple documents can remain open. English, Japanese, and French switch immediately and the selected language is saved.

## Offline help and zoom behavior

The Help menu contains a translated User Guide and About PPView dialog in English, Japanese, and French. The guide explains document opening, preview controls, preflight statuses, and limits without an Internet connection. During zoom, PPView immediately scales the last PDFium image for interaction; after a 150 ms pause it renders the selected page again with PDFium. The temporary image can look soft until the final render completes. A 96 MiB source-byte cache is shared by path and file timestamp and is released when the document closes. PDFium bitmaps are limited to 16 million pixels and 16,384 pixels per side; a reduced-resolution result is explicitly identified. PDFium documents are still opened and closed per render to avoid sharing native objects across threads.

## Screenshots and branding

The main window and icon assets are in [`assets/logo`](assets/logo). The Windows build embeds the multi-size ICO and uses the SVG mark in the app window. Test screenshots are generated from local PDFs; they do not represent tests of genuine Illustrator files.

## Run from source

Requires Python 3.11 or later. The reproducible Windows build uses 64-bit CPython 3.11.5 and the versions pinned in `requirements-lock.txt` (PySide6, pypdfium2/PDFium, pikepdf/QPDF, and PyInstaller).

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

Run `python scripts/zoom_benchmark.py --output dist/zoom-benchmark.json` for repeatable synthetic small and complex PDF measurements comparing the v0.2.2 rendering path with the cached v0.2.3 path. It reports median render/open timings, zoom handler response, actual render count, and Windows working set. It does not represent performance on the user’s 29 MB Illustrator brochure.

The generated fixtures cover image scaling and rotation, form placements, font resources, page boxes, and common color spaces. They are synthetic PDFs and do not claim full Adobe Illustrator compatibility.

## Install or use the portable Windows build

For a per-user installation on Windows 10 or 11 x64, run `PPView-Setup-v0.2.4-x64.exe`. Choose an installation folder, select an installer language (English, Japanese, or French), and optionally enable the desktop shortcut. The installer creates a Start Menu shortcut and a standard Windows uninstall entry. It does not change `.ai` or `.pdf` file associations. Uninstall from **Settings > Apps > Installed apps** or the Start Menu; PPView preferences remain in the user profile.

The installer is unsigned. Windows SmartScreen may warn that the software is unfamiliar. Verify the SHA-256 checksum file distributed beside the installer before running it.

The portable package is `PPView-Portable-v0.2.4-x64.zip`. Extract the folder anywhere writable and run `PPView/PPView.exe`; no installation or Python runtime is required. Preferences continue to be stored in the current Windows user profile.

For the genuine Illustrator document checklist, see [Real AI validation](docs/REAL_AI_VALIDATION.md).

## Build Windows distributions from source

On Windows with Python 3.11 installed:

```powershell
./scripts/build_windows.ps1
```

The script recreates the project `.venv`, runs tests and smoke checks, builds the portable ZIP and Inno Setup installer from the same one-folder app build, verifies the package, and runs install/upgrade/uninstall smoke checks. GitHub Actions stores the ZIP, installer, and SHA-256 checksums as workflow artifacts; it does not publish a release.

## PDFium diagnostic

Run `python scripts/pdfium_diagnostics.py` to repeat the isolated import, pytest, faulthandler, and rendering comparisons. Current local evidence and limits are recorded in [PDFium investigation](docs/PDFIUM_INVESTIGATION.md). The exception remains under investigation and must be rechecked on a clean Windows machine before a public beta.


See [Zoom performance](docs/ZOOM_PERFORMANCE.md) for implementation decisions and reproducible synthetic measurements.

## License and dependencies

PPView is licensed under GNU GPLv3; see [LICENSE](LICENSE). The PDF structure inspector uses pikepdf (MPL-2.0) and its QPDF runtime (Apache-2.0). See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md), included dependency license files, and [LGPLv3](LICENSES/LGPL-3.0.txt) for notices.

## Languages

[Français](README.fr.md) · [日本語](README.ja.md)
