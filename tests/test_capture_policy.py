from __future__ import annotations

from claude_tap.capture_policy import should_save_record


def _cfg(rules=None, *, enabled=True, default_save=True) -> dict:
    return {"capture": {"enabled": enabled, "default_save": default_save, "rules": rules or []}}


def test_global_disabled_skips_record() -> None:
    assert should_save_record(_cfg(enabled=False), user_key="u", model="m", status=200) is False


def test_default_save_when_no_rule_matches() -> None:
    assert should_save_record(_cfg(default_save=True)) is True
    assert should_save_record(_cfg(default_save=False)) is False


def test_first_matching_rule_wins() -> None:
    rules = [
        {"user_key": "u1", "model": "", "status_filter": "all", "save": False},
        {"user_key": "u1", "model": "", "status_filter": "all", "save": True},
    ]
    assert should_save_record(_cfg(rules), user_key="u1", model="m", status=200) is False


def test_status_filters() -> None:
    # non_200 + save=True: only saves non-200; a 200 falls through to default_save.
    assert (
        should_save_record(_cfg([{"user_key": "", "model": "", "status_filter": "non_200", "save": True}]), status=500)
        is True
    )
    assert (
        should_save_record(
            _cfg([{"user_key": "", "model": "", "status_filter": "non_200", "save": True}], default_save=False),
            status=200,
        )
        is False
    )
    assert (
        should_save_record(_cfg([{"user_key": "", "model": "", "status_filter": "success", "save": True}]), status=200)
        is True
    )
    assert (
        should_save_record(
            _cfg([{"user_key": "", "model": "", "status_filter": "success", "save": True}], default_save=False),
            status=404,
        )
        is False
    )
    assert (
        should_save_record(_cfg([{"user_key": "", "model": "", "status_filter": "429", "save": True}]), status=429)
        is True
    )
    assert (
        should_save_record(
            _cfg([{"user_key": "", "model": "", "status_filter": "429", "save": True}], default_save=False),
            status=200,
        )
        is False
    )


def test_model_filter() -> None:
    rule = {"user_key": "", "model": "claude-opus", "status_filter": "all", "save": False}
    assert should_save_record(_cfg([rule]), model="claude-opus", status=200) is False
    assert should_save_record(_cfg([rule]), model="claude-sonnet", status=200) is True  # falls through to default
