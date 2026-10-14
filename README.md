# PPView

PPView 0.2.0 is a local desktop viewer for PDFs and Adobe Illustrator `.ai` files that contain PDF-compatible content. It renders pages with PDFium and reports a focused set of technical preflight observations. PPView does not edit or repair source files and is not a certified print-production validator.

**Source documents are never modified.** Files stay on the local computer; PPView has no account, telemetry, cloud processing, or upload feature.

## Preflight checks

The Information / Checks panel organizes findings into Document, Images, Fonts, Page Geometry, and Colors. Analysis runs in a worker thread while the preview remains usable. Selecting a page-specific finding navigates to that page. The PDF itself is not annotated; precise artwork highlighting is not provided in this version.

- **Document:** QPDF structure access, page count, page content-stream parsing, and PDFium rendering are reported separately. A failure in one content stream can leave the other available findings visible.
- **Images:** PPView follows image `Do` placements, including nested Form XObjects, and reports pixel dimensions, object reference, color space, bit depth, placement bounds, and effective PPI when the transformation is measurable. PPI uses the actual placement transform, including scale and rotation; a conservative principal scale is used for shear. Reused images are listed per placement. Inline image PPI is calculated when its placement can be established, though its stream decoding status may remain Unknown. Clipping geometry is not resolved, and image streams over 8 million pixels may be left undecoded to limit memory use. PPView can only inspect images present in the accessible PDF representation; it cannot know whether the designer intended additional photographs.
- **Resolution thresholds:** File > Preflight Settings offers 150, 200, or 300 PPI (default 300). An image below the selected threshold is a warning; below 150 PPI is marked high priority. These are user-selected guidelines, not universal printer requirements. A low-resolution image is not, by itself, evidence that a document is unprintable.
- **Fonts:** PDF font resources are inspected for referenced embedded programs, including composite CID fonts. Type 3 and unreadable structures may be Unknown. A program reference does not guarantee that every glyph will render as intended; successful text extraction is not proof of correct glyph appearance. Outlined artwork is not treated as a missing font.
- **Page geometry:** MediaBox, CropBox, TrimBox, BleedBox, and ArtBox dimensions are reported in millimeters when valid. Document size (MediaBox) and intended trimmed size (TrimBox) can differ. The 0, 2, 3, or 5 mm bleed setting (default 3 mm) compares explicit TrimBox and BleedBox geometry only. It does not establish that visible artwork extends to the bleed edge. Missing or ambiguous box data is Unknown, not proof of missing bleed.
- **Colors:** Basic DeviceGray, DeviceRGB, DeviceCMYK, ICCBased, and other recognized color-space names are reported where encountered. PPView does not convert colors or validate the printer's color-management pipeline, ICC profile accuracy, spot colors, DeviceN, transparency, or overprint behavior. RGB is not automatically an error.
- **Unknown:** A result is Unknown when a structure, image decode, transformation, or color space cannot be established reliably. Unknown is never silently counted as Passed.

Successful opening or previewing does not guarantee print readiness. Complex transparency, spot colors, overprint, image clipping, detailed issue highlighting, and printer-specific profiles remain out of scope. Illustrator compatibility refers only to the PDF representation embedded in an `.ai` file; that representation may differ from the editable Illustrator document, and a PDF page is not necessarily one artboard.

## Use

Open files with drag-and-drop, **File > Open Files** / **Ctrl+O**, or the integrated Browser. The Information / Checks panel displays document information and findings. Use the toolbar to fit, zoom, pan, and navigate pages; multiple documents can remain open. English, Japanese, and French switch immediately and the selected language is saved.

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

The generated fixtures cover image scaling and rotation, form placements, font resources, page boxes, and common color spaces. They are synthetic PDFs and do not claim full Adobe Illustrator compatibility.

## Build the portable Windows executable

On Windows with Python 3.11 installed:

```powershell
./scripts/build_windows.ps1
```

The script recreates the project `.venv`, runs tests and smoke checks, builds `dist/PPView/` and `dist/PPView-windows-x64.zip`, verifies the packaged icon and preflight dependencies, then launches the packaged EXE with a generated PDF. GitHub Actions performs the same Windows x64 build on pushes to `main` and `feature/**`, pull requests, and manual runs. The package includes dependency license notices.

## PDFium diagnostic

On this Windows development machine, enabling Python's `faulthandler` prints a `Windows fatal exception: access violation` stack at `FPDF_InitLibraryWithConfig` during pypdfium2 import. The same process continues, reports PDFium initialized, and passes the standalone render smoke check; ordinary import without faulthandler is quiet. This native first-chance/handled exception has not yet been traced to its upstream cause. It remains under investigation and must be rechecked before any public release.

## License and dependencies

PPView is licensed under GNU GPLv3; see [LICENSE](LICENSE). The PDF structure inspector uses pikepdf (MPL-2.0) and its QPDF runtime (Apache-2.0). See [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md), included dependency license files, and [LGPLv3](LICENSES/LGPL-3.0.txt) for notices.

## Languages

[Français](README.fr.md) · [日本語](README.ja.md)
