from __future__ import annotations

from datetime import date

from field_practice.enrich_activities import EnrichedWeeklyRow
from field_practice.weekly_full_report import render_week8_shortage_report


def test_week8_shortage_when_capacity_exists_then_reports_partial_auto_use() -> None:
    rows = (
        _row(date_text="26/4/20", minutes=600, evidence_ids=("GH-1",)),
        _row(date_text="26/4/21", minutes=600, evidence_ids=("CAL-1",)),
        _row(date_text="26/4/22", minutes=600, evidence_ids=("CAL-2",)),
        _row(date_text="26/4/23", minutes=600, evidence_ids=("GH-2",)),
        _row(date_text="26/4/26", minutes=600, evidence_ids=("GH-3",)),
    )

    markdown = render_week8_shortage_report(rows, shortage_before=666)

    assert "자동 반영 가능 여부: 가능" in markdown
    assert "manual_evidence_required: 예" in markdown
    assert "남은 수동 증빙 필요분: 120분" in markdown


def test_week8_shortage_when_no_evidence_then_requires_manual_evidence() -> None:
    markdown = render_week8_shortage_report((), shortage_before=666)

    assert "자동 반영 가능 여부: 불가" in markdown
    assert "manual_evidence_required: 예" in markdown


def _row(
    *,
    date_text: str,
    minutes: int,
    evidence_ids: tuple[str, ...],
) -> EnrichedWeeklyRow:
    return EnrichedWeeklyRow(
        week=8,
        record_date=date(2026, 4, int(date_text.rsplit("/", maxsplit=1)[1])),
        date_text=date_text,
        weekday_ko="월",
        minutes=minutes,
        activity="프로토타입 검증을 위해 오류 재현 조건을 정리하여 QA 체크리스트에 반영함.",
        evidence_ids=evidence_ids,
        confidence="A_candidate",
        scenario="640",
        needs_review=False,
        quality_status="ok",
    )
