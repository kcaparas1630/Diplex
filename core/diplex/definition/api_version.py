"""The API version every /render request sends in a header (ADR 012), and the versions this engine serves."""

API_VERSION_HEADER = "Diplex-Api-Version"
CURRENT_API_VERSION = "1"
SUPPORTED_API_VERSIONS = (CURRENT_API_VERSION,)  # a release keeps the previous version for at least one more release
