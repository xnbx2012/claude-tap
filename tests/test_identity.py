from __future__ import annotations

from claude_tap.identity import extract_session_identity


def test_extract_reads_session_id_and_authorization_case_insensitively() -> None:
    headers = {"X-Claude-Code-Session-Id": "abc-123", "Authorization": "Bearer secret-token"}
    assert extract_session_identity(headers) == ("abc-123", "Bearer secret-token")

    lower = {"x-claude-code-session-id": "s1", "authorization": "Basic abc"}
    assert extract_session_identity(lower) == ("s1", "Basic abc")


def test_extract_returns_empty_when_missing() -> None:
    assert extract_session_identity({}) == ("", "")


def test_extract_trims_whitespace() -> None:
    headers = {"x-claude-code-session-id": "  padded  ", "authorization": "\tBearer x\n"}
    upstream, user = extract_session_identity(headers)
    assert upstream == "padded"
    assert user == "Bearer x"


def test_extract_truncates_oversized_values() -> None:
    headers = {"x-claude-code-session-id": "x" * 5000, "authorization": "y" * 5000}
    upstream, user = extract_session_identity(headers)
    assert len(upstream) <= 2048
    assert len(user) <= 2048
