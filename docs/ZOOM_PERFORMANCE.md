# PPView v0.2.3 zoom performance notes

## Rendering decisions

Wheel and toolbar zoom now resize the last completed PDFium image immediately with Qt's fast transform. The displayed zoom value and scroll anchor update in the same event. The temporary image can be soft; a 150 ms single-shot timer submits the final PDFium render after input pauses.

There is at most one page-render task in flight from the preview. If another request arrives, its serial invalidates the old result and the latest view state replaces pending work. The native PDFium call is allowed to finish; it is never forcibly interrupted. Preview tasks enter the shared Qt pool at higher priority than background analysis. Page changes and document switches invalidate old serials.

The source byte cache is a 96 MiB LRU keyed by canonical path, modification time, size, and change time. Files larger than the cap are read without retaining them. Closing a document releases its cached bytes. PDFium document and page objects remain per-render and are closed before the detached QImage is handed to Qt; this avoids unsafe cross-thread native object reuse. There is no rendered-bitmap cache.

The largest PDFium bitmap is 16 million pixels and each side is limited to 16,384 pixels. The estimated scale is reduced before allocation if either limit would be exceeded. PPView identifies this reduced-resolution result in the preview tooltip and Rendering status. The bound limits raw RGB image storage to about 48 MB; PDFium's native bitmap and the detached Qt copy add transient memory overhead. Only one preview render runs at a time.

## Reproduce the measurements

Run on Windows with the project environment:

```powershell
python scripts/zoom_benchmark.py --output dist/zoom-benchmark.json
```

The script generates a one-path PDF, a 12,000-path vector PDF, and a 28,809,453-byte PDF with a 3000 × 3200 RGB image. It compares the v0.2.2 render implementation (read bytes, open PDFium, render, detach image, close) with the v0.2.3 cached-byte implementation. Cold inspect-plus-render comparisons clear the new source cache before each sample and reproduce the uncached v0.2.2 inspection read. The script reports seven-run medians (five for the large raster), a 12-event real Qt zoom burst, final render completion, and process working-set counters. Results depend on CPU, filesystem cache, PDFium, and Qt versions. The process-wide peak includes Qt, fixture generation, and all benchmark cases; it is not a per-document allocation figure.

## Local measurement, 2026-10-15

| Synthetic fixture | Size | v0.2.2 render median | v0.2.3 cached render median | Cold inspect + render, v0.2.2 → v0.2.3 |
|---|---:|---:|---:|---:|
| Small vector | 472 B | 4.20 ms | 4.66 ms | 4.49 → 5.75 ms |
| Complex vector | 398,257 B | 185.32 ms | 140.50 ms | 145.33 → 153.82 ms |
| Large embedded raster | 28,809,453 B | 61.16 ms | 44.96 ms | 80.75 → 62.65 ms |

For both vector fixtures, 12 rapid wheel events started one PDFium render, eliminating 11 render starts relative to v0.2.2's immediate per-event submission. Median zoom-handler time was 0.078 ms for both fixtures. The complete final update was observed at 216.57 ms and 959.66 ms respectively, including debounce and event-loop scheduling. The complex burst reached the render pixel cap at its final zoom; that result was visibly marked as reduced resolution. The standalone 170% medians above stayed below the cap and used the requested render scale.

Windows working set after all benchmark cases was 121.8 MiB with a process peak of 232.5 MiB. This is a whole-process measurement, not a clean isolated high-water mark for the 28.8 MB file. Adjacent benchmark runs varied, and the tiny and complex fixture cold timings did not consistently improve; these figures are diagnostic rather than a statistically significant speed claim. The principal responsiveness gain comes from returning immediately with a scaled image and avoiding redundant render submissions. The real 29 MB Illustrator brochure mentioned in user testing was not present here, so its performance has not been independently benchmarked.

## Reliability coverage

Automated tests cover cache hit/change invalidation, a synthetic over-limit fallback, immediate preview scaling, anchor math, debounce coalescing state, stale pending renders, document switching, and closing while a render is active. UI smoke tests still render multiple PDF pages. Genuine Illustrator performance and exact clipping alignment should be checked with the manual real-document procedure in `REAL_AI_VALIDATION.md`.
