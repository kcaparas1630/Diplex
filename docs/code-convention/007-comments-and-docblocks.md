# Convention 007: Comments and Docblocks

> These are this project's preferences; other codebases may choose differently. Checked by the [convention checker](010-convention-checker.md).

## Files

- **Every file opens with a docblock saying what the file does.** Python: a module docstring. TypeScript: a `/** */` block as the first thing in the file. It may run to several lines.
- **A folder's entry file describes the folder** (`__init__.py`, `index.ts`): its docblock says what the folder contains ([convention 008](008-files-and-folders.md)).

## Functions

- **Every function has a one-line comment saying clearly what it does.** That includes methods, private helpers, nested functions and tests.
- **Python:** a one-line docstring, `"""Render every page and return the page records."""`.
- **TypeScript:** a one-line `/** ... */` directly above the declaration, with no blank line between. Decorators may sit between the comment and the declaration.
- **One line only.** If one line is not enough, the function is doing too much, or the detail belongs in the file docblock.

## Schemas and Types

- **Every schema or type definition has a one-line comment saying what it is and what it is for:** Pydantic models, dataclasses, zod schemas, TypeScript interfaces, type aliases, enums and classes.
- **Python:** a one-line class docstring, `"""A page as the viewer receives it: its number and pixel size."""`.
- **TypeScript:** a one-line `/** ... */` above the `interface`, `type`, `enum`, `class` or `const ... = z.` line.
