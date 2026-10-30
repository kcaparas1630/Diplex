# ADR 001: Architecture

> Status: **Accepted (living)** · 2026-10-30 · Licence: MIT
> The current system. Each part's reasoning is in its own ADR ([index](index.md)).

Diplex is an open-source document rendering engine. A consumer app sends a DOCX or PDF and gets back the PDF and an image of every page, ready to display. The engine stores nothing; the SDK keeps the files in the consumer's own bucket and the record in the consumer's own database.

---

## 1. Problems Diplex Solves

- **Showing documents in an app is hard.** Diplex turns every page into an image the app can display directly, without a PDF viewer in the browser.
- **Converting DOCX to PDF needs LibreOffice, fonts and isolation.** Diplex packages them in one Docker image, so every DOCX also has a PDF for download.
- **Out of scope:** content extraction (text, headings, table of contents, positions), PDF to DOCX, OCR, editing, and form filling. The proof of concept showed that structure extraction and PDF to DOCX are not reliable enough to promise ([ADR 002](002-rendering-engine-scope.md)). Consumers who need navigation build it on the PDF themselves.

## 2. Components

- **`diplex-core` (Python):** the engine. One render endpoint: a DOCX or PDF in, the PDF and page images out. Stateless: no database, no storage, no storage credentials. Shipped as a Docker image built from the root `Dockerfile`.
- **`diplex-sdk` (`@diplex/sdk`, TypeScript):** the only interface consumers use. It runs on the consumer's server, calls the engine to render, writes the files to the consumer's bucket with the consumer's credentials, and reads and writes the Diplex table through the consumer's database connection.
- **`diplex-store` (`@diplex/store`, TypeScript):** table definitions only. The Drizzle table is the canonical schema; drizzle-kit generates plain SQL migrations for consumers on other ORMs.
- **`diplex-playground`:** a sample consumer app in this repo, using only the SDK, its own bucket and its own database. It is never published.
- **Hosted gateway (hosted mode only):** API keys and rate limits in front of our engines. The engine itself does not know who the caller is.

```
consumer server
   │  createDocument(file)               getDocument / updateDocument / deleteDocument
   ▼                                          │
@diplex/sdk ── multipart ──► diplex-core      │  (no engine call)
   │            ◄── PDF + page images         ▼
   ├── writes ──► consumer's bucket ◄──── presigned GET ── consumer's browser
   └── writes ──► consumer's database (table defined by @diplex/store)
```

## 3. Deployment

> Decision: [ADR 006](006-hosted-and-self-hosted.md)

- **Self-hosted:** the consumer runs the engine image on their own network. Authentication is off by default (the engine must not be reachable from the internet) or a single static key set by environment variable. The consumer can add their own licensed fonts.
- **Hosted:** we run the engines behind a gateway that checks API keys and applies rate, concurrency and size limits. It is free; the limits exist for abuse control, not billing.
- **One image for both.** Authentication, limits and usage live in the gateway, never in the engine, so the engine stays stateless in both modes.
- **Versioned releases.** Images are tagged by version, each request carries an API version, and the SDK reports clearly when a self-hosted engine is too old.
- **Licence:** MIT for all Diplex code. Every dependency must allow that ([ADR 007](007-mit-licence.md), [convention 004](../code-convention/004-dependencies-and-licensing.md)).

## 4. Storage (the Consumer's Bucket)

> Decision: [ADR 003](003-consumer-owned-storage.md)

- **The consumer owns the bucket and the credentials.** The SDK uses them on the consumer's server, like any AWS SDK; they never reach the engine or a browser.
- **The SDK owns the key layout,** under a prefix the consumer chooses:

  ```
  s3://{consumer-bucket}/{prefix}/{userId}/{documentId}/
    original.docx | original.pdf
    document.pdf              (for PDF uploads, the original itself)
    pages/page-0001.webp
    pages/page-0002.webp
  ```

- **Page images are WebP at 144 DPI,** lossless for text pages and lossy (about quality 80) for scanned or photo-heavy pages. On the samples, lossless was smaller on 90% of pages (median 70 KB). Images carry a long `Cache-Control`, since they never change.
- **Folders are named by document ID, never by file name.** The user's file name lives in the database row and is applied on download.
- **The SDK documents the minimum IAM policy:** read, write, list and delete on the chosen prefix, nothing else.

## 5. Delivering Files (Presigned URLs)

- **The SDK signs, with the consumer's credentials,** and passes the URLs to the browser, which downloads directly from the bucket.
- **Never store presigned URLs.** They expire, and URLs signed with role credentials expire when the role session ends. Store the location and sign on demand.
- **Sign in batches as the user scrolls** (for example 10 pages at a time), with an expiry of 15 to 60 minutes, and reuse each URL for its lifetime so browsers can cache it.
- **Presigned URLs act as bearer passes.** The consumer app hands them only to users it has authorized.

## 6. Data in the Consumer's Database

- **One row per document,** in a table defined by `@diplex/store`:

  ```
  FileFormat = "docx" | "pdf"

  diplex_documents
    id              uuid, document ID
    user_id         uuid, owner the document was stored under
    file_name       original name, e.g. "Contract March.docx"
    location        key prefix of the document's folder in the consumer's bucket
    source_type     FileFormat
    pages           JSON, [{ index, width, height }] in points, so a viewer can lay out pages before images load
    schema_version
    created_at
    updated_at
    deleted_at      null until the document is deleted
  ```

- **`location` is opaque to consumer code.** Only the SDK reads it, so the key layout can change without breaking consumers.
- **The schema version is checked when the SDK starts.** A mismatch fails the deploy with a clear "run the migration" error instead of failing user requests.

## 7. SDK Procedures

| Procedure | Calls the engine | What it does |
|---|---|---|
| `createDocument(file)` | yes | Sends the file as a multipart upload, receives the PDF and page images, writes them and the original to the bucket, and writes the row. |
| `getDocument(id, range)` | no | Reads the row, presigns the requested page images and the PDF, and returns `{ pageCount, pages: [{ index, width, height, url }], pdfUrl }`. |
| `updateDocument(id, fields)` | no | Changes the row's metadata (for example `file_name`). New content means a new document. |
| `deleteDocument(id)` | no | Sets `deleted_at` and deletes the document's folder from the bucket straight away. |
| `exportDocument(id)` | no | Presigns the PDF (or the original DOCX) for download under the user's file name. |

- **Only `createDocument` reaches the engine,** so viewing, exporting and deleting keep working even when the engine is down.
- **The SDK runs on the server only.** It must never be bundled into browser code.

## 8. Rendering Pipeline (inside the Engine)

> Decisions: [ADR 004](004-unoserver-pool.md) (unoserver), [ADR 005](005-fonts.md) (fonts), [convention 003](../code-convention/003-untrusted-input.md) (untrusted input)

- **DOCX to PDF:** LibreOffice driven by a pool of [unoserver](https://github.com/unoconv/unoserver) instances (MIT). Each instance keeps one LibreOffice running, handles one conversion at a time, has its own profile, and binds only to localhost.
- **Instances are recycled and supervised:** restarted after a set number of conversions (`--stop-after`, because memory is not reclaimed after large files), killed on a conversion timeout (`--conversion-timeout`), and restarted by a supervisor when they exit, since unoserver does not restart LibreOffice itself.
- **Fonts:** the metric-compatible families (Carlito, Caladea, Liberation) plus DejaVu and Noto, installed as packages. Debian's stock fontconfig already maps Calibri, Cambria, Arial, Times New Roman and Courier New to them. Line breaks and page counts stay close to Word's; the glyphs differ, and fonts without a clone reflow. Diplex does not promise Word fidelity.
- **PDF to page images:** pypdfium2 (Apache-2.0 / BSD-3-Clause) at 144 DPI, encoded as WebP with Pillow.
- **Documents are untrusted input:** size and page limits, macro rejection, zip-bomb checks, no network for LibreOffice, a per-job scratch directory wiped afterwards, and no document contents in logs. Scanned PDFs render as images like any other PDF.

## 9. Open Decisions

- **Render response format:** a `multipart/mixed` response or a zip archive for the PDF and page images. A 100-page document is about 7 MB of images.
- **Upload limits:** maximum pages and file size for a synchronous render, measured on the engine image without a GPU.
- **unoserver pool:** pool size, `--stop-after` count, and conversion timeout. Sharing a LibreOffice process between jobs is a deliberate trade against one process per job, which the POC used.
- **Hosted gateway:** build it, or use a managed API gateway (keys and usage plans).
- **Word fidelity:** compare the DOCX samples rendered by Diplex against Word before making any fidelity claim.
- **Page image resolution:** one size, or a thumbnail plus a full size.
- **Storage beyond S3:** S3-compatible stores (R2, MinIO) work through the same SDK code; GCS and Azure need their own adapters.
- **TypeScript tooling and playground stack:** package manager, test runner, web framework and local database.
