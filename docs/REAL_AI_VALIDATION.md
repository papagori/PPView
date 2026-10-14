# Real Illustrator document validation

Use genuine PDF-compatible `.ai` files saved by Adobe Illustrator. Do not rename a `.pdf` file to `.ai`; that only tests extension handling. Keep private files on the local computer. PPView has no upload workflow, and these checks do not require sending documents to anyone.

No genuine Illustrator documents were available during this development run, so this checklist records a repeatable local procedure and does not claim real-file compatibility results.

## Procedure

1. Copy a representative `.ai` file to a local test folder and open it from PPView. Keep the original unchanged.
2. Repeat with one small file and one large or complex file. Include examples with Japanese and Latin text, placed images, vector artwork, transparency, clipping masks, and multiple artboards where available.
3. Switch the interface through English, Japanese, and French. Reopen the document after changing languages.
4. Use the checklist below. Record the PPView version, Windows version, approximate file size, and any observed error. Do not include private artwork in a report unless you choose to share it.
5. Close and reopen each file, then switch between two open documents while analysis is running. Confirm the displayed findings belong to the selected document.

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
