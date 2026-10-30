# ADR 002: Diplex Is a Rendering Engine

> Status: **Accepted** · 2026-10-30 · Supersedes: [ADR 008](008-pdf-to-docx-pipeline.md)

## Context

- **The first design promised three things:** page images, a JSON description of the content (sections, table of contents, tables, positions), and export to PDF or DOCX.
- **A proof of concept ran 214 real samples (103 DOCX, 111 PDF) through that design.**
- **Rendering was reliable:** every page rendered, and DOCX to PDF succeeded on 103 of 103 documents.
- **Understanding was not:** Docling found headings in only 45% of DOCX files, gave DOCX no positions, mis-levelled PDF headings, dropped table cells silently, and returned empty content for scanned PDFs as a success.
- **PDF to DOCX was unusable:** the output dropped and clipped words, and verifying it took minutes per document.

## Decision

- **Diplex turns a DOCX or PDF into a PDF and an image of every page.** Nothing else.
- **No content extraction:** Docling, the content JSON, the table of contents and page boxes are removed.
- **Export is PDF only.** A DOCX is converted to PDF once, at upload; the original DOCX can still be downloaded unchanged.
- **Consumers who need navigation or search build it on the PDF themselves.**

## Consequences

- **The engine image loses Docling, torch and the models,** so it is CPU-only and several GB smaller.
- **The plan shrinks** from 93–144 days to 54.5–84, losing the riskiest milestone (PDF to DOCX).
- **The only quality question left is how close a DOCX rendering is to Word** ([ADR 005](005-fonts.md)).
- **A text layer can be added later** without changing the design: pypdfium2 already reads it.
