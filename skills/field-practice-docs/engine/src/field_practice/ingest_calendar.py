from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from field_practice.classify import (
    classify_text,
    has_sensitive_text,
    redact_sensitive,
    report_phrase,
)
from field_practice.models import Confidence, Evidence, SourceType, Workstream
from field_practice.timeparse import parse_local_date
from field_practice.weeks import in_period, week_for_date
from field_practice.writers import write_evidence_csv


@dataclass(frozen=True, slots=True)
class CalendarRawEvent:
    start: str
    end: str
    summary: str
    description: str
    location: str
    attendees: str
    source_url: str
    workstream_hint: str


def ingest_calendar(path: Path) -> tuple[Evidence, ...]:
    if not path.exists():
        return ()
    match path.suffix.lower():
        case ".csv":
            return _parse_csv(path)
        case ".json":
            return _parse_json(path)
        case ".ics":
            return _parse_ics(path)
        case _:
            return ()


def ingest_calendar_to_csv(input_path: Path, output_path: Path) -> tuple[Evidence, ...]:
    evidence = ingest_calendar(input_path)
    write_evidence_csv(output_path, evidence)
    return evidence


def _parse_csv(path: Path) -> tuple[Evidence, ...]:
    events: list[CalendarRawEvent] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            events.append(_csv_event(row))
    return _events_to_evidence(events)


def _csv_event(row: dict[str, str]) -> CalendarRawEvent:
    start = row.get("start", "")
    end = row.get("end", "")
    if start == "":
        event_date = row.get("date", "")
        start = f"{event_date}T{row.get('start_time', '00:00')}:00+09:00"
        end = f"{event_date}T{row.get('end_time', '00:00')}:00+09:00"
    return CalendarRawEvent(
        start=start,
        end=end,
        summary=row.get("summary", ""),
        description=" ".join(
            (
                row.get("description", ""),
                row.get("category", ""),
                row.get("report_usage", ""),
                row.get("source_note", ""),
            )
        ).strip(),
        location=row.get("location", ""),
        attendees=row.get("attendees", ""),
        source_url=row.get("source_url", ""),
        workstream_hint=row.get("workstream", ""),
    )


def _parse_json(path: Path) -> tuple[Evidence, ...]:
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, list):
        return ()
    events: list[CalendarRawEvent] = []
    for raw_event in payload:
        if not isinstance(raw_event, dict):
            continue
        events.append(
            CalendarRawEvent(
                start=str(raw_event.get("start", "")),
                end=str(raw_event.get("end", "")),
                summary=str(raw_event.get("summary", "")),
                description=str(raw_event.get("description", "")),
                location=str(raw_event.get("location", "")),
                attendees=str(raw_event.get("attendees", "")),
                source_url=str(raw_event.get("source_url", "")),
                workstream_hint=str(raw_event.get("workstream", "")),
            ),
        )
    return _events_to_evidence(events)


def _parse_ics(path: Path) -> tuple[Evidence, ...]:
    events: list[CalendarRawEvent] = []
    current: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            events.append(
                CalendarRawEvent(
                    start=current.get("DTSTART", ""),
                    end=current.get("DTEND", ""),
                    summary=current.get("SUMMARY", ""),
                    description=current.get("DESCRIPTION", ""),
                    location=current.get("LOCATION", ""),
                    attendees=current.get("ATTENDEE", ""),
                    source_url=current.get("URL", ""),
                    workstream_hint="",
                ),
            )
            current = {}
            continue
        key, separator, value = line.partition(":")
        if separator != "":
            current[key.split(";", maxsplit=1)[0]] = value
    return _events_to_evidence(events)


def _events_to_evidence(events: list[CalendarRawEvent]) -> tuple[Evidence, ...]:
    evidence: list[Evidence] = []
    for index, event in enumerate(events, start=1):
        if event.start == "":
            continue
        event_date = parse_local_date(event.start)
        if not in_period(event_date):
            continue
        week = week_for_date(event_date)
        if week is None:
            continue
        combined = " ".join(
            (
                event.summary,
                event.description,
                event.location,
                event.attendees,
            ),
        )
        workstream = _workstream(event.workstream_hint, combined)
        title = redact_sensitive(event.summary or "Calendar 일정")
        evidence.append(
            Evidence(
                evidence_id=f"CAL-{index:04d}",
                source_type=SourceType.CALENDAR,
                source_ref=event.source_url or f"calendar:{index}",
                date=event_date,
                week=week,
                title=title,
                description=redact_sensitive(combined),
                workstream=workstream,
                confidence=Confidence.C,
                sensitive=has_sensitive_text(combined),
                report_phrase=report_phrase(workstream, title),
            ),
        )
    return tuple(evidence)


def _workstream(hint: str, combined: str) -> Workstream:
    normalized = hint.strip()
    if normalized in {item.value for item in Workstream}:
        return Workstream(normalized)
    return classify_text(combined)
