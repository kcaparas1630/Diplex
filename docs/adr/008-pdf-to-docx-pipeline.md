> Status: **Superseded** by [ADR 002](002-rendering-engine-scope.md) · 2026-10-30
>
> **Out of scope.** Diplex exports PDF only; PDF to DOCX was dropped after the proof of concept showed its output dropping and clipping words ([ADR 002](002-rendering-engine-scope.md)). Kept as a record of the design and as a starting point if the feature returns. Not maintained.

# ADR 008: PDF to DOCX Conversion Workflow

> Status: **Draft** · 2026-10-28 · based on "PDF → DOCX Conversion Workflow" by Kent Hudson Caparas
> Changes from the original are marked **Change:**.

LibreOffice is the conversion engine. Every other step exists to control which fonts are used when the DOCX is laid out, and to catch it when that goes wrong.

## The Core Problem

- **A PDF is a finished page.** Every character sits at a fixed position, drawn with a font packed inside the file.
- **A DOCX is a set of layout instructions.** Whoever opens it (Word, LibreOffice) lays out the page again, using the fonts installed on that machine.
- **A missing font changes character widths,** so lines wrap differently. The result is extra pages, a different look, or clipped text.

## The Workflow

Step 0 is prepared ahead of time. Steps 1 to 6 run for every job.

```
[0] Font library (ahead of time)
        │
PDF ─► [1] Inspect ─► [2] Resolve fonts ─► [3] Convert ─► [4] Export DOCX ─► [5] Verify ─► [6] Respond
        pypdf          rules + fonts.conf   LibreOffice     + embed fonts       reopen,        DOCX + report
                                            (per-job proc)                      render, compare or fail
```

### 0. Font Library (ahead of time)

- **Keep a font set on the worker image:** open-source fonts (Liberation, Carlito, Caladea, Gelasio), licensed fonts, and customer-uploaded brand fonts.
- **A fontconfig file adds alias rules,** for example Arial to Liberation Sans and Calibri to Carlito.
- **The fonts embedded inside a PDF cannot be reused.** They are subsets missing most characters and often lack a usable character map; reusing them produced garbage glyphs in testing.
- **Change:** build the fontconfig cache once in the image and share it read-only with every job, so each per-job process does not rescan the whole library at startup.

### 1. Inspect the PDF (pypdf)

- **Read the page count, check whether pages contain real text, and list every font the PDF references.**
- **Scanned PDFs (images, no text) are routed to OCR or rejected,** instead of producing an empty DOCX.
- **Change:** normalize font names before resolving them. Strip subset prefixes (`ABCDEF+ArialMT`), split PostScript names into family and style (`Arial-BoldMT` is Arial, bold), and handle names that embed the style in the family (`Arial Bold`). Unnormalized names fall through to the wrong bucket in step 2.
- **Change:** collect fonts from form XObjects and annotations as well as page resources, or fonts used in stamps and form fields are missed.

### 2. Resolve the Fonts

- **Each font goes into one of three buckets:**
  1. **Available:** the exact font is installed.
  2. **Aliased:** a metric-compatible substitute is mapped (same character widths).
  3. **Substituted:** nothing matches, the closest font is used, and the job is flagged.
- **The output is a per-job `fonts.conf` plus a record of each decision.**
- **Change:** same character widths keep line breaks the same, which removes most reflow. Tables and text boxes can still lay out slightly differently (LibreOffice bug 136231), so step 5 remains necessary even when every font is available or aliased.

### 3. Convert (LibreOffice, one process per job)

- **Start a fresh `soffice --headless` process** with its own profile (`-env:UserInstallation`) and its own `FONTCONFIG_FILE`, then open the PDF with the `writer_pdf_import` filter.
- **A fresh process is the only way to give each job its own fonts.** A running LibreOffice never picks up fonts added after it started (tested).
- **Isolation:** a malicious or broken PDF that hangs or crashes LibreOffice takes down only its own job. Kill the process on timeout. Run it without network access.
- **A warm pool of idle processes** (one job each, killed afterwards) can remove the 0.4 to 0.8 second startup cost later if needed.

### 4. Export the DOCX with Fonts Embedded (UNO)

- **Through UNO, turn on the `EmbedFonts` setting, then save as DOCX** with `storeToURL`. The font files are stored inside the DOCX.
- **This fixes fonts missing on the customer's machine.** With embedding, the DOCX rendered correctly on a machine without the font (tested).
- **Change:** test embedding in Word for Windows, Word for Mac, and Google Docs before promising it. Not every app honours embedded fonts.
- **Change:** check which font name an aliased font ends up with in the DOCX (the original name or the substitute) and which file gets embedded, so the report describes what the customer actually receives.

### 5. Verify

- **Change:** reopen the saved DOCX in a fresh LibreOffice process and render that to PDF. The original step rendered the document still open from step 3, which checks the import but not the file the customer receives.
- **Compare the render with the original PDF:** same page count, and the same words on each page. Normalize text first (ligatures, hyphenation, whitespace) and allow a small tolerance, because extraction order varies.
- **Change:** make the visual diff a default, not an option. Clipped text is still present in a PDF's text layer, so text comparison cannot detect clipping; only an image comparison can. Render with pypdfium2 (permissive licence, in-process) instead of pdftoppm (GPL subprocess).
- **Change:** this check compares against LibreOffice's own rendering, while customers open the DOCX in Word. Keep a regression set of real PDFs checked against Word on a schedule, so Word-specific differences are found before customers find them.

### 6. Respond

- **Return the DOCX plus a report:** which fonts were exact, aliased, or substituted, and whether verification passed.
- **If verification fails,** return an error or a warning, depending on what the API promises.
- **The report also tells us which fonts to add to the step 0 library next.**

## Concept Summary

| Concept | Problem it solves |
|---|---|
| Font library and alias rules | Fonts missing on the server |
| Inspect | Knowing which fonts a job needs; catching scanned PDFs |
| Font resolution | Reflow caused by fonts with different widths |
| Per-job LibreOffice process | Job-specific fonts; isolation; hangs |
| Font embedding | Fonts missing on the customer's machine |
| Verification | Layout breaking without any error |
| Report | Customer trust; knowing which fonts to add next |

## Stack and Licences

| Step | Tool | Licence |
|---|---|---|
| 1, 5: inspect, page counts, text comparison | pypdf | BSD |
| 0, 2: font library and resolution rules | Our code + fonts.conf; Liberation, Carlito, Caladea, Gelasio | Ours / OFL |
| 3: PDF import | LibreOffice `writer_pdf_import`, one process per job | MPL-2.0 |
| 4: font embedding and DOCX export | UNO `EmbedFonts`, then `storeToURL` | MPL-2.0 |
| 5: render back to PDF | A fresh LibreOffice process opening the saved DOCX | MPL-2.0 |
| 5: visual diff | pypdfium2 page rendering | Apache-2.0 / BSD-3 |

PyMuPDF (AGPL) and unoserver are not needed.

## Out of Scope

- **Editable flowing text.** LibreOffice's PDF import produces a DOCX that looks like the PDF, but each line is its own positioned text box, not a paragraph that can be edited normally. Flowing text needs a separate engine later (a commercial engine such as Aspose, or our own reconstruction from the JSON). **This is the main product decision:** confirm that "looks identical, editable line by line" is acceptable for DOCX exports.
- **Scanned PDFs.** These need OCR (for example ocrmypdf) before step 1.
- **Font licensing.** A font embedded in a customer's DOCX is a font we distribute. The step 0 library may only contain fonts whose licences allow embedding. Customer-uploaded brand fonts are embedded only in that customer's documents.
