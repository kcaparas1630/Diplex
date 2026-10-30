# Convention 005: Tooling and Testing

## Tooling

- **Python:** 3.11+, managed with `uv`; tests with `pytest`; HTTP API with FastAPI.
- **TypeScript:** package manager and test runner to be decided when `diplex-sdk`, `diplex-store` and `diplex-playground` are scaffolded; the playground's web framework is also undecided. Types are generated from the OpenAPI spec with openapi-typescript; migrations with drizzle-kit.
- **Docker:** the engine image builds from the root `Dockerfile`.
- **Conventions:** `python -m scripts.conventions` checks conventions 007 to 009 and runs automatically as a Claude Code Stop hook ([convention 010](010-convention-checker.md)).
- **Add the exact build, test and run commands to [AGENTS.md](../../AGENTS.md) once they exist.**

## Testing

- **Every module gets unit tests.** Run the full test suite and the convention checker before reporting work as done.
- **Measure rendering quality on real documents in `samples/`,** not synthetic ones. Do not generate sample documents.
- **When a result is compared against Word, say so;** when it is not, do not claim Word fidelity.
- **Report results faithfully,** including failures and numbers that look bad.
