# Convention 003: Documents Are Untrusted Input

- **Run LibreOffice only through the unoserver pool** ([ADR 004](../adr/004-unoserver-pool.md)): each instance on localhost only, with its own profile, no network access, a conversion timeout, recycling after a set number of conversions, and a supervisor that restarts it when it exits. Do not weaken the recycling or timeouts without an ADR.
- **Open a DOCX with LibreOffice's DOCX import filter only,** never format detection, which would convert a `.doc`, RTF, HTML or plain text sent in its place.
- **Work in a per-job scratch directory and wipe it afterwards.**
- **Reject macro-enabled files, enforce file size and page limits, and guard against zip bombs** (DOCX is a zip).
- **Refuse a page whose image would be too large before rendering anything.** A PDF can declare any page size, and at 144 DPI a 200-inch page is a 2.5 GB bitmap. A side over 16,383 pixels (113.7 inches) is refused too, since WebP can't hold it ([WebP FAQ](https://developers.google.com/speed/webp/faq)). The limits are `MAX_PAGE_PIXELS` and `MAX_PAGE_SIDE_PIXELS` in `engine/pages/page_images.py`.
- **Never log document contents.**
