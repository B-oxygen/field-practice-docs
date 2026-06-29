from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from field_practice.enrich_models import EvidenceRecord, MutableRow
from field_practice.ingest_calendar import ingest_calendar
from field_practice.timeparse import parse_local_date


def read_combined_evidence(
    evidence_path: Path,
    calendar_path: Path,
) -> tuple[EvidenceRecord, ...]:
    records = [*read_evidence(evidence_path), *_calendar_evidence(calendar_path)]
    deduped: dict[str, EvidenceRecord] = {}
    for record in records:
        deduped[record.evidence_id] = record
    return tuple(deduped.values())


def read_evidence(path: Path) -> tuple[EvidenceRecord, ...]:
    records: list[EvidenceRecord] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            records.append(
                EvidenceRecord(
                    evidence_id=row.get("evidence_id", ""),
                    source_type=row.get("source_type", ""),
                    record_date=parse_local_date(row.get("date", "")),
                    week=int(row.get("week", "0") or "0"),
                    title=row.get("title", ""),
                    description=row.get("description", ""),
                    workstream=row.get("workstream", ""),
                    confidence=row.get("confidence", ""),
                )
            )
    return tuple(records)


def _calendar_evidence(path: Path) -> tuple[EvidenceRecord, ...]:
    return tuple(
        EvidenceRecord(
            evidence_id=item.evidence_id,
            source_type=item.source_type.value,
            record_date=item.date,
            week=item.week,
            title=item.title,
            description=item.description,
            workstream=item.workstream.value,
            confidence=item.confidence.value,
        )
        for item in ingest_calendar(path)
    )


def read_weekly(path: Path, scenario: str) -> tuple[MutableRow, ...]:
    if not path.exists():
        return ()
    rows: list[MutableRow] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("scenario", scenario) != scenario:
                continue
            rows.append(
                MutableRow(
                    week=int(row.get("week", "0") or "0"),
                    record_date=parse_report_date(row.get("date", "")),
                    minutes=int(row.get("minutes", "0") or "0"),
                    activity=row.get("activity", ""),
                    evidence_ids=split_ids(row.get("evidence_ids", "")),
                    confidence=row.get("confidence", "D"),
                    scenario=scenario,
                    needs_review=row.get("needs_review", "false") == "true",
                )
            )
    return tuple(rows)


def read_weekly_minutes(path: Path) -> dict[int, int]:
    records: dict[int, int] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            week = int(row.get("week", "0") or "0")
            minutes = int(row.get("capped_minutes_week", "0") or "0")
            if week == 1 and minutes == 0:
                minutes = week1_existing_minutes(row.get("source_note", ""))
            records[week] = minutes
    return records


def time_ledger_has_scenario(path: Path, scenario: str) -> bool:
    if not path.exists():
        return False
    with path.open(encoding="utf-8-sig", newline="") as file:
        return any(row.get("scenario", "") == scenario for row in csv.DictReader(file))


def shortage_before(path: Path, scenario: str, week: int) -> int:
    if not path.exists():
        return 0
    shortage = 0
    pattern = re.compile(r"(\d+)분 미배정")
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("scenario", "") != scenario or row.get("week", "") != str(week):
                continue
            if row.get("needs_review", "false") != "true":
                continue
            match = pattern.search(row.get("reason", ""))
            if match is not None:
                shortage += int(match.group(1))
    return shortage


def evidence_by_date(
    evidence: tuple[EvidenceRecord, ...],
) -> dict[date, tuple[EvidenceRecord, ...]]:
    grouped: dict[date, list[EvidenceRecord]] = defaultdict(list)
    for item in evidence:
        grouped[item.record_date].append(item)
    return {key: tuple(value) for key, value in grouped.items()}


def parse_report_date(value: str) -> date:
    year, month, day = (int(part) for part in value.split("/"))
    return date(2000 + year, month, day)


def split_ids(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split(";") if item)


def week1_existing_minutes(note: str) -> int:
    match = re.search(r"(\d),(\d{3})분", note)
    if match is None:
        return 0
    return int(match.group(1) + match.group(2))
