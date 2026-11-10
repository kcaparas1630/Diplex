"""Reads the page limit from the DIPLEX_MAX_PAGES environment variable."""

import os

MAX_PAGES_VARIABLE = "DIPLEX_MAX_PAGES"
DEFAULT_MAX_PAGES = 500  # provisional until the engine is measured (#53); at the median 70 KB a page, a 35 MB response


def read_max_pages() -> int:
    """Return the page limit from DIPLEX_MAX_PAGES, or the default when it is not set."""
    configured_limit = os.environ.get(MAX_PAGES_VARIABLE, "").strip()
    if not configured_limit:
        return DEFAULT_MAX_PAGES
    if not configured_limit.isdecimal() or int(configured_limit) < 1:
        raise ValueError(f"{MAX_PAGES_VARIABLE} must be a whole number of pages above 0, not {configured_limit!r}")
    return int(configured_limit)
