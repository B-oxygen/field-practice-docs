from __future__ import annotations

from pathlib import Path

from field_practice.direct_template_fill import DirectFillRequest, fill_templates
from field_practice.hwpx_xml import read_hwpx
from hwpx_fixture import write_final_hwpx_fixture, write_weekly_hwpx_fixture


def test_final_template_fill_inserts_fixed_report_sections(tmp_path: Path) -> None:
    weekly_template = tmp_path / "weekly.hwpx"
    final_template = tmp_path / "final.hwpx"
    write_weekly_hwpx_fixture(weekly_template)
    write_final_hwpx_fixture(final_template)
    weekly_data = tmp_path / "weekly.csv"
    weekly_data.write_text(
        "\ufeffweek,student_id,date,weekday_ko,minutes,activity,evidence_ids,confidence,scenario,needs_review,quality_status\n",
        encoding="utf-8",
    )
    final_draft = tmp_path / "final.md"
    monthly_draft = tmp_path / "monthly.md"
    evidence = tmp_path / "evidence.csv"
    final_draft.write_text("# final\n", encoding="utf-8")
    monthly_draft.write_text("# monthly\n", encoding="utf-8")
    evidence.write_text("evidence_id\n", encoding="utf-8")

    result = fill_templates(
        DirectFillRequest(
            scenario="640",
            weekly_template=weekly_template,
            final_template=final_template,
            weekly_data=weekly_data,
            final_draft=final_draft,
            monthly_draft=monthly_draft,
            evidence=evidence,
            out_dir=tmp_path / "direct",
        )
    )

    text = read_hwpx(result.final_output).combined_text()
    assert "홍길동" in text
    assert "0000000000" in text
    assert "12학점(주전공)" in text
    assert "경영학 전공에서 학습한 창업" in text
    assert "오리엔테이션, 역할 정리" in text
    assert "창업현장실습 기간 동안 제품 기획" in text
    assert "성명 홍길동 / 신청학점" not in text
    assert "학번 0000000000" not in text
