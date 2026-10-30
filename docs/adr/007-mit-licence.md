# ADR 007: MIT Licence, Free to Use

> Status: **Accepted** · 2026-10-30

## Context

- **Diplex could be closed, source-available, or open source.**
- **Every dependency the engine needs is free and permissive:** unoserver (MIT), LibreOffice (MPL-2.0, run unmodified as a separate process), pypdfium2 (Apache-2.0 / BSD-3-Clause), Pillow (MIT-CMU), and the OFL and Apache-2.0 fonts.
- **Gotenberg, the closest comparable engine, is MIT.**

## Decision

- **All Diplex code is released under the [MIT licence](../../LICENSE).**
- **Diplex is free, both self-hosted and hosted.** There is no paid tier for now.

## Consequences

- **Every new dependency must be compatible with distributing Diplex under MIT;** AGPL dependencies are not allowed ([convention 004](../code-convention/004-dependencies-and-licensing.md)).
- **Anyone may run or resell Diplex,** including as a hosted service.
- **Fonts shipped in the image must allow redistribution and embedding in PDFs.**
