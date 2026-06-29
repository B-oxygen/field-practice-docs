from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from field_practice.allocation_rows import merge_weekly_rows
from field_practice.config import MAX_DAY_MINUTES, MAX_WEEK_MINUTES, FillStep
from field_practice.models import (
    AllocationRequest,
    AllocationResult,
    ALogRecord,
    Confidence,
    Evidence,
    Scenario,
    TimeEntry,
    WeeklyALogRecord,
    WeeklyRow,
)
from field_practice.weeks import weekday_ko

CONFIDENCE_RANK: dict[Confidence, int] = {
    Confidence.A_PLUS: 5,
    Confidence.A: 4,
    Confidence.A_CANDIDATE: 3,
    Confidence.B: 3,
    Confidence.C: 2,
    Confidence.D: 1,
}


@dataclass(frozen=True, slots=True)
class EvidenceDay:
    record_date: date
    week: int
    evidence_ids: tuple[str, ...]
    confidence: Confidence
    activity: str
    capacity_minutes: int


def cap_day(minutes: int) -> int:
    return min(max(minutes, 0), MAX_DAY_MINUTES)


def cap_week(minutes: int) -> int:
    return min(max(minutes, 0), MAX_WEEK_MINUTES)


def allocate_scenario(
    request: AllocationRequest,
    fill_steps: tuple[FillStep, ...],
    evidence: tuple[Evidence, ...],
    alog_records: tuple[ALogRecord, ...],
    weekly_records: tuple[WeeklyALogRecord, ...] = (),
) -> AllocationResult:
    days = _evidence_days(evidence, alog_records, weekly_records)
    weekly_by_week = {record.week: record for record in weekly_records}
    rows: list[WeeklyRow] = []
    entries: list[TimeEntry] = []
    allocated_by_day: dict[date, int] = defaultdict(int)
    allocated_by_week: dict[int, int] = defaultdict(int)
    remaining_target = max(request.target_minutes - request.base_current_minutes, 0)
    for step in fill_steps:
        requested = min(step.minutes, remaining_target)
        allocated = _allocate_step(
            request.scenario,
            step.week,
            requested,
            days,
            rows,
            entries,
            allocated_by_day,
            allocated_by_week,
            weekly_by_week,
        )
        remaining_target -= allocated
        if allocated < requested:
            entries.append(
                TimeEntry(
                    record_date=_fallback_date(days, step.week),
                    week=step.week,
                    raw_minutes=0,
                    proposed_minutes=0,
                    capped_day_minutes=0,
                    capped_week_minutes=_capped_week_total(
                        step.week, allocated_by_week[step.week], weekly_by_week
                    ),
                    scenario=request.scenario,
                    evidence_ids=(),
                    needs_review=True,
                    reason=(
                        f"GitHub/Calendar 증빙 부족으로 {requested - allocated}분 미배정"
                    ),
                ),
            )
    merged_rows = merge_weekly_rows(rows)
    allocated_minutes = sum(row.minutes for row in merged_rows)
    shortage = max(
        request.target_minutes - request.base_current_minutes - allocated_minutes, 0
    )
    return AllocationResult(
        scenario=request.scenario,
        rows=tuple(
            sorted(merged_rows, key=lambda row: (row.record_date, row.activity))
        ),
        time_entries=tuple(
            sorted(entries, key=lambda row: (row.record_date, row.reason))
        ),
        base_current_minutes=request.base_current_minutes,
        target_minutes=request.target_minutes,
        allocated_minutes=allocated_minutes,
        shortage_minutes=shortage,
    )


def _allocate_step(
    scenario: Scenario,
    week: int,
    requested_minutes: int,
    days: tuple[EvidenceDay, ...],
    rows: list[WeeklyRow],
    entries: list[TimeEntry],
    allocated_by_day: dict[date, int],
    allocated_by_week: dict[int, int],
    weekly_by_week: dict[int, WeeklyALogRecord],
) -> int:
    allocated = 0
    for day in days:
        if day.week != week or allocated >= requested_minutes:
            continue
        day_left = MAX_DAY_MINUTES - allocated_by_day[day.record_date]
        week_left = _week_remaining(week, allocated_by_week[week], weekly_by_week)
        capacity_left = day.capacity_minutes - allocated_by_day[day.record_date]
        proposed = min(
            requested_minutes - allocated, day_left, week_left, capacity_left
        )
        if proposed <= 0:
            continue
        allocated_by_day[day.record_date] += proposed
        allocated_by_week[week] += proposed
        allocated += proposed
        rows.append(
            WeeklyRow(
                week=week,
                record_date=day.record_date,
                weekday_ko=weekday_ko(day.record_date),
                minutes=proposed,
                activity=day.activity,
                evidence_ids=day.evidence_ids,
                confidence=day.confidence,
                scenario=scenario,
                needs_review=False,
            ),
        )
        entries.append(
            TimeEntry(
                record_date=day.record_date,
                week=week,
                raw_minutes=day.capacity_minutes,
                proposed_minutes=proposed,
                capped_day_minutes=allocated_by_day[day.record_date],
                capped_week_minutes=_capped_week_total(
                    week, allocated_by_week[week], weekly_by_week
                ),
                scenario=scenario,
                evidence_ids=day.evidence_ids,
                needs_review=False,
                reason="증빙 기반 자동 배정",
            ),
        )
    return allocated


def _evidence_days(
    evidence: tuple[Evidence, ...],
    alog_records: tuple[ALogRecord, ...],
    weekly_records: tuple[WeeklyALogRecord, ...],
) -> tuple[EvidenceDay, ...]:
    evidence_by_date: dict[date, list[Evidence]] = defaultdict(list)
    alog_by_date = {record.record_date: record for record in alog_records}
    weekly_by_week = {record.week: record for record in weekly_records}
    for item in evidence:
        if item.confidence != Confidence.D:
            evidence_by_date[item.date].append(item)
    days: list[EvidenceDay] = []
    for record_date, items in evidence_by_date.items():
        best = max(items, key=lambda item: CONFIDENCE_RANK[item.confidence])
        capacity = _capacity_for_date(
            best.confidence,
            alog_by_date.get(record_date),
            weekly_by_week.get(best.week),
        )
        if capacity <= 0:
            continue
        days.append(
            EvidenceDay(
                record_date=record_date,
                week=best.week,
                evidence_ids=tuple(item.evidence_id for item in items),
                confidence=best.confidence,
                activity=best.report_phrase,
                capacity_minutes=capacity,
            ),
        )
    return tuple(sorted(days, key=lambda day: (day.record_date, -day.capacity_minutes)))


def _capacity_for_date(
    confidence: Confidence,
    alog: ALogRecord | None,
    weekly_record: WeeklyALogRecord | None,
) -> int:
    if alog is not None:
        return alog.capped_minutes_day
    match confidence:
        case Confidence.A_PLUS | Confidence.A | Confidence.A_CANDIDATE:
            return MAX_DAY_MINUTES
        case Confidence.B:
            return 240
        case Confidence.C:
            return 120 if weekly_record is None else min(120, MAX_DAY_MINUTES)
        case Confidence.D:
            return 0


def _week_remaining(
    week: int,
    allocated_minutes: int,
    weekly_by_week: dict[int, WeeklyALogRecord],
) -> int:
    record = weekly_by_week.get(week)
    if record is None:
        return MAX_WEEK_MINUTES - allocated_minutes
    return min(
        MAX_WEEK_MINUTES - record.capped_minutes_week - allocated_minutes,
        record.remaining_to_52h_minutes - allocated_minutes,
    )


def _capped_week_total(
    week: int,
    allocated_minutes: int,
    weekly_by_week: dict[int, WeeklyALogRecord],
) -> int:
    record = weekly_by_week.get(week)
    if record is None:
        return allocated_minutes
    return record.capped_minutes_week + allocated_minutes


def _fallback_date(days: tuple[EvidenceDay, ...], week: int) -> date:
    for day in days:
        if day.week == week:
            return day.record_date
    return date(2026, 3, 2)
