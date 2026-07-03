from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from claude_tap import parse_args
from claude_tap.cli import async_main
from claude_tap.trace_store import get_trace_store, reset_trace_store


def test_parse_args_accepts_web_proxy_mode() -> None:
    args = parse_args(["--tap-proxy-mode", "web_proxy"])

    assert args.proxy_mode == "web_proxy"
    assert args.host == "0.0.0.0"


def test_parse_args_web_proxy_defaults_to_all_interfaces() -> None:
    args = parse_args(["--tap-proxy-mode", "web_proxy"])

    assert args.proxy_mode == "web_proxy"
    assert args.host == "0.0.0.0"


def test_parse_args_web_proxy_explicit_loopback_overrides_default() -> None:
    args = parse_args(["--tap-proxy-mode", "web_proxy", "--tap-host", "127.0.0.1"])

    assert args.proxy_mode == "web_proxy"
    assert args.host == "127.0.0.1"


def test_parse_args_allows_trust_ca_with_web_proxy() -> None:
    args = parse_args(["--tap-proxy-mode", "web_proxy", "--tap-trust-ca"])

    assert args.proxy_mode == "web_proxy"
    assert args.trust_ca is True


def test_parse_args_codexapp_rejects_web_proxy_mode() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--tap-client", "codexapp", "--tap-proxy-mode", "web_proxy"])


@pytest.mark.asyncio
async def test_async_main_web_proxy_starts_forward_server_without_launching_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ca_path = tmp_path / "ca.pem"
    key_path = tmp_path / "ca-key.pem"
    captured: dict[str, object] = {}
    monkeypatch.setenv("CLOUDTAP_DB", str(tmp_path / "web-proxy.sqlite3"))
    reset_trace_store()

    class FakeCertificateAuthority:
        def __init__(self, cert_path: Path, key_path: Path) -> None:
            captured["ca_paths"] = (cert_path, key_path)

    class FakeForwardProxyServer:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs
            captured["stopped"] = False

        async def start(self) -> int:
            captured["started"] = True
            return 4567

        async def stop(self) -> None:
            captured["stopped"] = True

    async def fail_run_client(*args, **kwargs):
        raise AssertionError("web_proxy mode must not launch a client")

    async def cancel_sleep(delay: float) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr("claude_tap.cli.ensure_ca", lambda: (ca_path, key_path))
    monkeypatch.setattr("claude_tap.cli.CertificateAuthority", FakeCertificateAuthority)
    monkeypatch.setattr("claude_tap.cli.ForwardProxyServer", FakeForwardProxyServer)
    monkeypatch.setattr("claude_tap.cli.run_client", fail_run_client)
    monkeypatch.setattr("claude_tap.cli.asyncio.sleep", cancel_sleep)

    args = parse_args(
        [
            "--tap-proxy-mode",
            "web_proxy",
            "--tap-no-live",
            "--tap-no-open",
            "--tap-no-update-check",
            "--tap-max-traces",
            "0",
        ]
    )

    code = await async_main(args)

    assert code == 0
    assert captured["started"] is True
    assert captured["stopped"] is True
    kwargs = captured["kwargs"]
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 0
    assert kwargs["local_reverse_target"] is None
    assert kwargs["local_reverse_allowed_path_prefixes"] == ()
    assert kwargs["store_stream_events"] is False
    assert kwargs["capture_only"] is False

    out = capsys.readouterr().out
    assert "web proxy on http://0.0.0.0:4567" in out
    assert "Keep the provider/model base URL set to its original upstream address." in out
    assert "WARNING: proxy is exposed to the local network." in out
    assert "web_proxy mode: proxy running" in out

    rows = get_trace_store().list_session_rows()
    assert len(rows) == 1
    assert rows[0]["client"] == "web_proxy"
    assert rows[0]["proxy_mode"] == "web_proxy"
