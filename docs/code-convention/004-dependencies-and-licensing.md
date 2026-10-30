# Convention 004: Dependencies and Licensing

- **Diplex is MIT** ([ADR 007](../adr/007-mit-licence.md)). Every dependency must be compatible with distributing Diplex under MIT.
- **No AGPL dependencies** (for example PyMuPDF). GPL tools only as separate processes.
- **Check the licence before adding any dependency,** and record it in the relevant doc.
- **Fonts shipped in the image must allow redistribution and embedding in PDFs.**

## Current Engine Dependencies

| Component | Licence | Use |
|---|---|---|
| LibreOffice | MPL-2.0 | DOCX to PDF, run unmodified as a separate process |
| unoserver | MIT | keeps LibreOffice running between conversions |
| pypdfium2 | Apache-2.0 / BSD-3-Clause | PDF page rendering |
| Pillow | MIT-CMU | WebP encoding |
| Carlito, Caladea, Liberation, DejaVu, Noto fonts | OFL / Apache-2.0 / Bitstream Vera | rendering |
