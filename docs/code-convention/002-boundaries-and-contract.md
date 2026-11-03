# Convention 002: Boundaries and the API Contract

Do not break these without an ADR that changes [ADR 001](../adr/001-architecture.md).

## Engine

- **The engine is stateless.** No database, no storage, no storage credentials, no knowledge of customers. It renders a request and forgets it.
- **The engine never writes to a bucket or signs URLs.** It returns the results in the response; storing and delivering them is the consumer's code ([ADR 009](../adr/009-engine-only.md)).
- **The engine's only authentication is an optional static key.** It runs self-hosted on the consumer's network and must not be reachable from the internet.

## The API Contract

- **The Pydantic models in `core/src/diplex_core/definition/` are the API contract.** FastAPI generates the OpenAPI spec from them, and consumers code against that spec. Change the models; never hand-edit the spec.
- **`/render` speaks `multipart/form-data` both ways** ([ADR 010](../adr/010-render-response-format.md)): page sizes as JSON and one WebP per page for every upload, plus the converted PDF when the upload is a DOCX.
- **There is no SDK or client package.** Do not add one without a new ADR.

## Playground

- **The playground is an ordinary consumer.** It calls the engine over HTTP only, with its own bucket and its own database. It never imports `diplex_core`.
- **It follows the storage guidance in [ADR 001](../adr/001-architecture.md) §5:** credentials only on its server, presigned URLs signed on demand and never stored, and deleting a document removes its files.
