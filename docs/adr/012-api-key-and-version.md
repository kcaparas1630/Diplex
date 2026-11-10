# ADR 012: An Optional Bearer Key and a Required API Version Header

> Status: **Accepted** · 2026-11-10

## Context

- **The engine is self-hosted on the consumer's network** ([ADR 009](009-engine-only.md)). [ADR 001](001-architecture.md) §3 allows no authentication by default, or one static key from an environment variable.
- **There is no SDK,** so consumers send whatever the engine needs with a plain HTTP client; the headers must be ones every client can set.
- **Bearer tokens are the standard way to send a key in a header:** `Authorization: Bearer <token>`, and a server that refuses one answers 401 with a `WWW-Authenticate` challenge ([RFC 6750](https://www.rfc-editor.org/rfc/rfc6750) §2.1, §3).
- **[ADR 001](001-architecture.md) §3 also says each request carries an API version,** so a consumer pins the contract it codes against and the engine can change it without breaking them.

## Decision

### The Key

- **`DIPLEX_API_KEY` turns authentication on.** Unset or empty, the engine needs no key. Set, it must be at least 16 characters, or the engine refuses to start.
- **`/render` then needs `Authorization: Bearer <key>`.** The key is compared in constant time (`hmac.compare_digest`); anything else gets 401 `unauthorized` with `WWW-Authenticate: Bearer`, before the upload is rendered.
- **`/health` and `/openapi.json` stay open,** so health checks and consumers' code generators need no key.
- **The OpenAPI spec lists the key as an optional Bearer scheme** (`ApiKey`, with an empty alternative requirement).

### The Version

- **Every `/render` request sends `Diplex-Api-Version: 1`.** A missing or unknown version gets 400 `unsupported_api_version`, whose message lists the versions the engine supports.
- **A change that would break consumers gets a new version,** and an engine release keeps serving the previous one for at least one more release. Additions that old consumers can ignore (a new error code, a new optional part) keep the version.

## Consequences

- **One key per engine:** rotating it means restarting the engine with the new key and updating every consumer at the same time.
- **The key travels in clear text over plain HTTP.** Keep the engine on a private network, or put TLS in front of it when traffic crosses one that isn't.
- **Every consumer must send the version header,** including the smoke test, the load test and the playground; a client without it gets 400 rather than a silent guess.
