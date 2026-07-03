"""Request identity helpers for claude-tap."""

from __future__ import annotations

from collections.abc import Mapping

SESSION_ID_HEADER = "x-claude-code-session-id"
AUTHORIZATION_HEADER = "authorization"
MAX_IDENTITY_VALUE_CHARS = 2048


def _header_value(headers: Mapping[str, str], name: str) -> str:
    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return _clean_identity_value(str(value))
    return ""


def _clean_identity_value(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch >= " " and ch != "\x7f")
    if len(cleaned) > MAX_IDENTITY_VALUE_CHARS:
        return cleaned[:MAX_IDENTITY_VALUE_CHARS]
    return cleaned


def extract_session_identity(headers: Mapping[str, str]) -> tuple[str, str]:
    """Return (upstream_session_id, user_key) from request headers."""
    return _header_value(headers, SESSION_ID_HEADER), _header_value(headers, AUTHORIZATION_HEADER)
