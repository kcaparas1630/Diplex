# Convention 009: Naming

> These are this project's preferences; other codebases may choose differently. Checked by the [convention checker](010-convention-checker.md).

- **Every function, class, variable and parameter has a name that says what it holds or does:** `page_count`, `render_page_images`, `PresignedPage`, not `count`, `process`, `Thing`.
- **No vague names:** `data`, `info`, `temp`, `tmp`, `obj`, `val`, `res`, `ret`, `stuff`, `thing`, `foo`, `func`, `fn`, `cb`, `helper`, `manager`, `handle`, `util` and the like. Numbered variants (`data2`) count as the same name.
- **No cryptic short names.** Names are at least three characters, except the conventional `i`, `j`, `k` (loop indexes), `x`, `y`, `w`, `h` (coordinates and sizes), and `id`, `ok`, `db`, `io`. `self`, `cls` and `_` are always allowed.
- **Functions are named for what they do** (a verb: `presign_pages`); values and types for what they are (a noun: `page_images`, `RenderResponse`).
- **The checker can only catch the mechanical cases.** A long name can still be unclear; reviewers judge the rest.
