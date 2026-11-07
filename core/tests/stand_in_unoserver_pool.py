"""A stand-in for the engine's unoserver pool in API tests: it starts no LibreOffice and converts with a given function."""

from collections.abc import Callable

from diplex.engine import UnoserverUnavailableError


class StandInUnoserverPool:
    """Takes UnoserverPool's place in create_app: records start and stop, and converts with the function it was given."""

    def __init__(self, docx_conversion: Callable[[bytes], bytes] | None = None) -> None:
        """Keep the conversion to use; without one, every conversion fails as with no unoserver running."""
        self.docx_conversion = docx_conversion
        self.started = False
        self.stopped = False

    def start(self) -> None:
        """Note that the app started the pool."""
        self.started = True

    def stop(self) -> None:
        """Note that the app stopped the pool."""
        self.stopped = True

    def convert_docx_to_pdf(self, docx_bytes: bytes) -> bytes:
        """Convert with the given function, or fail as when no unoserver is running."""
        if self.docx_conversion is None:
            raise UnoserverUnavailableError("the stand-in pool has no conversion")
        return self.docx_conversion(docx_bytes)
