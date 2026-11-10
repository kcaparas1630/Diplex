# ADR 016: The Playground Is Next.js With Postgres and RustFS

> Status: **Accepted** · 2026-11-10

## Context

- **The playground is an ordinary consumer** ([ADR 009](009-engine-only.md), [convention 002](../code-convention/002-boundaries-and-contract.md)): it calls the engine over HTTP, stores the results in its own bucket and database as [ADR 001](001-architecture.md) §5 describes, never imports `diplex`, and is never published.
- **It needs server code and a browser viewer:** credentials and signing stay on its server; the browser uploads, lays out pages and loads them as the user scrolls.
- **It needs a local bucket and database,** started with the rest by one command (issues #72, #85).
- **Licences, from the npm registry and the images on 2026-11-10** ([convention 004](../code-convention/004-dependencies-and-licensing.md)): Next.js, React, `pg`, Vitest and pnpm are MIT; TypeScript and the AWS SDK for JavaScript are Apache-2.0; PostgreSQL is under the PostgreSQL License; RustFS is Apache-2.0.
- **MinIO was the first choice for the bucket, but it is unavailable:** `minio/minio` no longer exists on Docker Hub (checked 2026-11-10), and MinIO is AGPL-3.0, which convention 004 keeps out.

## Decision

- **Next.js (App Router) with React,** run on Node 22. Server code runs only in route handlers and server components; the upload form and the viewer are client components that call the playground's own routes.
- **PostgreSQL 17 through `pg`,** with one `documents` table that the playground creates on first start.
- **RustFS as the local S3-compatible store,** reached through the AWS SDK's S3 client. Endpoint, region, keys and path-style addressing come from environment variables, so any S3-compatible store (AWS S3, R2, MinIO) works unchanged.
- **pnpm and Vitest, in TypeScript.** `docker compose up --build` in `playground/` starts the engine (built from the root Dockerfile, on a network with no egress, [ADR 013](013-no-network-for-libreoffice.md)), RustFS, Postgres and the playground.
- **The folders follow [convention 008](../code-convention/008-files-and-folders.md):** every route folder has an `index.ts` entry; server code lives in `playground/server/`, browser code in `playground/viewer/`, reached by relative imports of folder entries. No path aliases, since the convention checker follows relative imports only.

## Consequences

- **The playground shows a familiar full-stack shape** consumers can copy: route handlers that call `/render`, store the results and sign URLs.
- **File-based routing adds an `index.ts` to every route folder,** which Next.js ignores and the checker needs.
- **RustFS is young;** the playground relies only on the common S3 calls (put, copy, list, delete, presigned GET), so another store is an environment change away.
