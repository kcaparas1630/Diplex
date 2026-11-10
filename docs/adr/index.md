# Architecture Decision Records

Each record captures one decision: the context, what was decided, and what follows from it. [ADR 001](001-architecture.md) is the living description of the system; the others explain why it looks that way.

| # | Decision | Status | Date |
|---|---|---|---|
| [001](001-architecture.md) | Architecture: the current system | Accepted (living) | 2026-10-30 |
| [002](002-rendering-engine-scope.md) | Diplex is a rendering engine: PDF and page images only | Accepted | 2026-10-30 |
| [003](003-consumer-owned-storage.md) | Storage belongs to the consumer; the SDK runs on their server | Superseded by 009 | 2026-10-30 |
| [004](004-unoserver-pool.md) | LibreOffice runs through a unoserver pool | Accepted | 2026-10-30 |
| [005](005-fonts.md) | Fonts are a fixed set of packages; no Word-fidelity promise | Accepted | 2026-10-30 |
| [006](006-hosted-and-self-hosted.md) | Hosted and self-hosted, one engine image; auth in a gateway | Superseded by 009 | 2026-10-30 |
| [007](007-mit-licence.md) | MIT licence, free to use | Accepted | 2026-10-30 |
| [008](008-pdf-to-docx-pipeline.md) | PDF to DOCX conversion workflow | Superseded by 002 | 2026-10-28 |
| [009](009-engine-only.md) | Diplex is the engine only: no SDK, no store, self-hosted | Accepted | 2026-11-03 |
| [010](010-render-response-format.md) | The render response is multipart/form-data | Accepted | 2026-11-03 |
| [011](011-unoserver-pool-dispatcher.md) | The engine runs, dispatches and recycles the unoserver pool | Accepted | 2026-11-07 |
| [012](012-api-key-and-version.md) | An optional Bearer key and a required API version header | Accepted | 2026-11-10 |
