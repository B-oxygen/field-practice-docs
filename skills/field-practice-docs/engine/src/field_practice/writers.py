from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from pathlib import Path

from field_practice.config import STUDENT_ID
from field_practice.models import Evidence, TimeEntry, WeeklyRow
from field_practice.weeks import report_date


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_evidence_csv(path: Path, evidence: Iterable[Evidence]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "evidence_id",
                "source_type",
                "source_ref",
                "repo",
                "date",
                "week",
                "title",
                "description",
                "workstream",
                "confidence",
                "sensitive",
                "report_phrase",
            ],
        )
        for item in evidence:
            writer.writerow(
                [
                    item.evidence_id,
                    item.source_type.value,
                    item.source_ref,
                    item.repo,
                    item.date.isoformat(),
                    item.week,
                    item.title,
                    item.description,
                    item.workstream.value,
                    item.confidence.value,
                    str(item.sensitive).lower(),
                    item.report_phrase,
                ],
            )


def write_time_csv(path: Path, rows: Iterable[TimeEntry]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "date",
                "week",
                "raw_minutes",
                "proposed_minutes",
                "capped_day_minutes",
                "capped_week_minutes",
                "scenario",
                "evidence_ids",
                "needs_review",
                "reason",
            ],
        )
        for row in rows:
            writer.writerow(
                [
                    row.record_date.isoformat(),
                    row.week,
                    row.raw_minutes,
                    row.proposed_minutes,
                    row.capped_day_minutes,
                    row.capped_week_minutes,
                    row.scenario.value,
                    ";".join(row.evidence_ids),
                    str(row.needs_review).lower(),
                    row.reason,
                ],
            )


def write_weekly_csv(path: Path, rows: Iterable[WeeklyRow]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "week",
                "student_id",
                "date",
                "weekday_ko",
                "minutes",
                "activity",
                "evidence_ids",
                "confidence",
                "scenario",
                "needs_review",
            ],
        )
        for row in rows:
            writer.writerow(
                [
                    row.week,
                    STUDENT_ID,
                    report_date(row.record_date),
                    row.weekday_ko,
                    row.minutes,
                    row.activity,
                    ";".join(row.evidence_ids),
                    row.confidence.value,
                    row.scenario.value,
                    str(row.needs_review).lower(),
                ],
            )


def write_markdown(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def weekly_markdown(title: str, rows: Sequence[WeeklyRow]) -> str:
    lines = [
        f"# {title}",
        "",
        f"- 학번: {STUDENT_ID}",
        "",
        "| 주차 | 학번 | 날짜 | 요일 | 근무시간(분) | 활동내역 | 증빙 |",
        "|---:|---|---|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row.week} | {STUDENT_ID} | {report_date(row.record_date)} | "
            f"{row.weekday_ko} | "
            f"{row.minutes} | {row.activity} | {';'.join(row.evidence_ids)} |",
        )
    return "\n".join(lines) + "\n"
