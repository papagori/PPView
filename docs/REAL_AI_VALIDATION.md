# Real Illustrator document validation

Use genuine PDF-compatible `.ai` files saved by Adobe Illustrator. Do not rename a `.pdf` file to `.ai`; that only tests extension handling. Keep private files on the local computer. PPView has no upload workflow, and these checks do not require sending documents to anyone.

The project owner has reported successful use with genuine PDF-compatible Illustrator documents, including a Japanese brochure. That experience is useful real-world feedback but does not establish universal Illustrator compatibility. This checklist supports further local testing; it does not claim that every example below was retested for this beta.

## Procedure

1. Copy a representative `.ai` file to a local test folder and open it from PPView. Keep the original unchanged.
2. Try a small Illustrator document and a large photographic Illustrator document.
3. Try a document containing Japanese text and one combining vector artwork with raster images.
4. If available, try a multipage PDF and an Illustrator file with multiple artboards. PDF pages and Illustrator artboards need not correspond one-to-one.
5. Switch the interface through English, Japanese, and French. Reopen the document after changing languages.
6. Use the checklist below. Record the PPView version, Windows version, approximate file size, and any observed error. Do not include private artwork in a report.
7. Close and reopen each file, then switch between two open documents while analysis is running. Confirm the displayed findings belong to the selected document.

## Checklist

- [ ] Preview opens and visible raster and vector artwork appears in the expected page order.
- [ ] Japanese and Latin text are legible; note any missing glyphs or font substitution.
- [ ] Image placements and unique image-object counts are plausible. Reused images may have multiple placements.
- [ ] Horizontal, vertical, and effective PPI values are plausible at the displayed placement size. Treat thresholds as configurable guidance, not universal print requirements.
- [ ] Font findings distinguish embedded PDF font programs, non-embedded programs, and Unknown. Outlined text does not require a font resource.
- [ ] Page dimensions match the PDF-compatible representation. Illustrator artboards and PDF pages need not correspond one-to-one.
- [ ] Selecting an image finding highlights its approximate placement. Clipping paths are not resolved, so the outline may include clipped-away areas.
- [ ] Review warnings and Unknown values. A PDF image does not confirm whether the native Illustrator file has a valid link or an embedded original.
- [ ] Exercise zoom, page navigation, document switching, and repeated open/close. Watch for a crash, blank page, stale findings, or increasing memory use.
- [ ] On large documents, note startup time, first-page render time, analysis time, responsiveness, and peak memory if observable.

Record any difference between the preview and Illustrator separately from preflight observations. PPView reads the accessible PDF-compatible representation and does not certify the editable Illustrator document or print output.
