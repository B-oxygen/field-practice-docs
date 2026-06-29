from __future__ import annotations

from pathlib import Path

from field_practice.direct_template_fill import (
    DirectFillRequest,
    fill_templates,
    format_weekly_activity_cell,
)
from field_practice.hwpx_xml import read_hwpx
from hwpx_fixture import write_final_hwpx_fixture, write_weekly_hwpx_fixture


def test_direct_template_fill_replaces_bad_text_and_adds_week16(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path)

    result = fill_templates(request)

    weekly_text = read_hwpx(result.weekly_output).combined_text()
    assert "0000000000" in weekly_text
    assert "000000001" not in weekly_text
    assert "26//3/6" not in weekly_text
    assert "(600min)" not in weekly_text
    assert "· 최종 보고서 증빙 정리" in weekly_text
    assert "· 산출물 패키징 반영" in weekly_text
    assert "26/6/15" in weekly_text
    assert result.weekly_mapping.exists()
    validation = result.validation.read_text(encoding="utf-8")
    assert "HWPX 주차 테이블 행 수 일치: 예" in validation
    assert "HWPX 빨간 활동 스타일 잔존: 0" in validation
    assert "HWPX 금지 문자열 잔존: 없음" in validation


def test_direct_template_fill_when_hwp_only_then_reports_hwpx_required(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path, hwp_only=True)

    result = fill_templates(request)

    assert result.status == "template_hwpx_required"
    assert result.validation.exists()
    assert "template_hwpx_required" in result.validation.read_text(encoding="utf-8")


def test_format_weekly_activity_cell_returns_short_black_bullet_lines() -> None:
    activity = (
        "예시컴퍼니 서비스 QA의 백엔드 API와 데이터 처리 구조 개선을 위해 "
        "Merge pull request #330 from UniportOfficial/fix/file-menu-dropdown-position"
        "·fix(file-menu): 파일 메뉴 드롭다운 화면 하단 잘림/순서 역전/트리거 가림 해결을 "
        "검토하고, 주요 요구사항과 오류·운영 조건을 정리하여 QA 결과와 체크리스트에 반영함."
    )

    formatted = format_weekly_activity_cell(activity, minutes=600)

    lines = formatted.splitlines()
    assert lines == ["· 오류 재현·기능 검증", "· QA 체크리스트 반영"]
    assert all(len(line) <= 24 for line in lines)
    assert "Merge pull request" not in formatted
    assert "600min" not in formatted


def _request(tmp_path: Path, hwp_only: bool = False) -> DirectFillRequest:
    weekly_template = tmp_path / ("weekly.hwp" if hwp_only else "weekly.hwpx")
    final_template = tmp_path / ("final.hwp" if hwp_only else "final.hwpx")
    if hwp_only:
        weekly_template.write_bytes(b"hwp")
        final_template.write_bytes(b"hwp")
    else:
        write_weekly_hwpx_fixture(weekly_template)
        write_final_hwpx_fixture(final_template)
    weekly_data = tmp_path / "weekly.csv"
    weekly_data.write_text(
        "\ufeffweek,student_id,date,weekday_ko,minutes,activity,evidence_ids,confidence,scenario,needs_review,quality_status\n"
        "1,0000000000,26/3/6,금,600,오리엔테이션 참석을 위해 운영방식과 근무관리 시스템을 확인하고 향후 실행계획에 반영함.,CAL-1,C,640,false,ok\n"
        "16,0000000000,26/6/15,월,600,보고서 제출을 위해 최종 활동 증빙을 검토하고 산출물 패키징 결과를 정리함.,GH-1,A,640,false,ok\n",
        encoding="utf-8",
    )
    final_draft = tmp_path / "final.md"
    monthly_draft = tmp_path / "monthly.md"
    evidence = tmp_path / "evidence.csv"
    final_draft.write_text("# final\n", encoding="utf-8")
    monthly_draft.write_text("# monthly\n", encoding="utf-8")
    evidence.write_text("evidence_id\nGH-1\n", encoding="utf-8")
    return DirectFillRequest(
        scenario="640",
        weekly_template=weekly_template,
        final_template=final_template,
        weekly_data=weekly_data,
        final_draft=final_draft,
        monthly_draft=monthly_draft,
        evidence=evidence,
        out_dir=tmp_path / "direct",
    )
