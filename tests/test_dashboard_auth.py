from __future__ import annotations

from pathlib import Path

import aiohttp
import pytest

from claude_tap.config import reset_config_cache, save_config
from claude_tap.live import LiveViewerServer


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "config.json"
    monkeypatch.setenv("CLOUDTAP_CONFIG", str(path))
    reset_config_cache()
    yield path
    reset_config_cache()


def _session() -> aiohttp.ClientSession:
    # The default CookieJar ignores IP-address hosts (RFC 6265); tests hit 127.0.0.1.
    return aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))


@pytest.mark.asyncio
async def test_unauth_api_returns_401(trace_db, isolated_config) -> None:
    save_config({"dashboard_password": "secret"})
    server = LiveViewerServer(port=0, dashboard_mode=True)
    port = await server.start()
    try:
        async with _session() as session:
            async with session.get(f"http://127.0.0.1:{port}/api/sessions") as resp:
                assert resp.status == 401
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_login_then_access(trace_db, isolated_config) -> None:
    save_config({"dashboard_password": "secret"})
    server = LiveViewerServer(port=0, dashboard_mode=True)
    port = await server.start()
    try:
        async with _session() as session:
            async with session.post(
                f"http://127.0.0.1:{port}/api/auth/login",
                json={"password": "secret"},
            ) as resp:
                assert resp.status == 200
            async with session.get(f"http://127.0.0.1:{port}/api/sessions") as resp:
                assert resp.status == 200
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_wrong_password_rejected(trace_db, isolated_config) -> None:
    save_config({"dashboard_password": "secret"})
    server = LiveViewerServer(port=0, dashboard_mode=True)
    port = await server.start()
    try:
        async with _session() as session:
            async with session.post(
                f"http://127.0.0.1:{port}/api/auth/login",
                json={"password": "wrong"},
            ) as resp:
                assert resp.status == 401
            async with session.get(f"http://127.0.0.1:{port}/api/sessions") as resp:
                assert resp.status == 401
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_health_is_public(trace_db, isolated_config) -> None:
    save_config({"dashboard_password": "secret"})
    server = LiveViewerServer(port=0, dashboard_mode=True)
    port = await server.start()
    try:
        async with _session() as session:
            async with session.get(f"http://127.0.0.1:{port}/dashboard/health") as resp:
                assert resp.status == 200
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_change_password_persists(trace_db, isolated_config) -> None:
    from claude_tap.config import get_config

    save_config({"dashboard_password": "old"})
    server = LiveViewerServer(port=0, dashboard_mode=True)
    port = await server.start()
    try:
        async with _session() as session:
            async with session.post(f"http://127.0.0.1:{port}/api/auth/login", json={"password": "old"}) as resp:
                assert resp.status == 200
            async with session.put(f"http://127.0.0.1:{port}/api/auth/password", json={"password": "newpw"}) as resp:
                assert resp.status == 200
    finally:
        await server.stop()
    reset_config_cache()
    assert get_config()["dashboard_password"] == "newpw"


@pytest.mark.asyncio
async def test_settings_and_storage_endpoints(trace_db, isolated_config) -> None:
    save_config({"dashboard_password": "secret", "capture": {"enabled": False, "default_save": True, "rules": []}})
    server = LiveViewerServer(port=0, dashboard_mode=True)
    port = await server.start()
    try:
        async with _session() as session:
            async with session.post(f"http://127.0.0.1:{port}/api/auth/login", json={"password": "secret"}) as resp:
                assert resp.status == 200
            async with session.get(f"http://127.0.0.1:{port}/api/settings") as resp:
                assert resp.status == 200
                payload = await resp.json()
                assert payload["capture"]["enabled"] is False
            async with session.get(f"http://127.0.0.1:{port}/api/storage/stats") as resp:
                assert resp.status == 200
                stats = await resp.json()
                assert "db_size_bytes" in stats
            async with session.post(
                f"http://127.0.0.1:{port}/api/storage/cleanup/preview",
                json={"max_age_days": 1, "max_db_size_mb": 0, "only_success": False},
            ) as resp:
                assert resp.status == 200
                preview = await resp.json()
                assert "deleted_sessions" in preview
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_users_and_upstream_sessions_endpoints(trace_db, isolated_config) -> None:
    from claude_tap.trace_store import get_trace_store

    save_config({"dashboard_password": "secret"})
    store = get_trace_store()
    s1 = store.create_session(client="claude", proxy_mode="reverse", user_key="tok-a", upstream_session_id="up-1")
    store.append_record(s1, {"turn": 1})
    server = LiveViewerServer(port=0, dashboard_mode=True)
    port = await server.start()
    try:
        async with _session() as session:
            async with session.post(f"http://127.0.0.1:{port}/api/auth/login", json={"password": "secret"}) as resp:
                assert resp.status == 200
            async with session.get(f"http://127.0.0.1:{port}/api/users") as resp:
                assert resp.status == 200
                users = (await resp.json())["users"]
                assert any(u["key"] == "tok-a" for u in users)
            async with session.get(f"http://127.0.0.1:{port}/api/upstream-sessions?user=tok-a") as resp:
                assert resp.status == 200
                upstream = (await resp.json())["sessions"]
                assert any(u["key"] == "up-1" for u in upstream)
    finally:
        await server.stop()
