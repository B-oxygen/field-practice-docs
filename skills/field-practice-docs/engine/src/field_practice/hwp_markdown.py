from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from field_practice import hwp_final_markdown
from field_practice.config import (
    COMPANY_NAME,
    DEPARTMENT,
    STUDENT_ID,
    STUDENT_NAME,
)
from field_practice.weeks import WEEKS, dates_in_week, report_date, weekday_ko


@dataclass(frozen=True, slots=True)
class WeeklyActivityRow:
    week: int
    record_date: date
    minutes: int
    activity: str
    evidence_ids: tuple[str, ...]
    needs_review: bool


@dataclass(frozen=True, slots=True)
class HwpxOutputPaths:
    weekly_source: Path
    final_source: Path
    weekly_hwpx: Path
    final_hwpx: Path
    validation: Path


def read_weekly_rows(path: Path, scenario: str) -> tuple[WeeklyActivityRow, ...]:
    rows: list[WeeklyActivityRow] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for record in csv.DictReader(file):
            if record.get("scenario", scenario) != scenario:
                continue
            evidence_ids = tuple(
                item for item in record.get("evidence_ids", "").split(";") if item
            )
            rows.append(
                WeeklyActivityRow(
                    week=int(record.get("week", "0") or "0"),
                    record_date=parse_report_date(record.get("date", "")),
                    minutes=int(record.get("minutes", "0") or "0"),
                    activity=record.get("activity", "").strip(),
                    evidence_ids=evidence_ids,
                    needs_review=record.get("needs_review", "false") == "true",
                )
            )
    return tuple(rows)


def parse_report_date(value: str) -> date:
    parts = value.split("/")
    if len(parts) != 3:
        msg = f"invalid report date: {value}"
        raise ValueError(msg)
    year, month, day = (int(part) for part in parts)
    return date(2000 + year, month, day)


def render_weekly_source_markdown(weekly_path: Path, scenario: str) -> str:
    return render_weekly_source_from_rows(read_weekly_rows(weekly_path, scenario))


def render_weekly_source_from_rows(rows: tuple[WeeklyActivityRow, ...]) -> str:
    by_date = _rows_by_date(rows)
    lines = [
        "# 2026-1학기 창업대체학점 인정제(창업현장실습) 주차별 활동 보고서",
        "",
        f"예시대학 {DEPARTMENT} / {STUDENT_ID} / {STUDENT_NAME} / {COMPANY_NAME}",
        "",
    ]
    for week in WEEKS:
        lines.extend(
            [
                f"## {week.number}주차 ({report_date(week.start)}-{report_date(week.end)})",
                "",
                "| 주차 | 날짜 | 요일 | 근무시간(분) | 활동내역 |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for current in dates_in_week(week.number):
            row = by_date.get(current)
            minutes = "-" if row is None or row.minutes == 0 else str(row.minutes)
            activity = "" if row is None else _clean_cell(row.activity)
            lines.append(
                f"| {week.number} | {report_date(current)} | "
                f"{weekday_ko(current)} | {minutes} | {activity} |"
            )
        lines.append("")
    return "\n".join(lines)


def render_final_source_markdown(
    final_draft: Path,
    monthly_draft: Path,
    rows: tuple[WeeklyActivityRow, ...],
    scenario: str,
) -> str:
    return hwp_final_markdown.render_final_source_markdown(
        final_draft,
        monthly_draft,
        rows,
        scenario,
    )


def _rows_by_date(
    rows: tuple[WeeklyActivityRow, ...],
) -> dict[date, WeeklyActivityRow]:
    grouped: dict[date, list[WeeklyActivityRow]] = defaultdict(list)
    for row in rows:
        grouped[row.record_date].append(row)
    return {record_date: _merge_rows(items) for record_date, items in grouped.items()}


def _merge_rows(rows: list[WeeklyActivityRow]) -> WeeklyActivityRow:
    first = rows[0]
    activities = tuple(dict.fromkeys(row.activity for row in rows if row.activity))
    evidence = tuple(
        dict.fromkeys(evidence_id for row in rows for evidence_id in row.evidence_ids)
    )
    return WeeklyActivityRow(
        week=first.week,
        record_date=first.record_date,
        minutes=sum(row.minutes for row in rows),
        activity=" / ".join(activities),
        evidence_ids=evidence,
        needs_review=any(row.needs_review for row in rows),
    )


def _clean_cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ").strip()
