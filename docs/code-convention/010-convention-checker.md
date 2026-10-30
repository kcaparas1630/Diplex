# Convention 010: The Convention Checker

> Code: [`scripts/conventions/`](../../scripts/conventions) · Hook: [`.claude/settings.json`](../../.claude/settings.json)

## Running It

- **Run `python -m scripts.conventions` from the repository root.** It checks every Python and TypeScript file against conventions [007](007-comments-and-docblocks.md), [008](008-files-and-folders.md) and [009](009-naming.md), prints each problem with its file, line, rule and fix, and exits 1 if there are any.
- **It must pass before work is reported as done.** When it fails, read each problem, fix the code (not the checker), and run it again until it passes.
- **It needs only Python 3.11 or newer,** with no dependencies, so it works before any package is scaffolded.
- **Its tests:** `python -m pytest scripts/conventions/tests`.

## The Stop Hook

- **Claude Code runs the checker automatically every time it finishes a task,** through a project Stop hook in `.claude/settings.json` (`python -m scripts.conventions --hook`).
- **On failure the hook exits 2 and prints the report to stderr.** Claude Code then does not stop: it receives the report, fixes the code, and the hook runs again when it next tries to stop.
- **The loop ends only when the checker passes.** If a problem genuinely cannot be fixed, the rule or its settings need changing in a deliberate, reviewed change, never a bypass in the code.
- **Review or disable the hook with `/hooks`** in Claude Code.

## What It Checks, and How

| Rule | Python | TypeScript |
|---|---|---|
| File docblock | module docstring (`ast`) | first line is `/**` |
| One-line comments on functions, classes, schemas | docstrings (`ast`) | `/** ... */` directly above, found by line patterns |
| Import boundaries | resolved `import` and `from` statements (`ast`) | relative `import`, `export ... from`, `require()` |
| Names | every defined name (`ast`) | declarations and `const`/`let`/`var` |
| File length, file names, folder entries | both languages |

- **Python checks parse the code,** so they are exact.
- **TypeScript checks match lines,** not a syntax tree. They cover the usual one-line declaration forms and can miss unusual layouts, such as arrow functions whose parameters span lines.
- **When `diplex-sdk`, `diplex-store` and `diplex-playground` are scaffolded,** ESLint (typescript-eslint, eslint-plugin-jsdoc and a boundaries rule) takes over the TypeScript checks, and Ruff's pydocstyle rules can join on the Python side. The checker keeps the rules no linter has (one line only, sibling imports, folder entries) and runs the linters from the same command.
- **Limits and word lists** live in `scripts/conventions/settings/`.
