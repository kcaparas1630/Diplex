# Convention 003: Documents Are Untrusted Input

- **Run LibreOffice only through the unoserver pool** ([ADR 004](../adr/004-unoserver-pool.md)): each instance on localhost only, with its own profile, no network access, a conversion timeout, recycling after a set number of conversions, and a supervisor that restarts it when it exits. Do not weaken the recycling or timeouts without an ADR.
- **Work in a per-job scratch directory and wipe it afterwards.**
- **Reject macro-enabled files, enforce file size and page limits, and guard against zip bombs** (DOCX is a zip).
- **Never log document contents.**
