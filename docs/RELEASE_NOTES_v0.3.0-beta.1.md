# PPView v0.3.0-beta.1

First external beta candidate. This is a feature-frozen quality and packaging update, not a claim of universal Illustrator compatibility.

## Changes since v0.1.5

- Added a focused PDF preflight panel with separate Passed, Warning, Error, and Unknown results.
- Expanded image inspection to distinguish unique image objects from placements and report measured dimensions, effective PPI, stream availability, and decoding state where available.
- Added image placement highlighting, font embedding observations, page-box/bleed geometry, and basic color-space reporting.
- Improved zoom interaction with immediate temporary scaling, debounced final PDFium rendering, bounded caches, and render-size limits.
- Added translated offline User Guide and About dialogs, plus a per-user Windows installer and portable distribution.
- Refined the approved gradient branding and compact footer links.
- Added stability diagnostics, repeatable fixtures, packaging checks, and a beta feedback checklist.

## Scope and limits

PPView inspects the accessible PDF representation in a PDF or PDF-compatible `.ai` file. It does not read proprietary Illustrator structures, confirm native Illustrator image-link status, or certify printer-specific output. Some structures may be reported as Unknown. Image outlines are approximate and do not resolve all clipping paths. The installer is unsigned; SmartScreen may warn about an unfamiliar publisher. Keep private documents local and do not attach them to a bug report.

Python package metadata uses PEP 440 `0.3.0b1`; the application and distribution filenames display `0.3.0-beta.1`.
