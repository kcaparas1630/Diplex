# Convention 004: Dependencies and Licensing

- **Diplex is MIT** ([ADR 007](../adr/007-mit-licence.md)). Every dependency must be compatible with distributing Diplex under MIT.
- **No AGPL dependencies** (for example PyMuPDF). GPL tools only as separate processes.
- **Check the licence before adding any dependency,** and record it in the relevant doc.
- **Fonts shipped in the image must allow redistribution and embedding in PDFs.**
- **Keep the FreeType credit in the README.** FreeType comes with LibreOffice in the engine image and inside the pypdfium2 and Pillow wheels, and its licence (FTL) requires a binary distribution to say it is based in part on the FreeType Team's work.

## Current Engine Dependencies

| Component | Licence | Use |
|---|---|---|
| LibreOffice | MPL-2.0 | DOCX to PDF, run unmodified as a separate process |
| unoserver | MIT | keeps LibreOffice running between conversions |
| pypdfium2 | Apache-2.0 / BSD-3-Clause; its PDFium build is BSD-3-Clause and bundles permissive libraries (FreeType, ICU, libjpeg-turbo, OpenJPEG, libpng, zlib and others), whose licence files ship in the wheel | PDF page sizes and page rendering in `engine/pages/` |
| Pillow | MIT-CMU; its wheel bundles permissive libraries (libwebp, libjpeg-turbo, libpng, FreeType, HarfBuzz, zlib-ng and others), whose licence texts ship in the wheel | holds the rendered page images in `engine/pages/`; WebP encoding |
| Pydantic (with pydantic-core, annotated-types, typing-inspection) | MIT | the API contract models in `definition/` |
| typing-extensions | PSF-2.0 | installed with Pydantic |
| FastAPI (with annotated-doc) | MIT | the HTTP API in `api/` |
| Starlette | BSD-3-Clause | the web framework under FastAPI |
| anyio, h11 | MIT | installed with FastAPI and uvicorn |
| idna, click | BSD-3-Clause | installed with FastAPI and uvicorn |
| colorama | BSD-3-Clause | installed with click on Windows only |
| opentelemetry-api | Apache-2.0 | installed with FastAPI |
| uvicorn | BSD-3-Clause | serves the API |
| Carlito, Caladea, Liberation, DejaVu, Noto fonts | OFL / Apache-2.0 / Bitstream Vera | rendering |
| pytest | MIT | engine tests (development only) |
| httpx2 (with httpcore2) | BSD-3-Clause | FastAPI's `TestClient` in the API tests (development only) |
| truststore | MIT | installed with httpx2 (development only) |
| hatchling | MIT | builds the `diplex-core` package |
