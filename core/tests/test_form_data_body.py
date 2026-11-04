"""Unit tests for encode_form_data, reading the body back with Python's own MIME parser."""

from email import policy
from email.parser import BytesParser

from diplex.api.form_data import FormDataPart, encode_form_data


def _parse_form_data(body: bytes, content_type: str) -> list:
    """Parse a multipart/form-data body into its parts with the standard library."""
    message = BytesParser(policy=policy.HTTP).parsebytes(f"Content-Type: {content_type}\r\n\r\n".encode() + body)
    assert message.is_multipart()
    return list(message.iter_parts())


def test_parts_come_back_in_order_with_their_names_types_and_bytes():
    """A text part and two file parts with the same name keep their order, headers and exact bytes."""
    parts = [
        FormDataPart(name="manifest", content_type="application/json", content=b'{"pages": []}'),
        FormDataPart(name="page", content_type="image/webp", content=b"RIFF\x00\r\n--\xff", filename="page-0001.webp"),
        FormDataPart(name="page", content_type="image/webp", content=b"RIFF second", filename="page-0002.webp"),
    ]

    body, content_type = encode_form_data(parts)
    parsed_parts = _parse_form_data(body, content_type)

    assert [part.get_param("name", header="content-disposition") for part in parsed_parts] == ["manifest", "page", "page"]
    assert [part.get_filename() for part in parsed_parts] == [None, "page-0001.webp", "page-0002.webp"]
    assert [part.get_content_type() for part in parsed_parts] == ["application/json", "image/webp", "image/webp"]
    assert [part.get_payload(decode=True) for part in parsed_parts] == [part.content for part in parts]


def test_the_content_type_names_the_boundary_used_in_the_body():
    """The header is multipart/form-data with the boundary that delimits the body."""
    body, content_type = encode_form_data([FormDataPart(name="manifest", content_type="application/json", content=b"{}")])

    media_type, boundary_parameter = content_type.split("; ")
    boundary = boundary_parameter.removeprefix("boundary=")
    assert media_type == "multipart/form-data"
    assert body.startswith(f"--{boundary}\r\n".encode())
    assert body.endswith(f"\r\n--{boundary}--\r\n".encode())


def test_each_body_gets_a_new_boundary():
    """Boundaries are random, so a document can't be crafted to contain the one its response will use."""
    parts = [FormDataPart(name="manifest", content_type="application/json", content=b"{}")]

    assert encode_form_data(parts)[1] != encode_form_data(parts)[1]


def test_a_boundary_found_in_a_part_is_not_used(monkeypatch):
    """If the random boundary happens to be in a part's bytes, another one is picked."""
    picked_tokens = iter(["aa" * 16, "bb" * 16])
    monkeypatch.setattr("diplex.api.form_data.form_data_body.secrets.token_hex", lambda _: next(picked_tokens))
    parts = [FormDataPart(name="page", content_type="image/webp", content=b"xx diplex-" + b"aa" * 16 + b" xx")]

    body, content_type = encode_form_data(parts)

    assert content_type.endswith("boundary=diplex-" + "bb" * 16)
    assert _parse_form_data(body, content_type)[0].get_payload(decode=True) == parts[0].content
