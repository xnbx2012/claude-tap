from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from claude_tap.trace_store import SessionQuery, get_trace_store, reset_trace_store


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDTAP_DB", str(tmp_path / "t.sqlite3"))
    reset_trace_store()
    yield get_trace_store()
    reset_trace_store()


def test_create_session_with_identity(store) -> None:
    sid = store.create_session(client="claude", proxy_mode="reverse", upstream_session_id="up-1", user_key="tok-a")
    row = store.load_session_row(sid)
    assert row["upstream_session_id"] == "up-1"
    assert row["user_key"] == "tok-a"


def test_attach_identity_only_sets_empty_columns(store) -> None:
    sid = store.create_session(client="claude", proxy_mode="reverse", user_key="tok-a")
    store.attach_upstream_identity(sid, upstream_session_id="up-1", user_key="tok-b")
    row = store.load_session_row(sid)
    assert row["user_key"] == "tok-a"  # not overwritten
    assert row["upstream_session_id"] == "up-1"


def test_user_buckets(store) -> None:
    s1 = store.create_session(client="claude", proxy_mode="reverse", user_key="tok-a")
    s2 = store.create_session(client="claude", proxy_mode="reverse", user_key="tok-a")
    s3 = store.create_session(client="claude", proxy_mode="reverse", user_key="tok-b")
    store.append_record(s1, {"turn": 1})
    store.append_record(s2, {"turn": 1})
    store.append_record(s3, {"turn": 1})
    buckets = {row["key"]: row for row in store.list_user_buckets()}
    assert buckets["tok-a"]["sessions"] == 2
    assert buckets["tok-b"]["sessions"] == 1


def test_upstream_session_buckets_filter_by_user(store) -> None:
    s1 = store.create_session(client="claude", proxy_mode="reverse", upstream_session_id="up-1", user_key="tok-a")
    s2 = store.create_session(client="claude", proxy_mode="reverse", upstream_session_id="up-2", user_key="tok-b")
    store.append_record(s1, {"turn": 1})
    store.append_record(s2, {"turn": 1})
    filtered = {row["key"] for row in store.list_upstream_session_buckets("tok-a")}
    assert filtered == {"up-1"}


def test_session_query_filters_by_user_and_upstream(store) -> None:
    s1 = store.create_session(client="claude", proxy_mode="reverse", user_key="tok-a")
    s2 = store.create_session(client="claude", proxy_mode="reverse", user_key="tok-b")
    store.append_record(s1, {"turn": 1})
    store.append_record(s2, {"turn": 1})
    rows = store.list_session_rows(query=SessionQuery(user_key="tok-a"))
    assert {r["id"] for r in rows} == {s1}


def test_find_active_session_by_upstream_id(store) -> None:
    s1 = store.create_session(client="claude", proxy_mode="reverse", upstream_session_id="up-x")
    found = store.find_active_session_by_upstream_id("up-x")
    assert found is not None
    assert found["id"] == s1
    assert store.find_active_session_by_upstream_id("missing") is None


def test_storage_stats_and_cleanup(store) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=40)
    s1 = store.create_session(client="claude", proxy_mode="reverse", started_at=old)
    store.append_record(s1, {"turn": 1, "timestamp": old.isoformat()})
    # Mark it old by manipulating updated_at
    conn = store._connect()
    conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (old.isoformat(), s1))
    conn.commit()
    s2 = store.create_session(client="claude", proxy_mode="reverse")
    store.append_record(s2, {"turn": 1})

    stats = store.storage_stats()
    assert stats["session_count"] == 2
    assert stats["record_count"] == 2

    preview = store.cleanup_by_criteria(max_age_days=7, dry_run=True)
    assert preview["deleted_sessions"] == 1
    assert store.storage_stats()["session_count"] == 2  # dry run does not delete

    result = store.cleanup_by_criteria(max_age_days=7, dry_run=False)
    assert result["deleted_sessions"] == 1
    assert store.storage_stats()["session_count"] == 1


def test_cleanup_protects_session(store) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=40)
    s1 = store.create_session(client="claude", proxy_mode="reverse", started_at=old)
    store.append_record(s1, {"turn": 1, "timestamp": old.isoformat()})
    conn = store._connect()
    conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (old.isoformat(), s1))
    conn.commit()
    result = store.cleanup_by_criteria(max_age_days=7, protected_session_ids={s1})
    assert result["deleted_sessions"] == 0
