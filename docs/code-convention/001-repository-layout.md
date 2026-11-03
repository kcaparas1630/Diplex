# Convention 001: Repository Layout

The planned layout. So far only `core/` with `engine/docx_to_pdf/` exists; each folder is added when it has code.

```
Dockerfile                     builds the engine image, tagged diplex-core (Python, LibreOffice, unoserver, fonts)
LICENSE                        MIT
core/                          Python engine (uv): the whole product
  src/diplex_core/
    definition/                Pydantic models: the API contract (source of the OpenAPI spec)
    engine/
      docx_to_pdf/             unoserver pool and supervision
      pages/                   PDF -> WebP page images and page sizes
      checks/                  input checks: size, pages, macros, zip bombs
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

- **The folder is `core`, but the Python project stays `diplex-core` and the import name `diplex_core`,** because package names are global: a top-level `core` import could clash with any other installed package. The Docker image keeps the `diplex-core` tag for the same reason.
- **There is no SDK, client or table package,** and no hosted gateway ([ADR 009](../adr/009-engine-only.md)).
- **`samples/` is git-ignored** and must never be committed.
