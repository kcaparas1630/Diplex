# AGENTS.md

Guidance for coding agents working in this repository.

## Project

Diplex is an open-source (MIT) document rendering engine for consumer apps. A consumer sends a DOCX or PDF and gets back the PDF and an image of every page to display. The engine stores nothing; the SDK keeps the files in the consumer's own bucket and the record in the consumer's own database.

- **Docs:** start at [docs/README.md](docs/README.md); everything is listed in [docs/index.md](docs/index.md).
- **Architecture (source of truth):** [ADR 001](docs/adr/001-architecture.md). Each decision behind it has its own ADR.
- **Rules:** the [code conventions](docs/code-convention/index.md). This file summarises them; the conventions win if they differ.
- **When a change alters the design,** update ADR 001 and add or supersede an ADR in the same change ([convention 006](docs/code-convention/006-writing-docs.md)).
- **Out of scope:** content extraction and PDF to DOCX ([ADR 002](docs/adr/002-rendering-engine-scope.md)). Do not reintroduce them without a new ADR.

## Rules That Must Not Break

- **The engine is stateless:** no database, storage, storage credentials or customer knowledge ([convention 002](docs/code-convention/002-boundaries-and-contract.md)).
- **Storage belongs to the consumer:** only the SDK touches the bucket, server-side, with the consumer's credentials; only `createDocument` calls the engine; delete removes the files; never store presigned URLs.
- **The Pydantic models in `definition/` are the API contract;** `types.gen.ts` is generated, never edited by hand. `diplex-sdk` imports `diplex-store`, never the reverse.
- **Documents are untrusted input:** LibreOffice only through the recycled, supervised unoserver pool with no network; wiped scratch directories; size, page, macro and zip-bomb checks; no document contents in logs ([convention 003](docs/code-convention/003-untrusted-input.md)).
- **MIT-compatible dependencies only,** no AGPL, licence recorded for each ([convention 004](docs/code-convention/004-dependencies-and-licensing.md)).

## Code Style (this project's preferences)

- **Every file opens with a docblock; every function, class and schema has a one-line comment** saying what it does or is for ([convention 007](docs/code-convention/007-comments-and-docblocks.md)).
- **One responsibility per file; every folder of code has an entry file describing it; no sibling imports.** Import sub-folders or another folder's entry, never a parent ([convention 008](docs/code-convention/008-files-and-folders.md)).
- **Names say what they hold or do;** no vague or cryptic names ([convention 009](docs/code-convention/009-naming.md)).
- **`python -m scripts.conventions` checks all of this and runs as a Stop hook when you finish.** If it blocks you, read the report, fix the code, and finish again; never weaken the checker to pass ([convention 010](docs/code-convention/010-convention-checker.md)).

## Testing

- **Unit-test every module, and run the full suite and the convention checker before reporting work as done.**
- **Measure on the real documents in `samples/`;** never generate sample documents. Never claim Word fidelity without a Word comparison. Report failures and bad numbers faithfully ([convention 005](docs/code-convention/005-tooling-and-testing.md)).

## Commands

```
python -m scripts.conventions                  # convention check (also the Stop hook, with --hook)
python -m pytest scripts/conventions/tests     # checker tests
```

Add the engine, SDK and store commands here once they exist.

## Working Agreements

- **Ground technical recommendations in current documentation and cite sources;** do not rely on recalled knowledge for standards, limits or prices.
- **Ask before destructive actions** (deleting files, resetting state, removing images).
- **Do not commit unless asked.**
