# ADR 005: Fonts Are a Fixed Set of Packages

> Status: **Accepted** · 2026-10-30

## Context

- **Fonts do not decide whether a conversion succeeds;** they decide whether line breaks and page counts match Word's. A missing font falls back to a wider one, and the layout reflows.
- **Metric-compatible clones exist for the common Office fonts:** Carlito (Calibri), Caladea (Cambria), and Liberation (Arial, Times New Roman, Courier New).
- **Debian's stock fontconfig already maps those names to the clones,** so the custom alias file in the proof of concept was redundant.
- **Gotenberg uses the same approach:** the clones plus DejaVu and Noto, and no Microsoft fonts.

## Decision

- **The engine image installs the clone fonts, DejaVu and Noto as packages.** No font inspection, resolution rules, per-job configuration or font report.
- **Self-hosted operators may add fonts they are licensed for,** including Microsoft's, by mounting them into the image.
- **Diplex does not promise Word fidelity.** Only Word lays out Word documents exactly.

## Consequences

- **Documents in the common Office fonts keep Word's line breaks and page counts;** the glyphs look slightly different.
- **Fonts with no clone (Verdana, Tahoma, brand and CJK fonts) reflow** unless the operator installs them.
- **Word fidelity is unmeasured** until DOCX samples rendered by Diplex are compared against Word.
