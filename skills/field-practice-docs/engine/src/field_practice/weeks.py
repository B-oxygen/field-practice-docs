from __future__ import annotations

from datetime import date, timedelta

from field_practice.config import PERIOD_END, PERIOD_START
from field_practice.models import Week

WEEKS: tuple[Week, ...] = tuple(
    Week(
        number=index + 1,
        start=PERIOD_START + timedelta(days=7 * index),
        end=PERIOD_START + timedelta(days=(7 * index) + 6),
    )
    for index in range(16)
)

WEEKDAY_KO: tuple[str, ...] = ("월", "화", "수", "목", "금", "토", "일")


def week_for_date(value: date) -> int | None:
    for week in WEEKS:
        if week.start <= value <= week.end:
            return week.number
    return None


def dates_in_week(week_number: int) -> tuple[date, ...]:
    for week in WEEKS:
        if week.number == week_number:
            return tuple(week.start + timedelta(days=offset) for offset in range(7))
    msg = f"invalid week number: {week_number}"
    raise ValueError(msg)


def weekday_ko(value: date) -> str:
    return WEEKDAY_KO[value.weekday()]


def report_date(value: date) -> str:
    return f"{value.year % 100}/{value.month}/{value.day}"


def in_period(value: date) -> bool:
    return PERIOD_START <= value <= PERIOD_END
