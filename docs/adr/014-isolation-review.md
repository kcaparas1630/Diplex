# ADR 014: The Shared-LibreOffice Isolation Trade, Reviewed

> Status: **Accepted** · 2026-11-10 · Reviews: [ADR 004](004-unoserver-pool.md) (confirmed, with the changes below)

## Context

- **[ADR 004](004-unoserver-pool.md) traded isolation for speed:** one LibreOffice converts many documents, so a malicious one can affect later conversions on the same instance until it is recycled. It asked for this review once the untrusted-input checks existed.
- **What now stands between a document and the next one:**
  - every DOCX is checked before conversion: zip limits and macro or ActiveX refusal (convention 003)
  - LibreOffice has no network ([ADR 013](013-no-network-for-libreoffice.md))
  - an instance is replaced after 50 successful conversions, after any failure or timeout, and when it exits, with its whole process group killed and its profile and temporary files deleted ([ADR 011](011-unoserver-pool-dispatcher.md))
  - page, pixel and upload limits bound the work
- **What remains:** a document that exploits a LibreOffice bug without failing its own conversion could stay in that process for up to 49 more conversions, and see or alter them. With no network, anything it took could only leave inside a later document's PDF. It runs as the same unprivileged user as the API.
- **The alternative costs a LibreOffice start per document:** about 5.5 s (measured in CI and locally), against a median conversion of 0.15 s on the benchmark.

## Decision

- **Keep shared instances,** recycled as ADR 011 describes. The remaining risk needs a working LibreOffice exploit that survives its own conversion; everything cheaper is refused, cut off or recycled away.
- **Offer per-document isolation as a setting:** `DIPLEX_CONVERSIONS_BEFORE_RECYCLE=1` gives every DOCX a fresh LibreOffice and profile, at about 5.5 s of restart per conversion and instance. The self-hosting guide says when to choose it: when users who must not see each other's documents share one engine.
- **Recommend locking the container down further,** checked in CI on every pull request: a read-only root filesystem with `/tmp` as tmpfs, all Linux capabilities dropped, and `no-new-privileges`. The engine and its pool start and answer under all three.
- **Later, if needed:** run LibreOffice as a different user from the API, and give the container a narrower seccomp profile. Neither is done; both need privileges or maintenance this review does not justify yet.

## Consequences

- **The default stays fast:** LibreOffice starts about once per 50 documents per instance, not once per document.
- **Operators with untrusting users can buy full per-document isolation** with one variable, and see its cost in the load test.
- **ADR 004's trade is confirmed, not removed.** The window is at most 49 successful conversions on one instance, inside one consumer's deployment.
