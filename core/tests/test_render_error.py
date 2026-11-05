"""Unit tests for RenderError, the JSON body of an error response."""

import json

from diplex.definition import RenderError, RenderErrorCode


def test_json_is_the_code_and_the_message():
    """An error is sent as {"code": ..., "message": ...} and nothing else."""
    error = RenderError(code=RenderErrorCode.UPLOAD_TOO_LARGE, message="the upload is over the limit")

    assert json.loads(error.model_dump_json()) == {"code": "upload_too_large", "message": "the upload is over the limit"}


def test_codes_are_the_ones_consumers_branch_on():
    """The codes so far, as sent on the wire."""
    assert [code.value for code in RenderErrorCode] == [
        "upload_too_large",
        "unsupported_document_type",
        "unreadable_pdf",
        "page_too_large",
        "converter_unavailable",
        "internal_error",
    ]


def test_unknown_fields_are_ignored():
    """Fields a newer engine adds don't break reading an error, as with the manifest."""
    error = RenderError.model_validate({"code": "upload_too_large", "message": "too large", "limit": 10})

    assert error == RenderError(code=RenderErrorCode.UPLOAD_TOO_LARGE, message="too large")
