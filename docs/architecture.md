# Diplex Architecture

> Status: **Draft** · 2026-10-29
> Detailed pipeline: [pdf-to-docx.md](pdf-to-docx.md)

Diplex renders and converts documents so that apps don't have to. A consumer app uploads a DOCX or PDF and gets back page images to display, a JSON description of the content to navigate, and on-demand export to PDF or DOCX.

---

## 1. Problems Diplex Solves

- **Reliable conversion is hard to set up.** DOCX to PDF and PDF to DOCX need LibreOffice, the right fonts, and process isolation. Diplex packages all of it.
- **There is no structured view of a document.** Diplex returns a JSON object describing every block of content (text, type, page, position) for navigation and search.
- **Rendering documents in an app is hard.** Diplex turns every document into page images the app can display directly.
- **Out of scope:** prefilling forms, editing content, storing exported files, and Markdown output. Consumers get page images and `content`, which covers search and filtering.

## 2. Components

- **`diplex-core` (Python):** the service. Its engine converts files, renders page images, and extracts the JSON; its API and storage layers sign S3 URLs. It is stateless: no database and no metadata files. Shipped as a Docker image built from the `Dockerfile` at the repo root and hosted by us.
- **`diplex-sdk` (`@diplex/sdk`, TypeScript):** the only interface consumers use. It contains the API client and the procedures (`upload`, `getDocument`, `export`), and reads and writes the Diplex table in the consumer's database through the consumer's own database connection.
- **`diplex-store` (`@diplex/store`, TypeScript):** table definitions only. The Drizzle table is the canonical schema, and drizzle-kit generates plain SQL migrations for consumers on other ORMs. The consumer runs the migration in their own database; Diplex never touches it.
- **`diplex-playground` (sample website):** a consumer app kept in this repo. It uploads, views and exports documents through `@diplex/sdk`, using its own database and its own Diplex API key. It shows consumers how to integrate and gives us an end-to-end test of every flow. It is never published or deployed to customers.
- **One API contract:** Pydantic models in `diplex-core` define every request and response. FastAPI publishes them as an OpenAPI spec, and the SDK's TypeScript types are generated from it, so the Python and TypeScript sides cannot drift apart.
- **Boundary rule:** the consumer app talks only to the SDK; the SDK talks to the service and the consumer's database; only the service talks to S3 with credentials. `diplex-sdk` imports `diplex-store`, never the reverse.

```
consumer app
   │  diplex.getDocument(id)
   ▼
@diplex/sdk ──── reads/writes ────► consumer database (table defined by @diplex/store)
   │  HTTPS + API key
   ▼
diplex-core service (Python, hosted by us) ──► S3 (diplex-documents)
                                                   ▲
consumer browser ── presigned GET ─────────────────┘
```

Repository layout:

```
Dockerfile          builds the diplex-core service image
diplex-core/        src/diplex_core/{definition, engine, api, storage}, tests/
diplex-sdk/         procedures/, client/ (types.gen.ts generated from OpenAPI), index.ts
diplex-store/       tables/ (Drizzle + SCHEMA_VERSION), migrations/ (drizzle-kit SQL)
diplex-playground/  sample website that consumes Diplex through @diplex/sdk
docs/
```

## 3. Tenancy and Access

- **Consumers authenticate with an API key,** which the service maps to a tenant ID. Consumers never get AWS credentials or IAM roles.
- **Every S3 path starts with the tenant ID.** Two consumers can both have a "user1" without colliding.
- **The service enforces tenant isolation, and AWS backs it up.** Per request, the service assumes one shared role with a session policy limited to `{tenantId}/*` (the "token vending machine" pattern). A service bug still cannot read another tenant's files.
- **User isolation is shared.** Diplex checks that a document is requested with the user ID it was stored under. Deciding which of the consumer's users may open which document is the consumer app's responsibility.
- **Bring-your-own-bucket is a later option:** the consumer creates a role in their account that trusts ours, with an external ID. No access keys are ever exchanged.

## 4. Storage (S3)

- **Only originals and page images are stored.** Exports are produced on demand and never stored. The JSON lives in the consumer's database.
- **One bucket, tenant-scoped layout:**

  ```
  s3://diplex-documents/
    {tenantId}/{userId}/{documentId}/
      original.docx | original.pdf
      pages/page-0001.webp
      pages/page-0002.webp
  ```

- **Page images are WebP:** lossless for text pages, lossy (around quality 80) for scanned or photo-heavy pages. Page numbers are zero-padded so they sort correctly. Images carry a long `Cache-Control`, since they never change.
- **Folders are named by document ID, never by file name.** The user's file name is kept in the consumer's table and applied on download.
- **A lifecycle rule** removes documents the consumer has deleted.

## 5. Delivering Files (Presigned URLs)

- **Never store presigned URLs.** They last at most 7 days, and URLs signed with role credentials expire when the role session ends (often within an hour). Store the location and sign on demand.
- **Only the service signs.** The SDK asks the service for URLs and passes them to the browser, which downloads images directly from S3.
- **Sign in batches as the user scrolls** (for example 10 pages at a time), with an expiry of 15 to 60 minutes, and reuse each URL for its lifetime so browsers can cache it.
- **Presigned URLs act as bearer passes.** The consumer app hands them only to users it has authorized.
- **CloudFront comes later.** Add it (Origin Access Control plus signed cookies) when downloads pass about 1 TB a month or distant users need lower latency. The API returns URLs, so the switch is invisible to consumers.

## 6. Data in the Consumer's Database

- **One row per document,** in a table defined by `@diplex/store`:

  ```
  FileFormat = "docx" | "pdf"

  diplex_documents
    id              uuid, document ID (from the service)
    user_id         uuid, owner the document was stored under
    file_name       original name, e.g. "Contract March.docx"
    location        opaque S3 location string from the service
    source_type     FileFormat
    content         JSONB, the JSON object
    schema_version
    created_at
    updated_at
    deleted_at      null until the document is deleted
  ```

- **`location` is opaque.** The SDK passes it back to the service unchanged, so the S3 layout can change without breaking consumers.
- **Page data is not stored.** When the service signs URLs, it lists the page images under the document's location, so the page count always matches what is in S3. Page sizes are already in `content`, in Docling's `pages` field ([DoclingDocument](https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py)), in the same units as the bounding boxes. Pixel sizes come from the images.
- **`content` is loaded only when needed,** because long documents can produce a few megabytes of JSON.
- **Delete is soft.** The SDK sets `deleted_at` and hides deleted rows. The S3 files are removed straight away.
- **The schema version is checked when the SDK starts.** A mismatch fails the deploy with a clear "run the migration" error instead of failing user requests.

## 7. Flows

- **Upload:** the SDK sends the file to the service. The service stores the original, converts DOCX to PDF if needed, renders page images, and extracts the JSON, then returns `{ documentId, location, content }`. The SDK writes the row. The call is synchronous, so uploads have a page and size limit.
- **View:** `getDocument(documentId)`: the SDK reads the row and sends its location and a page range to the service. The service lists the page images, signs the requested ones, and returns `{ pageCount, pages: [{ index, url }] }`. The SDK returns those pages with `content`.
- **Export:**

  | File | Export as | Action |
  |---|---|---|
  | PDF | PDF | Presigned download of the original |
  | DOCX | DOCX | Presigned download of the original |
  | DOCX | PDF | Convert with LibreOffice, stream back |
  | PDF | DOCX | Convert with the pipeline in [pdf-to-docx.md](pdf-to-docx.md), stream back |

- **Delete:** the SDK sets `deleted_at` on the row and asks the service to delete the document's S3 folder.

## 8. Rendering Pipeline (inside the service)

- **DOCX to PDF:** LibreOffice, one process per job with its own profile and font configuration, using the same font library and resolution rules as PDF to DOCX.
- **PDF to page images:** pypdfium2 (permissive licence) at a fixed resolution, encoded as WebP.
- **Content extraction:** Docling reads the original file, and the service maps its output to the Diplex content model below.
- **Documents are untrusted input:** every LibreOffice process has a timeout and is killed afterwards, runs without network access, and works in a scratch directory that is wiped per job.
- **Licensing:** no AGPL dependencies (PyMuPDF, pdf2docx). GPL tools are allowed only as separate processes. Docling and docling-core are MIT ([docling](https://github.com/docling-project/docling), [docling-core](https://github.com/docling-project/docling-core)).

### Content JSON

- **`content` is a Diplex model, not raw Docling output.** It is defined in Pydantic in `definition/`, so a Docling upgrade cannot change what consumers receive. The service maps Docling's document to it after extraction. Docling's fields are defined in [docling-core](https://github.com/docling-project/docling-core/blob/main/docling_core/types/doc/document.py).
- **Content is a tree of sections.** Every heading starts a section that holds its own blocks and its subsections, nested by heading level. Text before the first heading goes in an untitled opening section. DOCX levels come from Word's heading styles. PDF headings arrive flat at level 1 unless Docling's opt-in heading recovery is enabled, which uses bookmarks, numbering and font style ([heading levels](https://docling-project.github.io/docling/usage/heading_levels/)). The service enables it. Where levels can't be recovered, sections form a flat list: the table of contents loses its indentation, but every heading stays linked and searchable. A document with no headings has one untitled section and an empty table of contents.
- **The table of contents is the section tree without its blocks.** Each entry links to its section by ID and carries the section's page and box, so the viewer can jump to it. It is built from the document's headings, so documents without a printed contents page still get one. A printed contents page is dropped.
- **Tables keep their structure.** Each table holds its cells with row, column, spans and header flags, so a table can be searched and shown as a grid. Cells keep no boxes of their own; the table's box covers them.
- **Everything else from Docling is dropped:** page headers and footers, watermarks, hidden text, all image data, picture annotations, form and key-value items, the internal reference graph, formatting and hyperlinks. Blocks keep a list of boxes, one per page, because a paragraph can cross a page break. Boxes are fractions of the page, measured from the top-left corner.

  ```
  content
    pages:    [{ index, width, height }]
    sections: [Section]

  Section   { id, title, level, boxes, blocks: [Block], sections: [Section] }
  Block     { id, kind, text, boxes, table? }      kind: paragraph | list_item | table | picture
                                                         | caption | footnote | formula | code
  Table     { rows, cols, cells: [{ row, col, rowSpan, colSpan, text, header }] }
  Box       { page, x, y, w, h }
  ```

## 9. Open Decisions

- **Upload limits:** maximum pages and file size for synchronous processing.
- **Page image resolution:** one size, or a thumbnail plus a full size.
- **PDF to DOCX editability:** LibreOffice's import produces positioned text boxes, not flowing paragraphs. Decide whether that meets customers' needs (see [pdf-to-docx.md](pdf-to-docx.md)).
- **Scanned PDFs:** run OCR (for example ocrmypdf) or reject them at upload.
- **More ORMs:** Prisma and SQLAlchemy table definitions, when a consumer needs them. Until then, drizzle-kit's SQL migrations cover other ORMs.
- **Text selection overlay:** block-level boxes cover navigation and search. Selectable text on the page needs line-level boxes in `content`.
- **TypeScript tooling:** package manager and test runner for `diplex-sdk`, `diplex-store` and `diplex-playground`.
- **Playground stack:** web framework and local database for `diplex-playground`.
