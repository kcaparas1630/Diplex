# ADR 010: The Render Response Is multipart/form-data

> Status: **Accepted** · 2026-11-03

## Context

- **`/render` returns several files at once:** for every upload, one image per page (about 7 MB per 100 pages) and the page sizes; for a DOCX, also the PDF it was converted to. [ADR 001](001-architecture.md) left the format open between `multipart/mixed` and a zip.
- **With no SDK ([ADR 009](009-engine-only.md)), consumers parse the response themselves,** so it must be readable without Diplex code.
- **`fetch` reads `multipart/form-data` natively:** `Response.formData()` accepts `multipart/form-data` and `application/x-www-form-urlencoded` bodies, and no other multipart type ([MDN](https://developer.mozilla.org/docs/Web/API/Response/formData)).
- **Node's `fetch` buffers the whole body to parse it,** and says to call `formData()` only on responses from trusted servers ([undici](https://undici.nodejs.org/api/Fetch)). The engine is the consumer's own server.
- **A zip needs an archive library in Node:** its built-in `zlib` handles Gzip, Deflate, Brotli and Zstd streams, not zip archives ([Node.js](https://nodejs.org/api/zlib.html)).

## Decision

- **`/render` takes and returns `multipart/form-data`.** The request carries the DOCX or PDF in one file part, not base64.
- **Every response carries the page images:** a JSON part with the page count and each page's `{ index, width, height }` in points, and one WebP image per page, in page order. A DOCX response also carries the PDF it was converted to.
- **A PDF upload gets no PDF back.** The engine does not change it and the consumer already has it, so returning it would only double the transfer.
- **The part names and the JSON shape are defined by the Pydantic models in `definition/`** and published in the OpenAPI spec ([convention 002](../code-convention/002-boundaries-and-contract.md)).

## Consequences

- **A JavaScript consumer reads the response with `fetch` alone:** `await response.formData()`.
- **`formData()` holds the whole response in memory,** so the page limit ([ADR 001](001-architecture.md) §7) also bounds the response size.
- **Consumers branch on what they sent:** for a PDF upload, they keep their original file as the document's PDF.
- **Consumers in other languages need a multipart parser,** as with any multipart API.
