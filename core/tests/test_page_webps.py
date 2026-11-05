"""Unit tests for encode_page_webps, on images made in memory; no documents are generated."""

import io

import pytest
from PIL import Image, ImageChops

from diplex.engine.pages import PageWebp, encode_page_webps

US_LETTER_AT_144_DPI = (1224, 1584)
A4_AT_144_DPI = (1191, 1684)
LOSSLESS_CHUNK = b"VP8L"  # the image chunk of a lossless WebP; a lossy one has "VP8 "


def _noisy_image(pixel_size: tuple[int, int]) -> Image.Image:
    """Make an RGB image of random pixels, which a lossy encoder could not keep exactly."""
    return Image.merge("RGB", [Image.effect_noise(pixel_size, sigma) for sigma in (30, 60, 90)])


def _decode(webp_bytes: bytes) -> Image.Image:
    """Decode WebP bytes into a loaded image, checking they are WebP."""
    with Image.open(io.BytesIO(webp_bytes)) as webp_image:
        assert webp_image.format == "WEBP"
        webp_image.load()
        return webp_image.copy()


def test_pages_are_named_in_page_order():
    """The first page is page-0001.webp, the second page-0002.webp, and so on."""
    page_images = [Image.new("RGB", US_LETTER_AT_144_DPI, "white") for _ in range(3)]

    page_webps = list(encode_page_webps(page_images))

    assert [page_webp.filename for page_webp in page_webps] == ["page-0001.webp", "page-0002.webp", "page-0003.webp"]


def test_each_page_decodes_to_the_same_size_and_pixels():
    """Each WebP decodes to an RGB image of the page image's size with every pixel unchanged."""
    page_images = [_noisy_image(US_LETTER_AT_144_DPI), _noisy_image(A4_AT_144_DPI)]
    page_webps = encode_page_webps(page_image.copy() for page_image in page_images)  # copies, as the encoder closes them

    for page_image, page_webp in zip(page_images, page_webps, strict=True):
        decoded_image = _decode(page_webp.webp_bytes)
        assert (decoded_image.mode, decoded_image.size) == ("RGB", page_image.size)
        assert ImageChops.difference(decoded_image, page_image).getbbox() is None


def test_the_webp_is_lossless():
    """The file's image chunk is VP8L, the lossless format, right after the RIFF and WEBP headers."""
    page_webp = next(encode_page_webps([Image.new("RGB", US_LETTER_AT_144_DPI, "white")]))

    assert page_webp.webp_bytes[:4] == b"RIFF"
    assert page_webp.webp_bytes[8:16] == b"WEBP" + LOSSLESS_CHUNK


def test_encodes_a_page_only_when_it_is_asked_for():
    """The next page image is not taken until the next WebP is asked for, so pages render one at a time."""
    taken_page_numbers = []

    def page_images():
        """Yield blank page images, recording each one taken."""
        for page_number in (1, 2, 3):
            taken_page_numbers.append(page_number)
            yield Image.new("RGB", US_LETTER_AT_144_DPI, "white")

    page_webps = encode_page_webps(page_images())

    assert isinstance(next(page_webps), PageWebp)
    assert taken_page_numbers == [1]
    next(page_webps)
    assert taken_page_numbers == [1, 2]


def test_closes_each_page_image_once_it_is_encoded():
    """A page image's pixels are freed before its WebP is handed over, not when the next page comes."""
    page_images = [Image.new("RGB", US_LETTER_AT_144_DPI, "white") for _ in range(2)]
    page_webps = encode_page_webps(page_images)

    next(page_webps)

    with pytest.raises(ValueError, match="closed image"):
        page_images[0].getpixel((0, 0))
    assert page_images[1].getpixel((0, 0)) == (255, 255, 255)
