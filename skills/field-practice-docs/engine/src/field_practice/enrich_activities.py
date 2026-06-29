from __future__ import annotations

from datetime import date

from field_practice.activity_quality import assess_activity
from field_practice.config import MAX_DAY_MINUTES, MAX_WEEK_MINUTES
from field_practice.enrich_activity_text import (
    best_confidence,
    blue_activity,
    evidence_dates_for_week,
)
from field_practice.enrich_models import (
    EnrichedWeeklyRow,
    EnrichmentInputs,
    EnrichmentResult,
    EvidenceRecord,
    MutableRow,
    RewriteLog,
)
from field_practice.enrich_readers import (
    evidence_by_date,
    read_combined_evidence,
    read_weekly,
    read_weekly_minutes,
    shortage_before,
    time_ledger_has_scenario,
)
from field_practice.weeks import WEEKS, dates_in_week, report_date, weekday_ko


def enrich_weekly_reports(inputs: EnrichmentInputs) -> EnrichmentResult:
    evidence = evidence_by_date(
        read_combined_evidence(inputs.evidence, inputs.calendar)
    )
    rows = _full_skeleton(inputs.scenario)
    rows = _merge_existing(rows, read_weekly(inputs.weekly, inputs.scenario))
    rows = _apply_weekly_baseline(
        rows,
        read_weekly_minutes(inputs.alog_weekly),
        evidence,
        time_ledger_has_scenario(inputs.time_ledger, inputs.scenario),
    )
    shortage = shortage_before(inputs.time_ledger, inputs.scenario, 8)
    rows = _apply_week8_candidate_minutes(rows, shortage, evidence)
    enriched, logs = _enrich_rows(rows, evidence)
    return EnrichmentResult(rows=enriched, rewrite_logs=logs, shortage_before=shortage)


def _full_skeleton(scenario: str) -> dict[date, MutableRow]:
    rows: dict[date, MutableRow] = {}
    for week in WEEKS:
        for current in dates_in_week(week.number):
            rows[current] = MutableRow(
                week=week.number,
                record_date=current,
                minutes=0,
                activity="",
                evidence_ids=(),
                confidence="",
                scenario=scenario,
                needs_review=False,
            )
    return rows


def _merge_existing(
    rows: dict[date, MutableRow],
    existing_rows: tuple[MutableRow, ...],
) -> dict[date, MutableRow]:
    merged = dict(rows)
    for row in existing_rows:
        previous = merged[row.record_date]
        evidence_ids = tuple(dict.fromkeys((*previous.evidence_ids, *row.evidence_ids)))
        merged[row.record_date] = MutableRow(
            week=row.week,
            record_date=row.record_date,
            minutes=min(previous.minutes + row.minutes, MAX_DAY_MINUTES),
            activity=row.activity or previous.activity,
            evidence_ids=evidence_ids,
            confidence=row.confidence or previous.confidence,
            scenario=row.scenario,
            needs_review=previous.needs_review or row.needs_review,
        )
    return merged


def _apply_weekly_baseline(
    rows: dict[date, MutableRow],
    weekly_minutes: dict[int, int],
    evidence: dict[date, tuple[EvidenceRecord, ...]],
    time_ledger_rows_exist: bool,
) -> dict[date, MutableRow]:
    updated = dict(rows)
    for week in WEEKS:
        existing_total = _week_total(updated, week.number)
        requested = weekly_minutes.get(week.number, 0)
        if not time_ledger_rows_exist:
            requested = max(requested - existing_total, 0)
        _allocate_week_minutes(updated, week.number, requested, evidence)
    return updated


def _apply_week8_candidate_minutes(
    rows: dict[date, MutableRow],
    shortage: int,
    evidence: dict[date, tuple[EvidenceRecord, ...]],
) -> dict[date, MutableRow]:
    if shortage <= 0:
        return rows
    updated = dict(rows)
    room = max(min(MAX_WEEK_MINUTES - _week_total(updated, 8), shortage), 0)
    _allocate_week_minutes(updated, 8, room, evidence)
    return updated


def _allocate_week_minutes(
    rows: dict[date, MutableRow],
    week: int,
    requested: int,
    evidence: dict[date, tuple[EvidenceRecord, ...]],
) -> None:
    remaining = min(requested, MAX_WEEK_MINUTES - _week_total(rows, week))
    for record_date in evidence_dates_for_week(week, evidence):
        if remaining <= 0:
            return
        previous = rows[record_date]
        proposed = min(remaining, MAX_DAY_MINUTES - previous.minutes)
        if proposed <= 0:
            continue
        date_evidence = evidence.get(record_date, ())
        rows[record_date] = _with_added_minutes(previous, proposed, date_evidence)
        remaining -= proposed


def _with_added_minutes(
    row: MutableRow,
    minutes: int,
    evidence: tuple[EvidenceRecord, ...],
) -> MutableRow:
    return MutableRow(
        week=row.week,
        record_date=row.record_date,
        minutes=row.minutes + minutes,
        activity=row.activity,
        evidence_ids=tuple(
            dict.fromkeys((*row.evidence_ids, *(item.evidence_id for item in evidence)))
        ),
        confidence=row.confidence or best_confidence(evidence),
        scenario=row.scenario,
        needs_review=row.needs_review,
    )


def _enrich_rows(
    rows: dict[date, MutableRow],
    evidence: dict[date, tuple[EvidenceRecord, ...]],
) -> tuple[tuple[EnrichedWeeklyRow, ...], tuple[RewriteLog, ...]]:
    enriched: list[EnrichedWeeklyRow] = []
    logs: list[RewriteLog] = []
    for row in sorted(rows.values(), key=lambda item: item.record_date):
        item, log = _enrich_row(row, evidence.get(row.record_date, ()))
        enriched.append(item)
        if log is not None:
            logs.append(log)
    return tuple(enriched), tuple(logs)


def _enrich_row(
    row: MutableRow,
    evidence: tuple[EvidenceRecord, ...],
) -> tuple[EnrichedWeeklyRow, RewriteLog | None]:
    activity = ""
    status = "blank_zero"
    needs_review = row.needs_review
    log: RewriteLog | None = None
    if row.minutes > 0:
        before_quality = assess_activity(row.activity, row.minutes)
        activity = blue_activity(row, evidence)
        after_quality = assess_activity(activity, row.minutes)
        status = (
            "ok" if not after_quality.needs_review else ";".join(after_quality.issues)
        )
        needs_review = needs_review or after_quality.needs_review
        if before_quality.needs_review or row.activity.strip() != activity:
            log = RewriteLog(
                week=row.week,
                date_text=report_date(row.record_date),
                minutes=row.minutes,
                before=row.activity,
                after=activity,
                reason=";".join(before_quality.issues) or "activity_enriched",
            )
    return (
        EnrichedWeeklyRow(
            week=row.week,
            record_date=row.record_date,
            date_text=report_date(row.record_date),
            weekday_ko=weekday_ko(row.record_date),
            minutes=row.minutes,
            activity=activity,
            evidence_ids=row.evidence_ids,
            confidence=row.confidence or best_confidence(evidence),
            scenario=row.scenario,
            needs_review=needs_review,
            quality_status=status,
        ),
        log,
    )


def _week_total(rows: dict[date, MutableRow], week: int) -> int:
    return sum(row.minutes for row in rows.values() if row.week == week)
