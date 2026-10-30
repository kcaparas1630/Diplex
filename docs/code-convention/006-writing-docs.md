# Convention 006: Writing Docs

- **Each section is numbered and indexed.** A new document gets the next number in its folder and a line in that folder's `index.md`. Numbers are never reused.
- **ADRs are append-only.** To change a decision, write a new ADR that supersedes the old one and update the old one's status line; do not rewrite history. [ADR 001](../adr/001-architecture.md) is the exception: it is the living description of the current system and is updated in the same change as any ADR that alters it.
- **Every ADR has a status line** (Proposed, Accepted, Superseded) and the sections Context, Decision, Consequences.
- **Describe each concept in 3 to 5 bullets,** each starting with a bold lead-in.
- **Ground technical claims in current documentation, specifications and vendor docs, and cite sources.** Do not rely on recalled knowledge for standards, limits or prices.
