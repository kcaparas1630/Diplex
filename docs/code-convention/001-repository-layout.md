# Convention 001: Repository Layout

The planned layout. So far `core/diplex/` has its three top-level folders (`definition/`, `engine/`, `api/`), `api/form_data/`, `api/job_log/`, `engine/checks/`, `engine/docx_to_pdf/` (with `unoserver_client/` and `unoserver_pool/`), `engine/pdf_loading/` and `engine/pages/`; each deeper folder is added when it has code.

```
Dockerfile                     builds the engine image, tagged diplex-core (the engine, LibreOffice, unoserver, fonts)
LICENSE                        MIT
core/                          Python engine (uv project diplex-core): the whole product
  diplex/                      the importable package: import diplex
    definition/                Pydantic models: the API contract (source of the OpenAPI spec)
    engine/
      docx_to_pdf/             DOCX to PDF with LibreOffice
        unoserver_client/      XML-RPC calls to one unoserver
        unoserver_pool/        the engine's unoserver instances and the dispatcher (ADR 011)
          pooled_instance/     one instance's state and keeper thread
            unoserver_process/ its process: its own session, ports and scratch folder
      pdf_loading/             loads a PDF's bytes into PDFium, for pages/ and checks/
      pages/                   PDF -> WebP page images and page sizes
      checks/                  input checks: document type, size, pages, macros, zip bombs
    api/                       FastAPI routes: health and render
      form_data/               builds multipart/form-data response bodies
      job_log/                 logs each render job without its contents
  tests/
playground/                    sample consumer app: calls the engine over HTTP and stores the results
                               in its own bucket and database (never published)
docs/                          see docs/README.md
scripts/
  conventions/                 the convention checker (convention 010)
  smoke_render/                renders every sample through a running engine and reports what happened
  load_test/                   sends every DOCX sample to a running engine, several at once, and reports throughput and latency
  start-unoserver.sh           builds the engine image and runs one unoserver on port 2003 for the engine tests
  engine-entrypoint.sh         the image's command: runs the engine API, which starts its unoserver pool
.claude/settings.json          Claude Code project settings: the Stop hook that runs the checker
.github/workflows/ci.yml       CI on every pull request and on main (convention 005)
samples/                       real test documents (git-ignored, never committed)
```

- **The folder says which part of the repository this is; the package says whose code it is.** `core/` holds the project (`pyproject.toml`, `uv.lock`, `tests/`), and the code inside it is the `diplex` package, imported as `import diplex`. Package names are global once installed, so a bare `core` package could clash with another one. The Docker image keeps the `diplex-core` tag for the same reason.
- **The package sits directly in `core/`, with no `src/` folder.** The src layout mainly protects libraries published to PyPI from packaging mistakes ([PyPA](https://packaging.python.org/discussions/src-layout-vs-flat-layout/)); Diplex ships as a Docker image, whose smoke test catches those.
- **There is no SDK, client or table package,** and no hosted gateway ([ADR 009](../adr/009-engine-only.md)).
- **`samples/` is git-ignored** and must never be committed.
