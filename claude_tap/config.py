"""Runtime configuration for claude-tap."""

from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

DEFAULT_DASHBOARD_PASSWORD = "admin"
CONFIG_FILENAME = "config.json"

_DEFAULT_CONFIG: dict[str, Any] = {
    "dashboard_password": DEFAULT_DASHBOARD_PASSWORD,
    "capture": {
        "enabled": True,
        "default_save": True,
        "rules": [],
    },
    "cleanup": {
        "max_age_days": 0,
        "max_db_size_mb": 0,
        "only_success": False,
    },
}

_config_lock = threading.Lock()
_config_cache: dict[str, Any] | None = None
_config_path_cache: Path | None = None


def resolve_config_path() -> Path:
    override = os.environ.get("CLOUDTAP_CONFIG", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    from claude_tap.trace_store import resolve_db_path

    return (resolve_db_path().parent / CONFIG_FILENAME).resolve()


def default_config() -> dict[str, Any]:
    return deepcopy(_DEFAULT_CONFIG)


def _merge_defaults(value: dict[str, Any]) -> dict[str, Any]:
    merged = default_config()
    for key, item in value.items():
        if isinstance(item, dict) and isinstance(merged.get(key), dict):
            merged[key].update(item)
        else:
            merged[key] = item
    capture = merged.setdefault("capture", {})
    capture.setdefault("enabled", True)
    capture.setdefault("default_save", True)
    capture.setdefault("rules", [])
    cleanup = merged.setdefault("cleanup", {})
    cleanup.setdefault("max_age_days", 0)
    cleanup.setdefault("max_db_size_mb", 0)
    cleanup.setdefault("only_success", False)
    merged.setdefault("dashboard_password", DEFAULT_DASHBOARD_PASSWORD)
    return merged


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or resolve_config_path()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default_config()
    except (json.JSONDecodeError, OSError):
        return default_config()
    return _merge_defaults(data if isinstance(data, dict) else {})


def save_config(config: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    config_path = path or resolve_config_path()
    normalized = _merge_defaults(config)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    global _config_cache, _config_path_cache
    with _config_lock:
        _config_cache = deepcopy(normalized)
        _config_path_cache = config_path
    return normalized


def get_config() -> dict[str, Any]:
    global _config_cache, _config_path_cache
    path = resolve_config_path()
    with _config_lock:
        if _config_cache is None or _config_path_cache != path:
            _config_cache = load_config(path)
            _config_path_cache = path
        return deepcopy(_config_cache)


def reset_config_cache() -> None:
    global _config_cache, _config_path_cache
    with _config_lock:
        _config_cache = None
        _config_path_cache = None


def verify_password(password: str, config: dict[str, Any] | None = None) -> bool:
    cfg = config or get_config()
    return str(password) == str(cfg.get("dashboard_password", DEFAULT_DASHBOARD_PASSWORD))
