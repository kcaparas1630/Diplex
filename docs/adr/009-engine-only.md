# ADR 009: Diplex Is the Engine Only

> Status: **Accepted** · 2026-11-03 · Supersedes: [ADR 003](003-consumer-owned-storage.md), [ADR 006](006-hosted-and-self-hosted.md)

## Context

- **The design had four parts:** the engine, a TypeScript SDK (`@diplex/sdk`), a TypeScript table package (`@diplex/store`) and a hosted gateway.
- **Most of it was storage, not rendering.** The SDK wrote the consumer's bucket, owned a database table and its migrations, checked schema versions, signed URLs, and was heading for GCS and Azure adapters. About 27 of the 75 open issues were SDK, store or gateway work.
- **It tied consumers to TypeScript and Drizzle,** and needed a Pydantic to OpenAPI to TypeScript pipeline to keep two languages in step.
- **The engine is the one part that must be separate.** LibreOffice is a desktop application, not a library, and documents are untrusted, so conversion runs in its own container ([convention 003](../code-convention/003-untrusted-input.md)).
- **Gotenberg, which ADR 005 compares against, has the same shape:** a Docker image with a multipart HTTP route for LibreOffice conversion ([source](https://github.com/gotenberg/gotenberg/blob/main/pkg/modules/libreoffice/routes.go)).

## Decision

- **Diplex is the engine image and nothing else.** An HTTP API takes a DOCX or PDF and returns an image of every page and the page sizes; a DOCX is converted to PDF first, and that PDF is returned too ([ADR 010](010-render-response-format.md)). It stays stateless.
- **No SDK, no `@diplex/store`, no hosted gateway.** Consumers call the engine from their server with any HTTP client, in any language, against the published OpenAPI spec.
- **Storage stays the consumer's, and so does the code for it.** The consumer app writes the results to its own bucket and database and signs its own URLs. Diplex documents how ([ADR 001](001-architecture.md) §5), and the playground shows it working.
- **Self-hosted only.** The engine runs on the consumer's own network, with authentication off by default or a single static key set by environment variable.

## Consequences

- **Two parts instead of four:** the engine and the playground. TypeScript lives only in the playground, which is never published.
- **The engine never holds storage credentials.** It is the part that opens untrusted documents, so it holds the fewest secrets; writing to a bucket from the engine would bring back the credential handling ADR 003 rejected.
- **Consumers write their own storage code:** an upload, a database row and URL signing. The storage rules (never store presigned URLs, delete the files with the row) become guidance Diplex cannot enforce.
- **Viewing, downloading and deleting never touch the engine,** since the consumer holds every file.
- **There is no hosted service,** so ADR 007's "free when hosted" has nothing to apply to. Anyone may still host Diplex themselves under MIT.
