# PPView 0.3.0-beta.2: tester checklist

This beta is for feedback on PPView's local preview and preflight workflow. It reads the PDF-compatible representation in PDFs and `.ai` files; it does not inspect Illustrator's private editable structures, validate native image links, or certify print production.

## Try these tasks

1. Install `PPView-Setup-v0.3.0-beta.2-x64.exe`, launch from Start, close and reopen PPView. Optionally test the portable ZIP from an extracted folder.
2. Open a small PDF-compatible Illustrator file and one large photographic file. Use copies if you want to avoid touching originals; PPView does not edit them.
3. Check a document with Japanese text, and one with both vector artwork and raster images. If available, try a multipage PDF or an Illustrator file with multiple artboards.
4. Compare visible text, photographs, graphics, and page order with the source application. Report differences you can see; do not assume a preview proves print readiness.
5. Try Fit Page, Fit Width, zoom in/out, mouse-wheel zoom, panning, page navigation, and image placement highlighting. Note if the preview jumps, goes blank, or feels unresponsive.
6. Read image PPI, image object/placement counts, font embedding, page-box and color findings. Note any warning or Unknown result that is hard to understand.
7. Open more than one document, switch between them while checks are running, close documents, and repeat. Note crashes, errors, or unusual memory growth.

## Report a problem

Use [GitHub Issues](https://github.com/papagori/PPView/issues) and include:

- PPView version (`0.3.0-beta.2`) and Windows version.
- What you were doing and what happened.
- Steps to reproduce.
- Expected result and actual result.
- An optional screenshot with private artwork removed or obscured.

Do not upload or attach proprietary, confidential, or customer documents. A description, screenshot, and approximate file size are usually enough to start. Do not disable antivirus or Windows security features to test PPView.
