from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from field_practice.config import TIMEZONE

SEOUL = ZoneInfo(TIMEZONE)


def parse_local_date(raw: str) -> date:
    value = raw.strip()
    if len(value) == 8 and value.isdigit():
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    if value.endswith("Z"):
        parsed = datetime.fromisoformat(value)
        return parsed.astimezone(SEOUL).date()
    if "T" in value or " " in value:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=SEOUL)
        return parsed.astimezone(SEOUL).date()
    return date.fromisoformat(value)


def parse_local_datetime(raw: str) -> datetime:
    value = raw.strip()
    if len(value) == 8 and value.isdigit():
        return datetime(
            int(value[:4]),
            int(value[4:6]),
            int(value[6:8]),
            tzinfo=SEOUL,
        )
    if value.endswith("Z"):
        return datetime.fromisoformat(value).astimezone(SEOUL)
    normalized = (
        value.replace(" ", "T", 1) if " " in value and "T" not in value else value
    )
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=SEOUL)
    return parsed.astimezone(SEOUL)


def duration_minutes(start: str, end: str) -> int:
    start_dt = parse_local_datetime(start)
    end_dt = parse_local_datetime(end)
    minutes = int(
        (end_dt.astimezone(UTC) - start_dt.astimezone(UTC)).total_seconds() // 60
    )
    return max(minutes, 0)
