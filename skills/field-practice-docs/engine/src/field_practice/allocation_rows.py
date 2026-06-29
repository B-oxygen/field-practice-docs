from __future__ import annotations

from datetime import date

from field_practice.models import Confidence, Scenario, WeeklyRow

CONFIDENCE_RANK: dict[Confidence, int] = {
    Confidence.A_PLUS: 5,
    Confidence.A: 4,
    Confidence.A_CANDIDATE: 3,
    Confidence.B: 3,
    Confidence.C: 2,
    Confidence.D: 1,
}


def merge_weekly_rows(rows: list[WeeklyRow]) -> list[WeeklyRow]:
    merged: dict[tuple[date, str, Scenario], WeeklyRow] = {}
    for row in rows:
        key = (row.record_date, row.activity, row.scenario)
        previous = merged.get(key)
        if previous is None:
            merged[key] = row
            continue
        merged[key] = WeeklyRow(
            week=row.week,
            record_date=row.record_date,
            weekday_ko=row.weekday_ko,
            minutes=previous.minutes + row.minutes,
            activity=row.activity,
            evidence_ids=tuple(sorted({*previous.evidence_ids, *row.evidence_ids})),
            confidence=_stronger_confidence(previous.confidence, row.confidence),
            scenario=row.scenario,
            needs_review=previous.needs_review or row.needs_review,
        )
    return list(merged.values())


def _stronger_confidence(left: Confidence, right: Confidence) -> Confidence:
    if CONFIDENCE_RANK[left] >= CONFIDENCE_RANK[right]:
        return left
    return right
