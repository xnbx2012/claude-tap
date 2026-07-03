"""Shared test helpers for authenticated dashboard requests."""

from __future__ import annotations

import aiohttp

from tests.conftest import TEST_DASHBOARD_PASSWORD


def make_authed_client(*, timeout: aiohttp.ClientTimeout | None = None) -> aiohttp.ClientSession:
    """A client session whose cookie jar stores cookies for IP hosts."""
    return aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar(unsafe=True),
        timeout=timeout,
    )


async def login(client: aiohttp.ClientSession, port: int) -> None:
    """Authenticate the client against the local dashboard."""
    async with client.post(
        f"http://127.0.0.1:{port}/api/auth/login",
        json={"password": TEST_DASHBOARD_PASSWORD},
    ) as resp:
        assert resp.status == 200, await resp.text()
