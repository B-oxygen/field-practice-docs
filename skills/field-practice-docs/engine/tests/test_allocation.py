from __future__ import annotations

from datetime import date

from field_practice.allocate_time import allocate_scenario
from field_practice.classify import assign_confidence, report_phrase
from field_practice.config import FILL_480, FILL_640_EXTENSION
from field_practice.models import (
    AllocationRequest,
    ALogRecord,
    Confidence,
    Evidence,
    Scenario,
    SourceType,
    Workstream,
)


def test_allocate_scenario_when_480_has_enough_evidence_then_reaches_target() -> None:
    evidence, alog_records = _supported_fixture()
    result = allocate_scenario(
        AllocationRequest(Scenario.TARGET_480, 27019, 28800),
        FILL_480,
        evidence,
        alog_records,
    )
    assert result.shortage_minutes == 0
    assert result.base_current_minutes + result.allocated_minutes >= 28800


def test_allocate_scenario_when_640_has_enough_evidence_then_reaches_target() -> None:
    evidence, alog_records = _supported_fixture()
    result = allocate_scenario(
        AllocationRequest(Scenario.TARGET_640, 27019, 38400),
        (*FILL_480, *FILL_640_EXTENSION),
        evidence,
        alog_records,
    )
    assert result.shortage_minutes == 0
    assert result.base_current_minutes + result.allocated_minutes >= 38400


def test_allocate_scenario_when_evidence_is_d_grade_then_does_not_use_it() -> None:
    item = _evidence("GH-1", SourceType.GITHUB_COMMIT, date(2026, 6, 16), 16)
    result = allocate_scenario(
        AllocationRequest(Scenario.TARGET_480, 27019, 28800),
        FILL_480,
        (item,),
        (),
    )
    assert result.allocated_minutes == 0
    assert result.shortage_minutes == 1781


def _supported_fixture() -> tuple[tuple[Evidence, ...], tuple[ALogRecord, ...]]:
    specs = (
        (date(2026, 6, 15), 16, 600),
        (date(2026, 6, 16), 16, 600),
        (date(2026, 6, 17), 16, 600),
        (date(2026, 6, 2), 14, 120),
        (date(2026, 3, 16), 3, 600),
        (date(2026, 3, 17), 3, 600),
        (date(2026, 3, 18), 3, 600),
        (date(2026, 3, 23), 4, 600),
        (date(2026, 3, 24), 4, 600),
        (date(2026, 3, 25), 4, 600),
        (date(2026, 3, 26), 4, 600),
        (date(2026, 4, 13), 7, 600),
        (date(2026, 4, 14), 7, 600),
        (date(2026, 4, 15), 7, 600),
        (date(2026, 4, 16), 7, 600),
        (date(2026, 4, 20), 8, 600),
        (date(2026, 4, 21), 8, 600),
        (date(2026, 4, 22), 8, 600),
        (date(2026, 4, 23), 8, 600),
        (date(2026, 4, 24), 8, 600),
        (date(2026, 4, 27), 9, 600),
        (date(2026, 4, 28), 9, 600),
        (date(2026, 4, 29), 9, 600),
    )
    evidence: list[Evidence] = []
    alog_records: list[ALogRecord] = []
    for index, spec in enumerate(specs, start=1):
        record_date, week, minutes = spec
        evidence.append(
            _evidence(f"GH-{index}", SourceType.GITHUB_COMMIT, record_date, week)
        )
        evidence.append(_evidence(f"ALOG-{index}", SourceType.ALOG, record_date, week))
        alog_records.append(
            ALogRecord(
                record_date=record_date,
                raw_minutes=minutes,
                capped_minutes_day=minutes,
                week=week,
                source="test",
                confidence="test",
                evidence_id=f"ALOG-{index}",
            ),
        )
    return assign_confidence(evidence), tuple(alog_records)


def _evidence(
    evidence_id: str,
    source_type: SourceType,
    record_date: date,
    week: int,
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        source_type=source_type,
        source_ref=evidence_id,
        date=record_date,
        week=week,
        title="admin dashboard API",
        description="admin dashboard API",
        workstream=Workstream.B,
        confidence=Confidence.D,
        sensitive=False,
        report_phrase=report_phrase(Workstream.B, "admin dashboard API"),
    )
