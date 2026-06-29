from __future__ import annotations

from field_practice.allocate_time import cap_day, cap_week


def test_cap_day_when_minutes_exceed_limit_then_returns_600() -> None:
    assert cap_day(700) == 600


def test_cap_week_when_minutes_exceed_limit_then_returns_3120() -> None:
    assert cap_week(3500) == 3120


def test_caps_when_minutes_negative_then_returns_zero() -> None:
    assert cap_day(-1) == 0
    assert cap_week(-1) == 0
