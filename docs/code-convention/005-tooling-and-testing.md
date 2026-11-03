# Convention 005: Tooling and Testing

## Tooling

- **Python:** 3.11+, managed with `uv`; tests with `pytest`; HTTP API with FastAPI.
- **TypeScript:** only in `playground/`. Its package manager, test runner and web framework are decided with the playground stack ([ADR 001](../adr/001-architecture.md) §7).
- **Docker:** the engine image builds from the root `Dockerfile`.
- **Conventions:** `python -m scripts.conventions` checks conventions 007 to 009 and runs automatically as a Claude Code Stop hook ([convention 010](010-convention-checker.md)).
- **Add the exact build, test and run commands to [AGENTS.md](../../AGENTS.md) once they exist.**

## Testing

- **Every module gets unit tests.** Run the full test suite and the convention checker before reporting work as done.
- **Measure rendering quality on real documents in `samples/`,** not synthetic ones. Do not generate sample documents.
- **When a result is compared against Word, say so;** when it is not, do not claim Word fidelity.
- **Report results faithfully,** including failures and numbers that look bad.
