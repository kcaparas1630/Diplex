# ADR 015: Page Images Come in One Size

> Status: **Accepted** · 2026-11-10

## Context

- **[ADR 001](001-architecture.md) §7 left open** whether the engine should return a thumbnail with each page image.
- **Page images are small already:** WebP at 144 DPI, median 70 KB a page on the samples, lossless smaller than lossy on 90% of pages ([ADR 001](001-architecture.md) §4).
- **Encoding is the engine's slowest step after conversion,** and it runs one document at a time under the PDFium lock; a second size would add a resize and an encode per page.
- **Viewers lay pages out from their sizes and load them as the user scrolls,** about 10 at a time ([ADR 001](001-architecture.md) §5), so a page's image is only fetched when it is about to be seen. Browsers scale an image to its box.
- **Every response holds all its images in memory** on the consumer's side ([ADR 010](010-render-response-format.md)), so more parts make every render bigger.

## Decision

- **One size: each page at 144 DPI, as now.** The response format does not change.
- **Viewers show the same image at any size,** scaled by the browser; the playground's viewer does.
- **A consumer that needs thumbnails makes them from the stored page images,** on its own server, when it needs them.

## Consequences

- **No extra encode time, response size or contract change.**
- **A grid of many small pages downloads full-size images** (about 70 KB each), which a viewer loading in batches keeps to the pages on screen.
- **Thumbnails can still come later without a new API version,** as an extra optional part that old consumers ignore ([ADR 012](012-api-key-and-version.md)).
