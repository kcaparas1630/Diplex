"""The API version header (ADR 012): api_version_check.py refuses /render requests without a version this engine serves."""

from .api_version_check import UnsupportedApiVersionError, answer_unsupported_api_version, require_supported_api_version

__all__ = ["UnsupportedApiVersionError", "answer_unsupported_api_version", "require_supported_api_version"]
