from __future__ import annotations

from datetime import date

from field_practice.weeks import week_for_date


def test_week_for_date_when_period_boundaries_then_maps_expected_weeks() -> None:
    assert week_for_date(date(2026, 3, 2)) == 1
    assert week_for_date(date(2026, 3, 8)) == 1
    assert week_for_date(date(2026, 3, 9)) == 2
    assert week_for_date(date(2026, 6, 21)) == 16
