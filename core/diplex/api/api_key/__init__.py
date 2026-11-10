"""The optional static API key (ADR 012): api_key_setting.py reads it, api_key_check.py checks it on /render."""

from .api_key_check import (
    API_KEY_SCHEME_NAME,
    ApiKeyRejectedError,
    answer_rejected_api_key,
    bearer_scheme,
    require_api_key,
)
from .api_key_setting import API_KEY_VARIABLE, read_api_key

__all__ = [
    "API_KEY_SCHEME_NAME",
    "API_KEY_VARIABLE",
    "ApiKeyRejectedError",
    "answer_rejected_api_key",
    "bearer_scheme",
    "read_api_key",
    "require_api_key",
]
