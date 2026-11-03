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

- **`core/` (Python): the engine, and the whole product.** One render endpoint: a DOCX or PDF in, an image of every page and the page sizes out. A DOCX is converted to PDF first, and that PDF is returned as well. Stateless: no database, no storage, no storage credentials. Shipped as a Docker image built from the root `Dockerfile`.
- **The OpenAPI spec is the consumer's interface.** FastAPI generates it from the Pydantic models in `definition/`; consumers in any language call the engine with an ordinary HTTP client.
- **`playground/`:** a sample consumer app in this repo. It calls the engine over HTTP and stores the results in its own bucket and database, following §5. It is never published.

```
consumer app (server)
   │  POST /render ── multipart/form-data: the DOCX or PDF ──► Diplex engine (Docker, consumer's network)
   │               ◄── multipart/form-data: page sizes, page images (+ the converted PDF for a DOCX)
   ├── writes ──► consumer's bucket ◄──── presigned GET ── consumer's browser
   └── writes ──► consumer's database
```

## 3. Deployment

> Decision: [ADR 009](009-engine-only.md)

- **Self-hosted only.** The consumer runs the engine image on its own network. Authentication is off by default (the engine must not be reachable from the internet) or a single static key set by environment variable.
- **The consumer can add its own licensed fonts** by mounting them into the image ([ADR 005](005-fonts.md)).
- **Versioned releases.** Images are tagged by version and each request carries an API version.
- **Licence:** MIT for all Diplex code. Every dependency must allow that ([ADR 007](007-mit-licence.md), [convention 004](../code-convention/004-dependencies-and-licensing.md)).

## 4. The Render API

> Decision: [ADR 010](010-render-response-format.md)

- **`POST /render` takes `multipart/form-data`** with the DOCX or PDF in one file part, not base64.
- **Every upload gets its page images back,** as `multipart/form-data`: a JSON part with the page count and each page's `{ index, width, height }` in points, so a viewer can lay out pages before the images load, and one WebP image per page, in page order.
- **A DOCX takes one extra step:** the engine converts it to PDF first and renders the images from that PDF. The response also carries that PDF, so the app can offer it for download.
- **A PDF upload gets no PDF back.** The engine does not change it and the consumer already has it.
- **Page images are WebP at 144 DPI,** lossless for text pages and lossy (about quality 80) for scanned or photo-heavy pages. On the samples, lossless was smaller on 90% of pages (median 70 KB), so a 100-page document is about 7 MB of images.

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

> Decisions: [ADR 004](004-unoserver-pool.md) (unoserver), [ADR 005](005-fonts.md) (fonts), [convention 003](../code-convention/003-untrusted-input.md) (untrusted input)

- **DOCX to PDF:** LibreOffice driven by a pool of [unoserver](https://github.com/unoconv/unoserver) instances (MIT). Each instance keeps one LibreOffice running, handles one conversion at a time, has its own profile, and binds only to localhost.
- **Instances are recycled and supervised:** restarted after a set number of conversions (`--stop-after`, because memory is not reclaimed after large files), killed on a conversion timeout (`--conversion-timeout`), and restarted by a supervisor when they exit, since unoserver does not restart LibreOffice itself.
- **Fonts:** the metric-compatible families (Carlito, Caladea, Liberation) plus DejaVu and Noto, installed as packages. Debian's stock fontconfig already maps Calibri, Cambria, Arial, Times New Roman and Courier New to them. Line breaks and page counts stay close to Word's; the glyphs differ, and fonts without a clone reflow. Diplex does not promise Word fidelity.
- **PDF to page images, for every upload:** pypdfium2 (Apache-2.0 / BSD-3-Clause) renders every page of the PDF (the converted one for a DOCX, the upload itself for a PDF) at 144 DPI, encoded as WebP with Pillow. The images and the PDF therefore always match page for page.
- **Documents are untrusted input:** size and page limits, macro rejection, zip-bomb checks, LibreOffice's DOCX import filter only (never format detection, so other formats are refused), no network for LibreOffice, a per-job scratch directory wiped afterwards, and no document contents in logs. Scanned PDFs render as images like any other PDF.

## 7. Open Decisions

- **Upload limits:** maximum pages and file size for a synchronous render, measured on the engine image without a GPU. The page limit also bounds the response size, since consumers hold it in memory.
- **unoserver pool:** pool size, `--stop-after` count, and conversion timeout. Sharing a LibreOffice process between jobs is a deliberate trade against one process per job, which the POC used.
- **Word fidelity:** compare the DOCX samples rendered by Diplex against Word before making any fidelity claim.
- **Page image resolution:** one size, or a thumbnail plus a full size.
- **Playground stack:** web framework, local database, and TypeScript tooling (package manager, test runner).
