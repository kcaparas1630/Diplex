"""Reads the upload size limit from the DIPLEX_MAX_UPLOAD_BYTES environment variable."""

import os

MAX_UPLOAD_BYTES_VARIABLE = "DIPLEX_MAX_UPLOAD_BYTES"
DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # provisional until the engine is measured; the largest sample is 3 MB


def read_max_upload_bytes() -> int:
    """Return the upload limit in bytes from DIPLEX_MAX_UPLOAD_BYTES, or the default when it is not set."""
    configured_limit = os.environ.get(MAX_UPLOAD_BYTES_VARIABLE, "").strip()
    if not configured_limit:
        return DEFAULT_MAX_UPLOAD_BYTES
    if not configured_limit.isdecimal() or int(configured_limit) < 1:
        raise ValueError(f"{MAX_UPLOAD_BYTES_VARIABLE} must be a whole number of bytes above 0, not {configured_limit!r}")
    return int(configured_limit)
