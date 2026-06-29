from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Protocol

from field_practice.config import MAX_DAY_MINUTES, MAX_WEEK_MINUTES, STUDENT_ID
from field_practice.enrich_models import EnrichedWeeklyRow
from field_practice.hwpx_xml import WeeklyPackageDiagnostics


class DirectFillResultLike(Protocol):
    @property
    def status(self) -> str: ...


@dataclass(frozen=True, slots=True)
class DirectValidationInput:
    result: DirectFillResultLike
    rows: tuple[EnrichedWeeklyRow, ...]
    weekly_text: str
    final_text: str
    template_used: bool
    weekly_package: WeeklyPackageDiagnostics | None = None


@dataclass(frozen=True, slots=True)
class DirectValidationReport:
    ok: bool
    issues: tuple[str, ...]
    markdown: str


def validate_direct_fill(inputs: DirectValidationInput) -> DirectValidationReport:
    issues: list[str] = []
    combined = inputs.weekly_text + "\n" + inputs.final_text
    day_minutes: defaultdict[str, int] = defaultdict(int)
    week_minutes: defaultdict[int, int] = defaultdict(int)
    if not inputs.template_used:
        issues.append("template_not_used")
    if inputs.result.status == "markdown_fallback":
        issues.append("markdown_fallback_used")
    if "000000001" in combined:
        issues.append("student_id_typo")
    if STUDENT_ID not in combined and inputs.template_used:
        issues.append("student_id_missing")
    if "26//" in combined:
        issues.append("date_double_slash")
    if "(600min)" in combined:
        issues.append("minute_pattern")
    if inputs.weekly_package is not None:
        if not inputs.weekly_package.row_count_ok:
            issues.append("weekly_row_count_mismatch")
        if inputs.weekly_package.red_activity_style_count > 0:
            issues.append("weekly_red_activity_style")
        for forbidden in inputs.weekly_package.forbidden_hits:
            issues.append(f"weekly_forbidden_text:{forbidden}")
    for row in inputs.rows:
        day_minutes[row.date_text] += row.minutes
        week_minutes[row.week] += row.minutes
        if row.minutes > 0 and row.activity.strip() == "":
            issues.append("blank_nonzero_activity")
    if any(minutes > MAX_DAY_MINUTES for minutes in day_minutes.values()):
        issues.append("day_cap_exceeded")
    if any(minutes > MAX_WEEK_MINUTES for minutes in week_minutes.values()):
        issues.append("week_cap_exceeded")
    issue_tuple = tuple(dict.fromkeys(issues))
    return DirectValidationReport(
        ok=len(issue_tuple) == 0,
        issues=issue_tuple,
        markdown=_markdown(issue_tuple, inputs),
    )


def _markdown(
    issues: tuple[str, ...],
    inputs: DirectValidationInput,
) -> str:
    return "\n".join(
        [
            "# 직접 템플릿 삽입 검증 보고서",
            "",
            f"- 상태: {inputs.result.status}",
            f"- 원본 템플릿 구조 사용: {'예' if inputs.template_used else '아니오'}",
            f"- weekly output exists: {'예' if inputs.weekly_text else '아니오'}",
            f"- final output exists: {'예' if inputs.final_text else '아니오'}",
            f"- 사용 학번: {STUDENT_ID}",
            f"- HWPX 주차 테이블 행 수 일치: {_diagnostic_value(inputs, 'row_count_ok')}",
            f"- HWPX 활동 셀 정상 스타일 수: {_diagnostic_value(inputs, 'activity_style_count')}",
            f"- HWPX 빨간 활동 스타일 잔존: {_diagnostic_value(inputs, 'red_activity_style_count')}",
            f"- HWPX 금지 문자열 잔존: {_forbidden_value(inputs)}",
            f"- 검증 통과: {'예' if len(issues) == 0 else '아니오'}",
            "",
            "## 이슈",
            *(f"- {issue}" for issue in issues),
            "",
        ]
    )


def _diagnostic_value(inputs: DirectValidationInput, field: str) -> str:
    if inputs.weekly_package is None:
        return "미검사"
    value = getattr(inputs.weekly_package, field)
    if isinstance(value, bool):
        return "예" if value else "아니오"
    return str(value)


def _forbidden_value(inputs: DirectValidationInput) -> str:
    if inputs.weekly_package is None:
        return "미검사"
    if len(inputs.weekly_package.forbidden_hits) == 0:
        return "없음"
    return ", ".join(inputs.weekly_package.forbidden_hits)
