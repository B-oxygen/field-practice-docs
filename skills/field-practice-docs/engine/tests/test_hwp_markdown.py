from __future__ import annotations

from datetime import date
from pathlib import Path

from field_practice.config import MAX_DAY_MINUTES, MAX_WEEK_MINUTES
from field_practice.hwp_markdown import (
    WeeklyActivityRow,
    render_final_source_markdown,
    render_weekly_source_from_rows,
)
from field_practice.hwp_validation import summarize_weekly_validation


def test_weekly_source_markdown_contains_all_weeks_and_clean_identity() -> None:
    markdown = render_weekly_source_from_rows(
        (
            WeeklyActivityRow(
                week=16,
                record_date=date(2026, 6, 16),
                minutes=120,
                activity="결과보고서 작성을 위해 최종 활동을 정리하여 보고서 초안을 작성함.",
                evidence_ids=("GH-1",),
                needs_review=False,
            ),
        )
    )

    assert "16주차" in markdown
    assert "26/3/2" in markdown
    assert "26/6/21" in markdown
    assert "0000000000" in markdown
    assert "000000001" not in markdown
    assert "26//" not in markdown


def test_final_source_markdown_contains_required_applicant_fields(
    tmp_path: Path,
) -> None:
    final_draft = tmp_path / "final.md"
    monthly_draft = tmp_path / "monthly.md"
    final_draft.write_text("# draft\n", encoding="utf-8")
    monthly_draft.write_text("# monthly\n", encoding="utf-8")

    markdown = render_final_source_markdown(
        final_draft,
        monthly_draft,
        (),
        "640",
    )

    assert "0000000000" in markdown
    assert "12학점" in markdown
    assert "예시학과" in markdown
    assert "000-00-00000" in markdown


def test_hwp_validation_summary_keeps_daily_and_weekly_caps() -> None:
    rows = tuple(
        WeeklyActivityRow(
            week=16,
            record_date=date(2026, 6, 15 + offset),
            minutes=MAX_DAY_MINUTES,
            activity="보고서 제출을 위해 활동 증빙을 검토하여 최종 표를 작성함.",
            evidence_ids=(f"CAL-{offset}",),
            needs_review=False,
        )
        for offset in range(MAX_WEEK_MINUTES // MAX_DAY_MINUTES)
    )

    summary = summarize_weekly_validation(rows, "480")

    assert summary.daily_cap_ok
    assert summary.weekly_cap_ok
    assert len(summary.activities_without_evidence) == 0
