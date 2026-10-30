# Code Conventions

Rules for working in this repository. They apply to people and coding agents alike. Conventions 007 to 009 are this project's own preferences and may differ from other codebases; [AGENTS.md](../../AGENTS.md) summarises them.

| # | Convention | Covers |
|---|---|---|
| [001](001-repository-layout.md) | Repository layout | where each package and folder lives |
| [002](002-boundaries-and-contract.md) | Boundaries and the API contract | what the engine, SDK and store may do; Pydantic to OpenAPI to TypeScript |
| [003](003-untrusted-input.md) | Documents are untrusted input | unoserver isolation, scratch directories, input limits, logging |
| [004](004-dependencies-and-licensing.md) | Dependencies and licensing | MIT compatibility, no AGPL, fonts, current dependency licences |
| [005](005-tooling-and-testing.md) | Tooling and testing | Python, TypeScript and Docker tooling; testing on real samples |
| [006](006-writing-docs.md) | Writing docs | numbering, ADR rules, bullet style, citing sources |
| [007](007-comments-and-docblocks.md) | Comments and docblocks | file docblocks, one-line comments on every function and schema |
| [008](008-files-and-folders.md) | Files and folders | one responsibility per file, folder entries, no sibling imports |
| [009](009-naming.md) | Naming | clear names; no vague or cryptic names |
| [010](010-convention-checker.md) | The convention checker | running it, the Stop hook, what it checks |
