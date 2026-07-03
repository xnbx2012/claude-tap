"""Capture policy engine: decide whether a trace record should be persisted."""

from __future__ import annotations

from typing import Any


def _status_matches(status_filter: str, status: int) -> bool:
    status_filter = (status_filter or "all").strip().lower()
    if not status_filter or status_filter == "all":
        return True
    if status_filter == "success":
        return 200 <= status < 300
    if status_filter == "non_200":
        return status != 200
    if status_filter.isdigit():
        return status == int(status_filter)
    return True


def _rule_matches(rule: dict[str, Any], *, user_key: str, model: str, status: int) -> bool:
    rule_user = str(rule.get("user_key") or "").strip()
    if rule_user and rule_user != user_key:
        return False
    rule_model = str(rule.get("model") or "").strip()
    if rule_model and rule_model != model:
        return False
    return _status_matches(str(rule.get("status_filter") or "all"), status)


def should_save_record(config: dict[str, Any], *, user_key: str = "", model: str = "", status: int = 0) -> bool:
    """Return whether a trace record should be persisted per the capture policy."""
    capture = config.get("capture") if isinstance(config, dict) else None
    if not isinstance(capture, dict):
        return True
    if not capture.get("enabled", True):
        return False
    rules = capture.get("rules")
    if isinstance(rules, list):
        for rule in rules:
            if isinstance(rule, dict) and _rule_matches(rule, user_key=user_key, model=model, status=status):
                return bool(rule.get("save", True))
    return bool(capture.get("default_save", True))
