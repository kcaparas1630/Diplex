"""Builds a multipart/form-data body (RFC 7578) from named parts, the way the /render response is sent."""

import secrets
from collections.abc import Sequence
from dataclasses import dataclass

LINE_BREAK = b"\r\n"


@dataclass(frozen=True)
class FormDataPart:
    """One part of a multipart/form-data body: its name, content type, bytes, and file name if it is a file."""

    name: str
    content_type: str
    content: bytes
    filename: str | None = None


def encode_form_data(parts: Sequence[FormDataPart]) -> tuple[bytes, str]:
    """Return the body holding the parts in order, and its Content-Type header with the boundary."""
    boundary = _make_boundary(parts)
    delimiter = b"--" + boundary.encode("ascii")
    body_pieces = []
    for part in parts:
        disposition = f'form-data; name="{part.name}"'
        if part.filename is not None:
            disposition += f'; filename="{part.filename}"'
        part_headers = f"Content-Disposition: {disposition}\r\nContent-Type: {part.content_type}\r\n"
        body_pieces += [delimiter, LINE_BREAK, part_headers.encode("ascii"), LINE_BREAK, part.content, LINE_BREAK]
    body_pieces += [delimiter, b"--", LINE_BREAK]
    return b"".join(body_pieces), f"multipart/form-data; boundary={boundary}"


def _make_boundary(parts: Sequence[FormDataPart]) -> str:
    """Pick a random boundary that appears in none of the parts, as the boundary must not (RFC 2046 §5.1.1)."""
    while True:
        boundary = f"diplex-{secrets.token_hex(16)}"
        if not any(boundary.encode("ascii") in part.content for part in parts):
            return boundary
