"""Tests encode_page_webps on the real PDFs in samples/. A test is skipped when its PDF is missing (see samples/SOURCES.md)."""

import io
import math
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from diplex.engine.pages import encode_page_webps, read_page_sizes, render_page_images

SAMPLES_FOLDER = Path(__file__).resolve().parents[2] / "samples"
LOSSLESS_CHUNK = b"VP8L"  # the image chunk of a lossless WebP, after the 12-byte RIFF header


def _sample_pdf_parameters() -> list:
    """One test parameter per PDF in samples/, or a single skipped parameter when there are none."""
    sample_paths = sorted(SAMPLES_FOLDER.glob("*.pdf"))
    if not sample_paths:
        return [pytest.param(None, marks=pytest.mark.skip(reason=f"no PDF documents in {SAMPLES_FOLDER}"))]
    return [pytest.param(path, id=path.name) for path in sample_paths]


def _sample_bytes(sample_name: str) -> bytes:
    """Read a sample PDF, skipping the test when it isn't in samples/."""
    sample_path = SAMPLES_FOLDER / sample_name
    if not sample_path.exists():
        pytest.skip(f"{sample_name} is not in {SAMPLES_FOLDER}")
    return sample_path.read_bytes()


def _decode(webp_bytes: bytes) -> Image.Image:
    """Decode WebP bytes into a loaded image, checking they are WebP."""
    with Image.open(io.BytesIO(webp_bytes)) as webp_image:
        assert webp_image.format == "WEBP"
        webp_image.load()
        return webp_image.copy()


@pytest.mark.parametrize("sample_path", _sample_pdf_parameters())
def test_every_page_is_a_lossless_webp_of_its_rendered_size(sample_path):
    """Each real PDF gives one lossless WebP per page, named in page order, that decodes to the page's size at 144 DPI."""
    pdf_bytes = sample_path.read_bytes()
    page_sizes = read_page_sizes(pdf_bytes)

    webp_count = 0
    for page_size, page_webp in zip(page_sizes, encode_page_webps(render_page_images(pdf_bytes)), strict=True):
        webp_count += 1
        assert page_webp.filename == f"page-{page_size.index:04d}.webp"
        assert page_webp.webp_bytes[12:16] == LOSSLESS_CHUNK
        decoded_image = _decode(page_webp.webp_bytes)
        assert decoded_image.size == (math.ceil(page_size.width * 2), math.ceil(page_size.height * 2)), page_size
    assert webp_count == len(page_sizes)


@pytest.mark.parametrize("sample_name", ["irs-form-1040-2025.pdf", "uk-employability-support-guidance-chapter-12.pdf"])
def test_each_page_decodes_to_exactly_the_rendered_pixels(sample_name):
    """The IRS form (US Letter, form fields) and the UK guidance (A4) decode to every rendered pixel unchanged."""
    page_images = list(render_page_images(_sample_bytes(sample_name)))
    page_webps = encode_page_webps(page_image.copy() for page_image in page_images)  # copies, as the encoder closes them

    for page_image, page_webp in zip(page_images, page_webps, strict=True):
        decoded_image = _decode(page_webp.webp_bytes)
        assert decoded_image.mode == "RGB"
        assert ImageChops.difference(decoded_image, page_image).getbbox() is None, page_webp.filename
