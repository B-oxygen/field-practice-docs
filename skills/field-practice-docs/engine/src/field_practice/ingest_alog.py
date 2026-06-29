from __future__ import annotations

import csv
from pathlib import Path

from field_practice.classify import report_phrase
from field_practice.config import MAX_DAY_MINUTES, FillStep
from field_practice.models import (
    ALogBaseline,
    ALogRecord,
    Confidence,
    Evidence,
    FillPreference,
    SourceType,
    WeeklyALogRecord,
    Workstream,
)
from field_practice.timeparse import parse_local_date
from field_practice.weeks import in_period, week_for_date


def ingest_alog(path: Path) -> tuple[tuple[Evidence, ...], tuple[ALogRecord, ...]]:
    if not path.exists():
        return (), ()
    records: list[ALogRecord] = []
    evidence: list[Evidence] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for index, row in enumerate(csv.DictReader(file), start=1):
            record_date = parse_local_date(row.get("date", ""))
            if not in_period(record_date):
                continue
            raw_minutes = max(int(row.get("raw_minutes", "0") or "0"), 0)
            week = week_for_date(record_date)
            if week is None:
                continue
            evidence_id = f"ALOG-{index:04d}"
            capped = min(raw_minutes, MAX_DAY_MINUTES)
            source = path.name
            confidence = row.get("confidence", "source")
            evidence.append(
                Evidence(
                    evidence_id=evidence_id,
                    source_type=SourceType.ALOG,
                    source_ref=f"{source}:{index}",
                    date=record_date,
                    week=week,
                    title="aLog 근무시간 기록",
                    description=f"{raw_minutes}분 근무 기록",
                    workstream=Workstream.G,
                    confidence=Confidence.D,
                    sensitive=False,
                    report_phrase=report_phrase(Workstream.G, "aLog 근무시간 기록"),
                ),
            )
            records.append(
                ALogRecord(
                    record_date=record_date,
                    raw_minutes=raw_minutes,
                    capped_minutes_day=capped,
                    week=week,
                    source=source,
                    confidence=confidence,
                    evidence_id=evidence_id,
                ),
            )
    return tuple(evidence), tuple(records)


def ingest_alog_weekly(path: Path) -> tuple[WeeklyALogRecord, ...]:
    if not path.exists():
        return ()
    records: list[WeeklyALogRecord] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            records.append(
                WeeklyALogRecord(
                    week=int(row.get("week", "0") or "0"),
                    start_date=parse_local_date(row.get("start_date", "")),
                    end_date=parse_local_date(row.get("end_date", "")),
                    capped_minutes_week=max(
                        int(row.get("capped_minutes_week", "0") or "0"),
                        0,
                    ),
                    capped_hhmm=row.get("capped_hhmm", ""),
                    remaining_to_52h_minutes=max(
                        int(row.get("remaining_to_52h_minutes", "0") or "0"),
                        0,
                    ),
                    source_note=row.get("source_note", ""),
                ),
            )
    return tuple(records)


def ingest_alog_baselines(path: Path) -> tuple[ALogBaseline, ...]:
    if not path.exists():
        return ()
    records: list[ALogBaseline] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            records.append(
                ALogBaseline(
                    scenario=row.get("scenario", ""),
                    current_minutes=int(row.get("current_minutes", "0") or "0"),
                    target_480_minutes=int(
                        row.get("target_480_minutes", "28800") or "28800"
                    ),
                    target_640_minutes=int(
                        row.get("target_640_minutes", "38400") or "38400"
                    ),
                ),
            )
    return tuple(records)


def ingest_alog_fill_strategy(path: Path) -> tuple[FillPreference, ...]:
    if not path.exists():
        return ()
    records: list[FillPreference] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            records.append(
                FillPreference(
                    scenario=row.get("scenario", ""),
                    week=int(row.get("week", "0") or "0"),
                    preferred_additional_minutes=int(
                        row.get("preferred_additional_minutes", "0") or "0"
                    ),
                    reason=row.get("reason", ""),
                ),
            )
    return tuple(records)


def fill_steps_from_preferences(
    preferences: tuple[FillPreference, ...],
    scenario_names: tuple[str, ...],
) -> tuple[FillStep, ...]:
    return tuple(
        FillStep(week=item.week, minutes=item.preferred_additional_minutes)
        for item in preferences
        if item.scenario in scenario_names
    )
