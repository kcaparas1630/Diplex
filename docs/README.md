# About These Docs

This folder holds everything written about Diplex except the code: what it is, why it is built this way, and how to work on it. The full list is in [index.md](index.md).

## Sections

- **[adr/](adr/index.md): Architecture Decision Records.** What the system is and why. Start with [ADR 001](adr/001-architecture.md), the living description of the current architecture; the others each record one decision.
- **[code-convention/](code-convention/index.md): rules for working in the repository.** Layout, boundaries, untrusted input, licensing, testing and doc style.

## How to Read Them

- **New to Diplex:** read [ADR 001](adr/001-architecture.md), then skim the ADR index to see why each part is the way it is.
- **About to write code:** read the [code conventions](code-convention/index.md), especially [002](code-convention/002-boundaries-and-contract.md) and [003](code-convention/003-untrusted-input.md).
- **Wondering why something was cut:** the ADR that cut it records the evidence.
- **Everything is numbered.** Documents keep their number for life; superseded ADRs stay, marked as superseded, so the history is readable.

## Adding a Document

- **Pick the section, take the next number, and add a line to that section's `index.md` and to [index.md](index.md).**
- **Follow [convention 006](code-convention/006-writing-docs.md)** for ADR rules and style.
