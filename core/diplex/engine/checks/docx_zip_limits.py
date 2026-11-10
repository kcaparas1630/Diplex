"""Guards against zip bombs in a DOCX (convention 003): checks its zip headers, then reads every part within its declared size.

The limits are provisional until the engine is measured on the samples (issue #53); the largest sample is 3 MB.
"""

import io
import zipfile

from .docx_package import UNREADABLE_ZIP_ERRORS

MAX_PART_COUNT = 10_000  # a long report has a few hundred parts
MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024  # all parts together, unzipped; about half an instance's 1 GB budget (ADR 004)
MAX_COMPRESSION_RATIO = 100  # unzipped over zipped size, for any part above RATIO_CHECK_MIN_BYTES
RATIO_CHECK_MIN_BYTES = 1024 * 1024  # small parts of repeated XML compress well and harm nothing
READ_CHUNK_BYTES = 1024 * 1024


class DocxLimitsExceededError(Exception):
    """The DOCX would unzip into too many parts, too many bytes, or a part that expands too much."""


class DamagedDocxError(Exception):
    """The DOCX's zip data doesn't match its headers: a part is cut short, overlaps another or fails its checksum."""


def check_docx_zip_limits(docx_bytes: bytes) -> None:
    """Raise DocxLimitsExceededError if the zip headers break a limit, or DamagedDocxError if a part lies about its size."""
    try:
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as package:
            part_infos = package.infolist()
            _check_headers(part_infos)
            # The headers can lie; zipfile stops each part at its declared size and checks its CRC, so a lie fails here.
            for part_info in part_infos:
                with package.open(part_info) as part_file:
                    while part_file.read(READ_CHUNK_BYTES):
                        pass
    except UNREADABLE_ZIP_ERRORS as error:
        raise DamagedDocxError("the DOCX's zip data is damaged or doesn't match its headers") from error


def _check_headers(part_infos: list[zipfile.ZipInfo]) -> None:
    """Check the part count, the total unzipped size and each large part's compression ratio from the zip headers."""
    if len(part_infos) > MAX_PART_COUNT:
        raise DocxLimitsExceededError(f"the DOCX has {len(part_infos):,} parts, over the limit of {MAX_PART_COUNT:,}")
    uncompressed_bytes = sum(part_info.file_size for part_info in part_infos)
    if uncompressed_bytes > MAX_UNCOMPRESSED_BYTES:
        raise DocxLimitsExceededError(
            f"the DOCX unzips to {uncompressed_bytes / 1024**2:,.0f} MiB, over the limit of {MAX_UNCOMPRESSED_BYTES // 1024**2} MiB"
        )
    for part_info in part_infos:
        compression_ratio = part_info.file_size / max(part_info.compress_size, 1)
        if part_info.file_size > RATIO_CHECK_MIN_BYTES and compression_ratio > MAX_COMPRESSION_RATIO:
            raise DocxLimitsExceededError(
                f"a part of the DOCX expands {compression_ratio:,.0f} times, over the limit of {MAX_COMPRESSION_RATIO}"
            )
