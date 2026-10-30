# Convention 008: Files and Folders

> These are this project's preferences; other codebases may choose differently. Checked by the [convention checker](010-convention-checker.md).

## One Responsibility per File

- **A file does one thing,** so a behaviour can be traced to exactly one place.
- **Name the file after that responsibility** (`page_images.py`, `presign.ts`). Names like `utils`, `helpers`, `common`, `shared` and `misc` are not allowed, because they collect unrelated code.
- **The checker flags files over 300 lines** as a sign of more than one responsibility. Split them; do not raise the limit to pass.

## Folders

- **A folder's contents are clear from its name and its entry file.** Every folder of code has an entry (`__init__.py` for Python, `index.ts` for TypeScript) whose docblock says what the folder contains. The repository root and test folders are exempt.
- **The entry is the folder's only public door.** Other folders import the folder through its entry, never through one of its files.

## Imports

- **No sibling imports.** A file never imports another file in the same folder. If two files need the same code, that code moves into a sub-folder, or the folder's entry composes the two.
- **A file may import:** anything inside its own sub-folders, another folder's entry (a sibling or cousin folder, never a parent), and installed packages (`zod`, `@diplex/store`, `pydantic`).
- **Only the entry file may import its own folder's files,** to compose and re-export them.
- **Never import a parent folder.** Parents import their sub-folders, so importing upward creates cycles.
- **Tests are exempt** and may import the module they test directly.

```
engine/
  __init__.py          may import pages/, docx_to_pdf/ and its own files
  pages/
    __init__.py        public entry of pages/
    render.py          may import pages/encoding/ (sub-folder) and ../checks (an entry); not ../pages/x.py
    encoding/
      __init__.py
```
