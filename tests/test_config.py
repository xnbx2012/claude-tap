from __future__ import annotations

from pathlib import Path

import pytest

from claude_tap.config import (
    DEFAULT_DASHBOARD_PASSWORD,
    default_config,
    get_config,
    load_config,
    reset_config_cache,
    resolve_config_path,
    save_config,
    verify_password,
)


def test_default_config_has_admin_password() -> None:
    cfg = default_config()
    assert cfg["dashboard_password"] == DEFAULT_DASHBOARD_PASSWORD == "admin"
    assert cfg["capture"]["enabled"] is True
    assert cfg["capture"]["default_save"] is True
    assert cfg["capture"]["rules"] == []
    assert cfg["cleanup"]["max_age_days"] == 0


def test_save_and_load_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.json"
    monkeypatch.setenv("CLOUDTAP_CONFIG", str(path))
    reset_config_cache()
    cfg = default_config()
    cfg["dashboard_password"] = "secret"
    cfg["capture"]["rules"] = [{"user_key": "tok", "model": "m", "status_filter": "all", "save": False}]
    save_config(cfg)
    assert path.exists()
    reset_config_cache()
    loaded = load_config(path)
    assert loaded["dashboard_password"] == "secret"
    assert loaded["capture"]["rules"][0]["user_key"] == "tok"


def test_verify_password(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Drop the autouse-isolated config so get_config() returns defaults (admin password).
    config_path = tmp_path / "config.json"
    if config_path.exists():
        config_path.unlink()
    monkeypatch.setenv("CLOUDTAP_CONFIG", str(config_path))
    reset_config_cache()
    cfg = get_config()
    assert verify_password("admin", cfg) is True
    assert verify_password("wrong", cfg) is False
    cfg["dashboard_password"] = "newpw"
    save_config(cfg)
    reset_config_cache()
    assert verify_password("newpw") is True
    assert verify_password("admin") is False


def test_missing_config_file_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "missing.json"
    loaded = load_config(path)
    assert loaded == default_config()


def test_config_path_follows_cloudtap_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "custom.json"
    monkeypatch.setenv("CLOUDTAP_CONFIG", str(path))
    assert resolve_config_path() == path.resolve()
