from __future__ import annotations

import csv
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from field_practice.config import STUDENT_ID
from field_practice.direct_hwp_validation import (
    DirectValidationInput,
    validate_direct_fill,
)
from field_practice.enrich_models import EnrichedWeeklyRow
from field_practice.hwpx_xml import (
    diagnose_weekly_package,
    fill_final_report_tables,
    fill_text_blocks,
    fill_weekly_table,
    read_hwpx,
    write_hwpx,
)
from field_practice.template_document import direct_output_paths
from field_practice.timeparse import parse_local_date
from field_practice.weeks import report_date
from field_practice.writers import ensure_parent, write_markdown


@dataclass(frozen=True, slots=True)
class DirectFillRequest:
    scenario: str
    weekly_template: Path
    final_template: Path
    weekly_data: Path
    final_draft: Path
    monthly_draft: Path
    evidence: Path
    out_dir: Path


@dataclass(frozen=True, slots=True)
class DirectFillResult:
    status: str
    weekly_output: Path
    final_output: Path
    validation: Path
    weekly_mapping: Path
    final_mapping: Path
    notes: tuple[str, ...]


def fill_templates(request: DirectFillRequest) -> DirectFillResult:
    paths = direct_output_paths(request.out_dir, request.scenario)
    result = DirectFillResult(
        status="ok",
        weekly_output=paths.weekly,
        final_output=paths.final,
        validation=paths.validation,
        weekly_mapping=paths.weekly_mapping,
        final_mapping=paths.final_mapping,
        notes=(),
    )
    rows = _read_weekly_rows(request.weekly_data, request.scenario)
    if (
        request.weekly_template.suffix.lower() != ".hwpx"
        or request.final_template.suffix.lower() != ".hwpx"
    ):
        blocked = DirectFillResult(
            status="template_hwpx_required",
            weekly_output=paths.weekly,
            final_output=paths.final,
            validation=paths.validation,
            weekly_mapping=paths.weekly_mapping,
            final_mapping=paths.final_mapping,
            notes=("원본 HWP를 한컴오피스에서 HWPX로 저장한 뒤 다시 실행해야 합니다.",),
        )
        _write_blocked_validation(blocked, rows)
        return blocked
    weekly_text = _fill_weekly(
        request.weekly_template, paths.weekly, paths.weekly_mapping, rows
    )
    final_text = _fill_final(request.final_template, paths.final, paths.final_mapping)
    validation = validate_direct_fill(
        DirectValidationInput(
            result=result,
            rows=rows,
            weekly_text=weekly_text,
            final_text=final_text,
            template_used=True,
            weekly_package=diagnose_weekly_package(read_hwpx(paths.weekly)),
        )
    )
    write_markdown(paths.validation, validation.markdown)
    return result


def _fill_weekly(
    template: Path,
    output: Path,
    mapping: Path,
    rows: tuple[EnrichedWeeklyRow, ...],
) -> str:
    row_values = {
        row.date_text: (
            str(row.week),
            row.date_text,
            row.weekday_ko,
            "-" if row.minutes == 0 else str(row.minutes),
            format_weekly_activity_cell(row.activity, minutes=row.minutes),
        )
        for row in rows
    }
    package, mappings = fill_weekly_table(read_hwpx(template), row_values)
    write_hwpx(package, output)
    _write_mapping(mapping, ("date", "row_index", "status"), mappings)
    return read_hwpx(output).combined_text()


def format_weekly_activity_cell(activity: str, *, minutes: int) -> str:
    if minutes <= 0 or activity.strip() == "":
        return ""
    text = activity.lower()
    if "부산" in activity or "국세청" in activity or "중기부" in activity:
        return "· 부산 법인 설립 서류 정리\n· 실사 대응 자료 확인"
    if "최종" in activity or "보고서" in activity or "패키징" in activity:
        return "· 최종 보고서 증빙 정리\n· 산출물 패키징 반영"
    if "tips" in text or "ir" in text or "사업화" in activity or "제안" in activity:
        return "· 사업화 자료 쟁점 검토\n· 제안서·발표자료 보완"
    if "미팅" in activity or "협력" in activity or "mit" in text:
        return "· 협력 미팅 내용 정리\n· 후속 자료·회의록 반영"
    if "qa" in text or "오류" in activity or "fix" in text or "test" in text:
        return "· 오류 재현·기능 검증\n· QA 체크리스트 반영"
    if "대시보드" in activity or "api" in text or "관리자" in activity:
        return "· 관리자 기능/API 검토\n· 데이터 처리 조건 정리"
    return "· 요구사항·업무 범위 검토\n· 수행 결과 문서 반영"


def _fill_final(template: Path, output: Path, mapping: Path) -> str:
    replacements = {"000000001": STUDENT_ID}
    package = fill_text_blocks(read_hwpx(template), replacements)
    package = fill_final_report_tables(package)
    write_hwpx(package, output)
    _write_mapping(
        mapping, ("field", "status"), tuple((key, "filled") for key in replacements)
    )
    return read_hwpx(output).combined_text()


def _read_weekly_rows(path: Path, scenario: str) -> tuple[EnrichedWeeklyRow, ...]:
    rows: list[EnrichedWeeklyRow] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("scenario", scenario) != scenario:
                continue
            record_date = _parse_report_date(row.get("date", ""))
            rows.append(
                EnrichedWeeklyRow(
                    week=int(row.get("week", "0") or "0"),
                    record_date=record_date,
                    date_text=report_date(record_date),
                    weekday_ko=row.get("weekday_ko", ""),
                    minutes=int(row.get("minutes", "0") or "0"),
                    activity=row.get("activity", ""),
                    evidence_ids=tuple(
                        item for item in row.get("evidence_ids", "").split(";") if item
                    ),
                    confidence=row.get("confidence", ""),
                    scenario=scenario,
                    needs_review=row.get("needs_review", "false") == "true",
                    quality_status=row.get("quality_status", ""),
                )
            )
    return tuple(rows)


def _write_blocked_validation(
    result: DirectFillResult,
    rows: tuple[EnrichedWeeklyRow, ...],
) -> None:
    report = validate_direct_fill(
        DirectValidationInput(
            result=result,
            rows=rows,
            weekly_text="",
            final_text="",
            template_used=False,
        )
    )
    write_markdown(
        result.validation,
        report.markdown
        + "\n- template_hwpx_required\n"
        + "- 원본 HWP를 한컴오피스에서 HWPX로 저장해 주세요.\n",
    )


def _parse_report_date(value: str) -> date:
    year, month, day = (int(part) for part in value.split("/"))
    return parse_local_date(f"{2000 + year:04d}-{month:02d}-{day:02d}")


def _write_mapping(
    path: Path,
    header: tuple[str, ...],
    rows: Iterable[Sequence[object]],
) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)
