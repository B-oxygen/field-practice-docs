from __future__ import annotations

from datetime import date
from pathlib import Path

from field_practice.direct_hwp_validation import (
    DirectValidationInput,
    validate_direct_fill,
)
from field_practice.direct_template_fill import DirectFillResult
from field_practice.enrich_models import EnrichedWeeklyRow
from field_practice.hwpx_xml import WeeklyPackageDiagnostics


def test_direct_validation_fails_when_markdown_fallback_used(tmp_path: Path) -> None:
    result = DirectFillResult(
        status="markdown_fallback",
        weekly_output=tmp_path / "weekly.hwpx",
        final_output=tmp_path / "final.hwpx",
        validation=tmp_path / "validation.md",
        weekly_mapping=tmp_path / "weekly.csv",
        final_mapping=tmp_path / "final.csv",
        notes=("fallback",),
    )

    report = validate_direct_fill(
        DirectValidationInput(
            result=result,
            rows=(),
            weekly_text="",
            final_text="",
            template_used=False,
        )
    )

    assert not report.ok
    assert "template_not_used" in report.issues


def test_direct_validation_fails_when_student_typo_remains(tmp_path: Path) -> None:
    result = DirectFillResult(
        status="ok",
        weekly_output=tmp_path / "weekly.hwpx",
        final_output=tmp_path / "final.hwpx",
        validation=tmp_path / "validation.md",
        weekly_mapping=tmp_path / "weekly.csv",
        final_mapping=tmp_path / "final.csv",
        notes=(),
    )

    report = validate_direct_fill(
        DirectValidationInput(
            result=result,
            rows=(),
            weekly_text="000000001",
            final_text="",
            template_used=True,
        )
    )

    assert not report.ok
    assert "student_id_typo" in report.issues


def test_direct_validation_fails_when_nonzero_activity_blank(tmp_path: Path) -> None:
    row = EnrichedWeeklyRow(
        week=1,
        record_date=date(2026, 3, 2),
        date_text="26/3/2",
        weekday_ko="월",
        minutes=60,
        activity="",
        evidence_ids=("CAL-1",),
        confidence="C",
        scenario="640",
        needs_review=False,
        quality_status="ok",
    )
    result = DirectFillResult(
        status="ok",
        weekly_output=tmp_path / "weekly.hwpx",
        final_output=tmp_path / "final.hwpx",
        validation=tmp_path / "validation.md",
        weekly_mapping=tmp_path / "weekly.csv",
        final_mapping=tmp_path / "final.csv",
        notes=(),
    )

    report = validate_direct_fill(
        DirectValidationInput(
            result=result,
            rows=(row,),
            weekly_text="0000000000",
            final_text="",
            template_used=True,
        )
    )

    assert not report.ok
    assert "blank_nonzero_activity" in report.issues


def test_direct_validation_fails_on_weekly_package_diagnostics(
    tmp_path: Path,
) -> None:
    result = DirectFillResult(
        status="ok",
        weekly_output=tmp_path / "weekly.hwpx",
        final_output=tmp_path / "final.hwpx",
        validation=tmp_path / "validation.md",
        weekly_mapping=tmp_path / "weekly.csv",
        final_mapping=tmp_path / "final.csv",
        notes=(),
    )

    report = validate_direct_fill(
        DirectValidationInput(
            result=result,
            rows=(),
            weekly_text="0000000000",
            final_text="",
            template_used=True,
            weekly_package=WeeklyPackageDiagnostics(
                row_count_ok=False,
                red_activity_style_count=1,
                activity_style_count=0,
                forbidden_hits=("26//",),
            ),
        )
    )

    assert not report.ok
    assert "weekly_row_count_mismatch" in report.issues
    assert "weekly_red_activity_style" in report.issues
    assert "weekly_forbidden_text:26//" in report.issues
    assert "HWPX 주차 테이블 행 수 일치: 아니오" in report.markdown
