from __future__ import annotations

from datetime import date
from pathlib import Path

from field_practice.allocate_time import allocate_scenario
from field_practice.classify import report_phrase
from field_practice.config import FillStep
from field_practice.ingest_alog import ingest_alog_weekly
from field_practice.models import (
    AllocationRequest,
    Confidence,
    Evidence,
    Scenario,
    SourceType,
    Workstream,
)


def test_ingest_alog_weekly_when_csv_exists_then_reads_remaining_capacity(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "alog_weekly_summary.csv"
    csv_path.write_text(
        "week,start_date,end_date,capped_minutes_week,capped_hhmm,"
        "remaining_to_52h_minutes,source_note\n"
        "16,2026-06-15,2026-06-21,1668,27:48,1452,summary\n",
        encoding="utf-8",
    )

    records = ingest_alog_weekly(csv_path)

    assert records[0].week == 16
    assert records[0].capped_minutes_week == 1668
    assert records[0].remaining_to_52h_minutes == 1452


def test_allocate_scenario_when_only_weekly_alog_then_uses_evidence_dates(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "alog_weekly_summary.csv"
    csv_path.write_text(
        "week,start_date,end_date,capped_minutes_week,capped_hhmm,"
        "remaining_to_52h_minutes,source_note\n"
        "16,2026-06-15,2026-06-21,1668,27:48,1452,summary\n",
        encoding="utf-8",
    )
    evidence = (
        Evidence(
            evidence_id="LOCAL-1",
            source_type=SourceType.GITHUB_COMMIT_LOCAL,
            source_ref="abc",
            date=date(2026, 6, 15),
            week=16,
            title="final report docs",
            description="final report docs",
            workstream=Workstream.G,
            confidence=Confidence.A_CANDIDATE,
            sensitive=False,
            report_phrase=report_phrase(Workstream.G, "final report docs"),
            repo="uniport-api",
        ),
    )

    result = allocate_scenario(
        AllocationRequest(Scenario.TARGET_480, 27019, 28800),
        fill_steps=(FillStep(week=16, minutes=1452),),
        evidence=evidence,
        alog_records=(),
        weekly_records=ingest_alog_weekly(csv_path),
    )

    assert result.allocated_minutes == 600
    assert result.shortage_minutes == 1181
    assert result.time_entries[0].capped_week_minutes == 2268
