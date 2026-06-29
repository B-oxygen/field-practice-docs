from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from field_practice.config import (
    MAX_DAY_MINUTES,
    MAX_WEEK_MINUTES,
    STUDENT_ID,
    TARGET_480_MINUTES,
    TARGET_640_MINUTES,
)
from field_practice.hwp_markdown import HwpxOutputPaths, WeeklyActivityRow
from field_practice.weeks import report_date


@dataclass(frozen=True, slots=True)
class WeeklyValidationSummary:
    row_minutes: int
    credited_minutes: int
    target_minutes: int
    shortage_minutes: int
    has_week_16: bool
    daily_cap_ok: bool
    weekly_cap_ok: bool
    activities_without_evidence: tuple[str, ...]
    manual_review_items: tuple[str, ...]


def summarize_weekly_validation(
    rows: tuple[WeeklyActivityRow, ...],
    scenario: str,
    validation_report: Path | None = None,
) -> WeeklyValidationSummary:
    daily_minutes: defaultdict[date, int] = defaultdict(int)
    weekly_minutes: defaultdict[int, int] = defaultdict(int)
    missing: list[str] = []
    reviews: list[str] = []
    for row in rows:
        daily_minutes[row.record_date] += row.minutes
        weekly_minutes[row.week] += row.minutes
        if row.minutes > 0 and len(row.evidence_ids) == 0 and not row.needs_review:
            missing.append(f"{row.week}주차 {report_date(row.record_date)}")
        if row.needs_review:
            reviews.append(
                f"{row.week}주차 {report_date(row.record_date)} {row.activity}"
            )
    credited, target, shortage = _scenario_totals(scenario, validation_report, rows)
    return WeeklyValidationSummary(
        row_minutes=sum(row.minutes for row in rows),
        credited_minutes=credited,
        target_minutes=target,
        shortage_minutes=shortage,
        has_week_16=any(row.week == 16 for row in rows),
        daily_cap_ok=all(
            minutes <= MAX_DAY_MINUTES for minutes in daily_minutes.values()
        ),
        weekly_cap_ok=all(
            minutes <= MAX_WEEK_MINUTES for minutes in weekly_minutes.values()
        ),
        activities_without_evidence=tuple(missing),
        manual_review_items=tuple(reviews),
    )


def render_hwp_export_validation(
    paths: HwpxOutputPaths,
    scenario: str,
    summary: WeeklyValidationSummary,
    weekly_source: str,
    final_source: str,
    conversion_notes: tuple[str, ...],
) -> str:
    combined = weekly_source + "\n" + final_source
    lines = [
        "# HWPX 변환 검증 보고서",
        "",
        f"- 시나리오: {scenario}",
        f"- 주차별 원본 MD: {paths.weekly_source}",
        f"- 결과보고서 원본 MD: {paths.final_source}",
        f"- 주차별 HWPX: {paths.weekly_hwpx}",
        f"- 결과보고서 HWPX: {paths.final_hwpx}",
        f"- 총 근무분: {summary.credited_minutes}분",
        f"- 480시간 충족 여부: {_satisfied(summary.credited_minutes, TARGET_480_MINUTES)}",
        f"- 640시간 충족 여부: {_satisfied(summary.credited_minutes, TARGET_640_MINUTES)}",
        f"- 16주차 포함 여부: {_yes_no(summary.has_week_16)}",
        f"- 사용 학번: {STUDENT_ID}",
        f"- 학번 오타 잔존 여부: {_yes_no('000000001' in combined)}",
        f"- 날짜 이중 슬래시 잔존 여부: {_yes_no('26//' in combined)}",
        f"- 일일 상한 준수: {_yes_no(summary.daily_cap_ok)}",
        f"- 주간 상한 준수: {_yes_no(summary.weekly_cap_ok)}",
        f"- 증빙 없는 활동 수: {len(summary.activities_without_evidence)}",
        "",
        "## 수동 검토 항목",
    ]
    if summary.shortage_minutes > 0:
        lines.append(f"- 목표 대비 부족분: {summary.shortage_minutes}분")
    lines.extend(f"- {item}" for item in summary.manual_review_items)
    lines.extend(f"- 증빙 누락: {item}" for item in summary.activities_without_evidence)
    if len(conversion_notes) > 0:
        lines.append("")
        lines.append("## 변환 상태")
        lines.extend(f"- {note}" for note in conversion_notes)
    return "\n".join(lines) + "\n"


def _scenario_totals(
    scenario: str,
    validation_report: Path | None,
    rows: tuple[WeeklyActivityRow, ...],
) -> tuple[int, int, int]:
    target = TARGET_640_MINUTES if scenario == "640" else TARGET_480_MINUTES
    if validation_report is not None and validation_report.exists():
        text = validation_report.read_text(encoding="utf-8")
        pattern = rf"## {re.escape(scenario)}시간 시나리오(?P<body>.*?)(?:\n## |\Z)"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match is not None:
            body = match.group("body")
            total_match = re.search(r"- 합계: (?P<total>\d+)분", body)
            shortage_match = re.search(r"- 부족분: (?P<shortage>\d+)분", body)
            if total_match is not None:
                total = int(total_match.group("total"))
                shortage = (
                    int(shortage_match.group("shortage")) if shortage_match else 0
                )
                return total, target, shortage
    row_total = sum(row.minutes for row in rows)
    return row_total, target, max(target - row_total, 0)


def _yes_no(value: bool) -> str:
    return "예" if value else "아니오"


def _satisfied(minutes: int, target: int) -> str:
    return "충족" if minutes >= target else "미충족"
