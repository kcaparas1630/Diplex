# ADR 004: LibreOffice Runs Through a unoserver Pool

> Status: **Accepted** · 2026-10-30

## Context

- **The proof of concept started a fresh LibreOffice container per job.** That gives the strongest isolation, but pays LibreOffice's startup on every conversion.
- **[unoserver](https://github.com/unoconv/unoserver) (MIT) keeps LibreOffice running** and converts over a local socket.
- **Its README states its limits:** one conversion at a time per instance, no restart after a crash, memory not reclaimed after large files, and unauthenticated ports that must not be exposed.
- **Per-job fonts were the main reason for one process per job,** and [ADR 005](005-fonts.md) removed them.

## Decision

- **A pool of unoserver instances,** each with one LibreOffice, its own profile, and ports bound to localhost only.
- **Each instance is recycled** after a set number of conversions (`--stop-after`) and killed on a conversion timeout (`--conversion-timeout`).
- **A supervisor restarts instances when they exit.**
- **LibreOffice has no network access,** and each job still gets its own scratch directory, wiped afterwards.

## Consequences

- **Less CPU per conversion,** since LibreOffice no longer starts for every job.
- **Weaker isolation:** a malicious document can affect later conversions on the same instance until it is recycled. This is a deliberate trade, reviewed in the security milestone.
- **Pool size, recycle count and timeout are open decisions** ([ADR 001](001-architecture.md) §9).
