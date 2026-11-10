"""Tests that the app runs its unoserver pool for as long as it serves, and converts a DOCX with that pool."""

import io
import zipfile

from fastapi.testclient import TestClient

from diplex.api import create_app
from diplex.definition import RenderErrorCode
from diplex.engine import UnoserverPool
from stand_in_unoserver_pool import StandInUnoserverPool

WORD_CONTENT_TYPES = (
    '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
)


def _word_package() -> bytes:
    """A zip that the type check takes for a DOCX: just a [Content_Types].xml naming a Word document part."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as package:
        package.writestr("[Content_Types].xml", WORD_CONTENT_TYPES)
    return zip_buffer.getvalue()


def test_the_pool_starts_with_the_app_and_stops_at_shutdown():
    """The pool is started before the first request and stopped when the app shuts down, not when it is built."""
    unoserver_pool = StandInUnoserverPool()
    engine_app = create_app(unoserver_pool=unoserver_pool)
    assert not unoserver_pool.started

    with TestClient(engine_app) as client:
        assert unoserver_pool.started and not unoserver_pool.stopped
        assert client.get("/health").status_code == 200

    assert unoserver_pool.stopped


def test_a_docx_is_converted_by_the_apps_pool():
    """/render sends a DOCX to the app's own pool; with nothing to convert it, the upload gets 503."""
    converted_documents = []

    def refuse_and_record(docx_bytes):
        """Record the DOCX and fail as when no instance is running."""
        converted_documents.append(docx_bytes)
        return StandInUnoserverPool().convert_docx_to_pdf(docx_bytes)

    docx_bytes = _word_package()
    with TestClient(create_app(unoserver_pool=StandInUnoserverPool(refuse_and_record))) as client:
        response = client.post("/render", files={"document": ("upload.docx", docx_bytes)})

    assert converted_documents == [docx_bytes]
    assert response.status_code == 503
    assert response.json()["code"] == RenderErrorCode.CONVERTER_UNAVAILABLE


def test_without_a_pool_the_app_builds_one_from_the_environment(monkeypatch):
    """create_app() makes an UnoserverPool from DIPLEX_UNOSERVER_INSTANCES, without starting it."""
    monkeypatch.setenv("DIPLEX_UNOSERVER_INSTANCES", "3")

    engine_app = create_app()

    assert isinstance(engine_app.state.unoserver_pool, UnoserverPool)
    assert engine_app.state.unoserver_pool.settings.instance_count == 3
    assert engine_app.state.unoserver_pool.instances == []
