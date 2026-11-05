# Convention 001: Repository Layout

The planned layout. So far `core/diplex/` has its three top-level folders (`definition/`, `engine/`, `api/`), `engine/checks/`, `engine/docx_to_pdf/`, `engine/pdf_loading/` and `engine/pages/`; each deeper folder is added when it has code.

```
Dockerfile                     builds the engine image, tagged diplex-core (Python, LibreOffice, unoserver, fonts)
LICENSE                        MIT
core/                          Python engine (uv project diplex-core): the whole product
  diplex/                      the importable package: import diplex
    definition/                Pydantic models: the API contract (source of the OpenAPI spec)
    engine/
      docx_to_pdf/             unoserver pool and supervision
      pdf_loading/             loads a PDF's bytes into PDFium, for pages/ and checks/
      pages/                   PDF -> WebP page images and page sizes
      checks/                  input checks: document type, size, pages, macros, zip bombs
    api/                       FastAPI route: render
  tests/
playground/                    sample consumer app: calls the engine over HTTP and stores the results
                               in its own bucket and database (never published)
docs/                          see docs/README.md
scripts/
  conventions/                 the convention checker (convention 010)
  start-unoserver.sh           builds the engine image and runs unoserver for the engine tests
.claude/settings.json          Claude Code project settings: the Stop hook that runs the checker
samples/                       real test documents (git-ignored, never committed)
```

- **The folder says which part of the repository this is; the package says whose code it is.** `core/` holds the project (`pyproject.toml`, `uv.lock`, `tests/`), and the code inside it is the `diplex` package, imported as `import diplex`. Package names are global once installed, so a bare `core` package could clash with another one. The Docker image keeps the `diplex-core` tag for the same reason.
- **The package sits directly in `core/`, with no `src/` folder.** The src layout mainly protects libraries published to PyPI from packaging mistakes ([PyPA](https://packaging.python.org/discussions/src-layout-vs-flat-layout/)); Diplex ships as a Docker image, whose smoke test catches those.
- **There is no SDK, client or table package,** and no hosted gateway ([ADR 009](../adr/009-engine-only.md)).
- **`samples/` is git-ignored** and must never be committed.
