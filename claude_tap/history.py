"""Trace history retention helpers backed by SQLite."""

from __future__ import annotations

from pathlib import Path

from claude_tap.trace_store import get_trace_store


def delete_trace_history(
    date_key: str,
    *,
    protected_session_ids: set[str] | None = None,
) -> dict[str, int | str]:
    """Delete stored trace sessions for a date key."""
    store = get_trace_store()
    try:
        return store.delete_sessions_by_date(date_key, protected_session_ids=protected_session_ids)
    except ValueError as exc:
        raise ValueError("Invalid date format") from exc


def cleanup_trace_sessions(
    max_sessions: int,
    *,
    protected_session_id: str | None = None,
    protected_session_ids: set[str] | None = None,
) -> int:
    """Remove oldest trace sessions exceeding max_sessions."""
    return get_trace_store().cleanup_old_sessions(
        max_sessions,
        protected_session_id=protected_session_id,
        protected_session_ids=protected_session_ids,
    )


def cleanup_trace_history_by_criteria(
    *,
    max_age_days: int = 0,
    max_db_size_mb: int = 0,
    only_success: bool = False,
    dry_run: bool = False,
    protected_session_id: str | None = None,
    protected_session_ids: set[str] | None = None,
) -> dict:
    """Remove trace sessions matching age/size/success criteria."""
    protected = set(protected_session_ids or set())
    if protected_session_id:
        protected.add(protected_session_id)
    return get_trace_store().cleanup_by_criteria(
        max_age_days=max_age_days,
        max_db_size_mb=max_db_size_mb,
        only_success=only_success,
        dry_run=dry_run,
        protected_session_ids=protected or None,
    )


def trace_storage_stats() -> dict:
    """Return storage usage statistics for the dashboard."""
    return get_trace_store().storage_stats()


def migrate_legacy_traces(output_dir: Path) -> int:
    """Import legacy JSONL/log files from an output directory once."""
    return get_trace_store().migrate_legacy_directory(output_dir)


def _rel_posix(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()
