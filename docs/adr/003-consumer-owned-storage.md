# ADR 003: Storage Belongs to the Consumer

> Status: **Accepted** · 2026-10-30

## Context

- **The first design stored every document in our S3 bucket,** with a tenant prefix per consumer and a session policy per request to keep tenants apart.
- **That made Diplex a platform holding customers' documents,** with tenancy, retention, deletion and credential handling to get right.
- **Comparable engines hold nothing:** Gotenberg returns the converted file in the response, and the caller stores it.
- **Sending a consumer's storage credentials to a vendor is unsafe** and fails most security reviews.

## Decision

- **Files go in the consumer's own bucket, and the record in the consumer's own database.**
- **The SDK runs on the consumer's server** and uses the consumer's credentials there, like any AWS SDK. Credentials never reach the engine or a browser.
- **Only `createDocument` calls the engine.** It uploads the file (multipart, not base64), receives the PDF and page images, and writes them to the bucket.
- **Get, update, delete and export run in the SDK alone.** Delete removes the document's folder from the bucket, not only the row.

## Consequences

- **The engine is stateless:** no database, no storage, no tenancy, no credentials.
- **Viewing, exporting and deleting keep working when the engine is down.**
- **The render response carries the PDF and all page images,** about 7 MB per 100 pages. Its format is an open decision ([ADR 001](001-architecture.md) §9).
- **The SDK must document a minimum IAM policy** and must never be bundled into browser code.
