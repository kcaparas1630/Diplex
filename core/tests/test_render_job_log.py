"""Tests the render job log: one line per job with its facts, and no document contents, file names or bytes."""

import logging
import re
from pathlib import Path

import pypdfium2
import pytest
from fastapi.testclient import TestClient

from diplex.api import create_app, render_route
from diplex.api.job_log import log_unexpected_error, logged_render_job, render_job_logger, send_job_logs_to_stderr
from diplex.definition import RenderError, RenderErrorCode

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
SECRET_FILE_NAME = "board-minutes-acquisition-of-contoso.pdf"
JOB_LINE = re.compile(
    r"^render job=(?P<job_id>[0-9a-f]{32}) source=(?P<source>\w+) bytes=(?P<size>\d+) pages=(?P<pages>[\d-]+) "
    r"duration_ms=(?P<duration>\d+) outcome=(?P<outcome>\w+)$"
)


def _sample_bytes(sample_name: str) -> bytes:
    """Read a sample, skipping the test when it isn't in samples/."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")
    return sample_path.read_bytes()


def _document_words(pdf_bytes: bytes) -> set[str]:
    """Every word of 8 letters or more in the PDF's text, to look for in the logs."""
    pdf_document = pypdfium2.PdfDocument(pdf_bytes)
    try:
        page_texts = []
        for page in pdf_document:
            text_page = page.get_textpage()
            page_texts.append(text_page.get_text_range())
            text_page.close()
            page.close()
    finally:
        pdf_document.close()
    return set(re.findall(r"[A-Za-z]{8,}", " ".join(page_texts)))


def _post_render(document_bytes: bytes, file_name: str = SECRET_FILE_NAME):
    """Send the bytes to /render as the document part of an upload."""
    with TestClient(create_app()) as client:
        return client.post("/render", files={"document": (file_name, document_bytes, "application/pdf")})


def _job_lines(caplog) -> list[re.Match]:
    """The job lines logged so far, parsed."""
    job_messages = [record.getMessage() for record in caplog.records if record.name == render_job_logger.name]
    return [job_line for job_line in map(JOB_LINE.match, job_messages) if job_line is not None]


def _all_logged_text(caplog) -> str:
    """Every message logged by any logger during the test, as one string."""
    return "\n".join(record.getMessage() for record in caplog.records)


def test_a_rendered_pdf_logs_one_line_with_its_facts_and_none_of_its_text(caplog):
    """The UN resolution logs its ID, type, size, 12 pages, duration and ok, but no word of it and not its file name."""
    caplog.set_level(logging.DEBUG)
    pdf_bytes = _sample_bytes("un-resolution-78-1-en.pdf")
    document_words = _document_words(pdf_bytes)

    response = _post_render(pdf_bytes)

    assert response.status_code == 200
    (job_line,) = _job_lines(caplog)
    assert (job_line["source"], job_line["size"], job_line["pages"], job_line["outcome"]) == (
        "pdf",
        str(len(pdf_bytes)),
        "12",
        "ok",
    )
    logged_text = _all_logged_text(caplog)
    assert len(document_words) > 100  # the check below means something
    assert not [word for word in document_words if word in logged_text]
    assert SECRET_FILE_NAME not in logged_text
    assert "%PDF" not in logged_text


def test_a_refused_upload_logs_its_code_without_its_contents(caplog):
    """A text file is refused with its code as the outcome, and neither its text nor its name is logged."""
    caplog.set_level(logging.DEBUG)
    secret_text = b"Quarterly payroll for Jane Example: 123-45-6789\n"

    response = _post_render(secret_text, file_name="payroll-jane-example.txt")

    assert response.status_code == 415
    (job_line,) = _job_lines(caplog)
    assert (job_line["source"], job_line["pages"], job_line["outcome"]) == ("unknown", "-", "unsupported_document_type")
    assert [record.levelname for record in caplog.records if record.name == render_job_logger.name] == ["WARNING"]
    logged_text = _all_logged_text(caplog)
    assert "payroll" not in logged_text.lower()
    assert "123-45-6789" not in logged_text


def test_a_failure_logs_its_type_and_stack_but_not_its_message(caplog, monkeypatch):
    """An unexpected error whose message quotes the document is logged without that message, and answered with 500."""
    caplog.set_level(logging.DEBUG)

    def fail_quoting_the_document(pdf_bytes):
        """Fail with a message that quotes the document, as a library error might."""
        raise ValueError(f"could not parse {pdf_bytes[:60]!r}")

    monkeypatch.setattr(render_route, "render_pdf", fail_quoting_the_document)

    response = _post_render(b"%PDF-1.7\n% Merger terms: Contoso pays 4.2 billion\n")

    assert response.status_code == 500
    error = RenderError.model_validate_json(response.content)
    (job_line,) = _job_lines(caplog)
    assert error.code is RenderErrorCode.INTERNAL_ERROR
    assert job_line["job_id"] in error.message
    assert job_line["outcome"] == "internal_error"
    logged_text = _all_logged_text(caplog)
    assert f"render job={job_line['job_id']} failed with ValueError" in logged_text
    assert "fail_quoting_the_document" in logged_text  # the stack is there to debug with
    assert "Merger" not in logged_text and "Contoso" not in logged_text


def test_the_line_is_logged_even_when_the_job_raises(caplog):
    """A job that raises still logs its line before the error goes on."""
    caplog.set_level(logging.INFO, logger=render_job_logger.name)

    with pytest.raises(RuntimeError), logged_render_job(size_bytes=10) as render_job:
        render_job.outcome = "internal_error"
        raise RuntimeError("failed")

    (job_line,) = _job_lines(caplog)
    assert (job_line["size"], job_line["outcome"]) == ("10", "internal_error")
    assert caplog.records[-1].levelname == "ERROR"


def test_log_unexpected_error_leaves_out_the_message(caplog):
    """Only the type and the stack are logged."""
    caplog.set_level(logging.INFO, logger=render_job_logger.name)
    with logged_render_job(size_bytes=1) as render_job:
        document_text = "text from the document"  # the stack shows source lines, so the text comes from a value
        try:
            raise KeyError(document_text)
        except KeyError as error:
            log_unexpected_error(render_job, error)

    assert "failed with KeyError" in caplog.records[0].getMessage()
    assert "text from the document" not in _all_logged_text(caplog)


def test_job_logs_go_to_stderr_through_one_handler():
    """Building the app twice doesn't print each job line twice."""
    create_app()
    create_app()
    send_job_logs_to_stderr()

    assert len(render_job_logger.handlers) == 1
    assert render_job_logger.level == logging.INFO


def test_a_malformed_upload_leaves_none_of_its_bytes_in_the_logs(caplog):
    """python-multipart's warning quotes the byte it stopped at; it is kept out, and the client still gets 400."""
    caplog.set_level(logging.DEBUG)

    with TestClient(create_app()) as client:
        response = client.post(
            "/render", content=b"Zebra payroll", headers={"content-type": "multipart/form-data; boundary=missing"}
        )

    assert response.status_code == 400
    assert not [record for record in caplog.records if record.name.startswith("python_multipart")]
