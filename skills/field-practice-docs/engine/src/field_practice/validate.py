from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

from field_practice.config import (
    MAX_DAY_MINUTES,
    MAX_WEEK_MINUTES,
    STUDENT_ID,
    TARGET_480_MINUTES,
    TARGET_640_MINUTES,
)
from field_practice.models import AllocationResult, ValidationIssue

DATE_RE = re.compile(r"^\d{2}/\d{1,2}/\d{1,2}$")


def validate_weekly_csv(
    path: Path, evidence_path: Path | None = None
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    day_minutes: dict[str, int] = defaultdict(int)
    week_minutes: dict[int, int] = defaultdict(int)
    has_week_16 = False
    text = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    if "000000001" in text:
        issues.append(
            ValidationIssue("error", "잘못된 학번 000000001이 출력물에 포함됨")
        )
    if STUDENT_ID not in text and text != "":
        issues.append(
            ValidationIssue(
                "warning", "주차 CSV에는 학번 필드가 없어 별도 양식 병합 시 확인 필요"
            )
        )
    if not path.exists():
        return (ValidationIssue("error", f"weekly file not found: {path}"),)
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            date_text = row.get("date", "")
            week = int(row.get("week", "0") or "0")
            minutes = int(row.get("minutes", "0") or "0")
            needs_review = row.get("needs_review", "false") == "true"
            confidence = row.get("confidence", "")
            evidence_ids = row.get("evidence_ids", "")
            if not DATE_RE.fullmatch(date_text):
                issues.append(ValidationIssue("error", f"날짜 형식 오류: {date_text}"))
            if week == 16:
                has_week_16 = True
            if evidence_ids == "" and not needs_review:
                issues.append(
                    ValidationIssue("error", f"{date_text} 활동에 증빙 ID가 없음")
                )
            if confidence == "D" and not needs_review:
                issues.append(
                    ValidationIssue("error", f"{date_text} D등급 증빙이 자동 사용됨")
                )
            day_minutes[date_text] += minutes
            week_minutes[week] += minutes
    for day, minutes in day_minutes.items():
        if minutes > MAX_DAY_MINUTES:
            issues.append(
                ValidationIssue("error", f"{day} 일일 상한 초과: {minutes}분")
            )
    for week, minutes in week_minutes.items():
        if minutes > MAX_WEEK_MINUTES:
            issues.append(
                ValidationIssue("error", f"{week}주차 주간 상한 초과: {minutes}분")
            )
    if not has_week_16:
        issues.append(ValidationIssue("error", "16주차 활동 행이 없음"))
    if evidence_path is not None and evidence_path.exists():
        evidence_text = evidence_path.read_text(encoding="utf-8-sig")
        if "000000001" in evidence_text:
            issues.append(
                ValidationIssue("error", "증빙 원장에 잘못된 학번 000000001 포함")
            )
    return tuple(issues)


def validation_markdown(results: tuple[AllocationResult, ...]) -> str:
    lines = ["# 검증 보고서", ""]
    for result in results:
        total = result.base_current_minutes + result.allocated_minutes
        target_label = f"{result.scenario.value}시간 시나리오"
        lines.extend(
            [
                f"## {target_label}",
                f"- 기존 인정 가능 시간: {result.base_current_minutes}분",
                f"- 증빙 기반 추가 배정 시간: {result.allocated_minutes}분",
                f"- 합계: {total}분",
                f"- 목표: {result.target_minutes}분",
            ],
        )
        if result.shortage_minutes > 0:
            lines.append(f"- 부족분: {result.shortage_minutes}분")
            lines.append("- 판단: 증빙이 부족하여 목표 시간을 자동 충족하지 않음")
        else:
            lines.append("- 판단: 증빙 기반 배정으로 목표 시간 충족")
        lines.append("")
    lines.extend(
        [
            "## 공통 검증 기준",
            f"- 일일 상한: {MAX_DAY_MINUTES}분",
            f"- 주간 상한: {MAX_WEEK_MINUTES}분",
            f"- 480시간 목표: {TARGET_480_MINUTES}분",
            f"- 640시간 목표: {TARGET_640_MINUTES}분",
            f"- 출력 학번: {STUDENT_ID}",
            "- D등급 증빙은 자동 사용하지 않음",
            "",
        ],
    )
    for result in results:
        for entry in result.time_entries:
            if entry.needs_review:
                lines.append(
                    f"- needs_review: {entry.week}주차 {entry.reason}",
                )
    return "\n".join(lines) + "\n"
