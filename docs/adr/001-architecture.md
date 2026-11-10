# ADR 001: Architecture

> Status: **Accepted (living)** · 2026-11-03 · Licence: MIT
> The current system. Each part's reasoning is in its own ADR ([index](index.md)).

Diplex is an open-source document rendering engine. A consumer app sends a DOCX or PDF over HTTP and always gets back an image of every page, ready to display. A DOCX takes one extra step: the engine converts it to PDF first, renders the images from that PDF, and returns the PDF too so the app can offer it for download. The engine stores nothing; the consumer app keeps the results in its own bucket and database. There is no SDK.

---

## 1. Problems Diplex Solves

- **Showing documents in an app is hard.** Diplex turns every page into an image the app can display directly, without a PDF viewer in the browser.
- **Converting DOCX to PDF needs LibreOffice, fonts and isolation.** Diplex packages them in one Docker image, so every DOCX also has a PDF for download.
- **Out of scope:** content extraction (text, headings, table of contents, positions), PDF to DOCX, OCR, editing, and form filling. The proof of concept showed that structure extraction and PDF to DOCX are not reliable enough to promise ([ADR 002](002-rendering-engine-scope.md)). Consumers who need navigation build it on the PDF themselves.
- **Also out of scope:** storing documents, client libraries and a hosted service ([ADR 009](009-engine-only.md)).

## 2. Components

> Decision: [ADR 009](009-engine-only.md)

- **`core/` (Python): the engine, and the whole product.** One render endpoint: a DOCX or PDF in, an image of every page and the page sizes out. A DOCX is converted to PDF first, and that PDF is returned as well. Stateless: no database, no storage, no storage credentials. Shipped as a Docker image built from the root `Dockerfile`, which runs the API on port 8000; the engine starts its pool of unoserver instances on the container's localhost (§6), and a DOCX sent in the few seconds LibreOffice takes to start waits for it.
- **The OpenAPI spec is the consumer's interface.** FastAPI generates it from the Pydantic models in `definition/`, the engine serves it at `/openapi.json`, and [docs/openapi.json](../openapi.json) publishes it; consumers in any language call the engine with an ordinary HTTP client.
- **`playground/`:** a sample consumer app in this repo: Next.js with Postgres and RustFS ([ADR 016](016-playground-stack.md)). It calls the engine over HTTP and stores the results in its own bucket and database, following §5. It is never published.

```
consumer app (server)
   │  POST /render ── multipart/form-data: the DOCX or PDF ──► Diplex engine (Docker, consumer's network)
   │               ◄── multipart/form-data: page sizes, page images (+ the converted PDF for a DOCX)
   ├── writes ──► consumer's bucket ◄──── presigned GET ── consumer's browser
   └── writes ──► consumer's database
```

## 3. Deployment

> Decisions: [ADR 009](009-engine-only.md), [ADR 012](012-api-key-and-version.md) (key and version)

- **Self-hosted only.** The consumer runs the engine image on its own network, with no outbound network at all ([ADR 013](013-no-network-for-libreoffice.md); [self-hosting guide](../self-hosting.md)). Authentication is off by default (the engine must not be reachable from the internet), or `DIPLEX_API_KEY` sets one static key that `/render` then needs as `Authorization: Bearer <key>`; `/health` stays open.
- **The consumer can add its own licensed fonts** by mounting them into the image ([ADR 005](005-fonts.md)).
- **Settings are environment variables,** checked when the engine starts: `DIPLEX_MAX_UPLOAD_BYTES` is the largest request body the engine accepts, 50 MiB (52,428,800 bytes) by default until §7's measurements set it; `DIPLEX_MAX_PAGES` is the most pages a document may have, 500 by default, also provisional; `DIPLEX_UNOSERVER_INSTANCES` is the number of unoserver instances, by default the vCPUs available to the container (the CPUs it may run on, capped by a `docker run --cpus` quota rounded up); `DIPLEX_CONVERTER_WAIT_SECONDS` is how long a DOCX waits for an idle instance, 30 by default; `DIPLEX_CONVERSION_TIMEOUT_SECONDS` is how long a conversion may run before its instance is killed, 120 by default; `DIPLEX_CONVERSIONS_BEFORE_RECYCLE` is how many conversions an instance does before it is recycled, 50 by default.
- **Versioned releases.** Images are published to `ghcr.io/<owner>/diplex-core` as `1.2.3` and `1.2` when a `v1.2.3` tag is pushed ([convention 011](../code-convention/011-releases.md)), and each `/render` request carries the API version it codes against in `Diplex-Api-Version`.
- **Licence:** MIT for all Diplex code. Every dependency must allow that ([ADR 007](007-mit-licence.md), [convention 004](../code-convention/004-dependencies-and-licensing.md)).

## 4. The Render API

> Decision: [ADR 010](010-render-response-format.md)

- **`POST /render` takes `multipart/form-data`** with the DOCX or PDF in one file part, not base64, and the header `Diplex-Api-Version: 1` ([ADR 012](012-api-key-and-version.md)); a missing or unknown version gets 400 `unsupported_api_version`.
- **Every upload gets its page images back,** as `multipart/form-data`: a JSON part listing each page's `{ index, width, height }` in points, in page order (its length is the page count), so a viewer can lay out pages before the images load. Sizes are as the page is shown (its crop box, with `/Rotate` applied, so they match the image) and rounded to 0.01 pt; and one WebP image per page, in page order.
- **A DOCX takes one extra step:** the engine converts it to PDF first and renders the images from that PDF. The response also carries that PDF, so the app can offer it for download. A PDF upload gets no PDF back: the engine does not change it and the consumer already has it.
- **Errors are JSON `{ code, message }`** (`RenderError` in `definition/`): consumers branch on the code, and the message never repeats document contents. A request without the engine's API key, when it has one, gets 401 `unauthorized`; a request without a readable `document` part gets 400 or 422 `invalid_request`; a body over the upload limit gets 413 `upload_too_large` before the engine reads the rest of it; anything but a PDF or a DOCX gets 415 `unsupported_document_type`; a PDF that PDFium can't read gets 422 `unreadable_pdf`, one with a page over the pixel limits 422 `page_too_large`, and a document with more pages than `DIPLEX_MAX_PAGES` 422 `too_many_pages` (a PDF before any page renders, a DOCX once converted). A DOCX that would unzip past the zip-bomb limits gets 422 `docx_limits_exceeded`, and one carrying macros or ActiveX controls 422 `macros_not_allowed`, before LibreOffice sees it. A DOCX that LibreOffice can't load or convert, or that it is still converting at the timeout, gets 422 `docx_conversion_failed`, 503 `converter_unavailable` when no unoserver instance is running or ready, and 503 `converter_busy` when every instance stayed busy for `DIPLEX_CONVERTER_WAIT_SECONDS`. Anything unexpected gets 500 `internal_error`, whose message names the job in the engine's log.
- **Page images are WebP at 144 DPI, in one size** ([ADR 015](015-one-page-image-size.md)), lossless for text pages and lossy (about quality 80) for scanned or photo-heavy pages. On the samples, lossless was smaller on 90% of pages (median 70 KB), so a 100-page document is about 7 MB of images.

## 5. Storing the Results (the Consumer's Code)

> Decision: [ADR 009](009-engine-only.md). Diplex cannot enforce these; the playground follows them.

- **The consumer owns the bucket, the database and the credentials.** They stay on the consumer's server and never reach the engine or a browser. Viewing, downloading and deleting never touch the engine.
- **Name folders by document ID, never by file name,** under a prefix the consumer chooses, and keep the user's file name in the database:

  ```
  {prefix}/{userId}/{documentId}/
    original.docx | original.pdf
    document.pdf              (for PDF uploads, the original itself)
    pages/page-0001.webp
  ```

- **Keep one row per document:** its ID, owner, file name, folder location, source type (`docx` | `pdf`), the page sizes from the render response, and a deletion time. Deleting a document removes its folder from the bucket, not only the row.
- **Deliver files with presigned GET URLs signed on demand, never stored.** A presigned URL stops working at its expiry or when the credentials that signed it expire, whichever comes first ([AWS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)). Sign in batches as the user scrolls (for example 10 pages at a time) with a 15 to 60 minute expiry, and reuse each URL for its lifetime so browsers can cache the images, which never change.
- **Treat presigned URLs as bearer passes.** Anyone holding one can fetch the file until it expires, so hand them only to users the app has authorized, and give the signing credentials only read, write, list and delete on the chosen prefix.

## 6. Rendering Pipeline (inside the Engine)

> Decisions: [ADR 004](004-unoserver-pool.md) (unoserver), [ADR 011](011-unoserver-pool-dispatcher.md) (the pool), [ADR 014](014-isolation-review.md) (isolation), [ADR 005](005-fonts.md) (fonts), [convention 003](../code-convention/003-untrusted-input.md) (untrusted input)

- **DOCX to PDF:** LibreOffice driven by a pool of [unoserver](https://github.com/unoconv/unoserver) instances (MIT) that the engine starts, by default one per vCPU. Each instance keeps one LibreOffice running, handles one conversion at a time, has its own profile and temporary files, and binds only to localhost. A conversion takes an idle instance, waiting up to 30 s for one before 503 `converter_busy`, and times out after 120 s.
- **Instances are recycled and supervised by the engine,** not by unoserver's flags: after 50 conversions (memory is not reclaimed after large files; an instance's first life is shortened by its place in the pool, so recycles don't line up) and after any failed or timed-out conversion, between jobs, the instance's whole process group is killed, its profile and temporary files deleted, and a fresh instance started. A keeper thread restarts an instance that exits, since unoserver does not restart LibreOffice itself.
- **Fonts:** the metric-compatible families (Carlito, Caladea, Liberation) plus DejaVu and Noto, installed as packages. Debian's stock fontconfig already maps Calibri, Cambria, Arial, Times New Roman and Courier New to them. Line breaks and page counts stay close to Word's; the glyphs differ, and fonts without a clone reflow. Diplex does not promise Word fidelity.
- **PDF to page images, for every upload:** pypdfium2 (Apache-2.0 / BSD-3-Clause) reads each page's size and renders every page of the PDF (the converted one for a DOCX, the upload itself for a PDF) at 144 DPI, form fields included, encoded as WebP with Pillow: lossy at quality 80 when image objects cover at least half the page (a scan or a photo page, measured from PDFium's object bounds), lossless otherwise. PDFium is not thread-safe, even across documents ([pypdfium2](https://pypdfium2.readthedocs.io/en/stable/python_api.html)), so one document at a time goes through it, behind a lock in the engine process; a pool of worker processes, each with its own PDFium, is still to be designed. The images and the PDF therefore always match page for page.
- **Documents are untrusted input:** the type told from the bytes (a PDF or a DOCX, never by file name or the client's content type), size and page limits, a pixel limit per page image (40 MP, above an A0 drawing's 32 MP, and 16,383 pixels on a side, WebP's limit) checked before any page renders, macro rejection, zip-bomb checks (at most 10,000 parts, 512 MiB unzipped, and 100 times expansion for any part over 1 MiB, provisional until §7's measurements; each part is read back within its declared size, so lying headers fail), LibreOffice's DOCX import filter only (never format detection, so other formats are refused), no network for LibreOffice (the engine's container gets no egress, [ADR 013](013-no-network-for-libreoffice.md)), a per-job scratch directory wiped afterwards, and no document contents in logs. Scanned PDFs render as images like any other PDF.

## 7. Open Decisions

- **Upload limits:** maximum pages and file size (now a provisional 50 MiB; the largest sample is 3 MB) for a synchronous render, measured on the engine image without a GPU, and whether the 40 MP page image limit fits that memory. The page limit also bounds the response size, since consumers hold it in memory.
- **unoserver pool settings:** [ADR 011](011-unoserver-pool-dispatcher.md) sets the defaults (one instance per vCPU, recycling after 50 conversions, a 120 s timeout, a 30 s wait for an instance); a load test of the pool on the samples, on the hosting target, confirms or changes them. Sharing a LibreOffice process between jobs is a deliberate trade against one process per job, which the POC used. The 2026-10-30 benchmark ([ADR 004](004-unoserver-pool.md), laptop numbers to repeat on the hosting target) points to one instance per vCPU (more instances than vCPUs slowed every conversion, 2.04 times at 8 on 4 vCPUs), recycling after about 50 conversions (memory grows from 233 MB idle to about 1.0 GB after 50 and 1.65 GB after 303, never reclaimed), and a timeout above the slowest successful conversion, 75 s (median 0.15 s, p95 2.3 s, p99 about 44 s; one document takes 189 s). A timed-out instance must be killed with its LibreOffice: it keeps failing requests, and `soffice.bin` outlives unoserver and holds the UNO port.
- **Word fidelity:** compare the DOCX samples rendered by Diplex against Word before making any fidelity claim.
