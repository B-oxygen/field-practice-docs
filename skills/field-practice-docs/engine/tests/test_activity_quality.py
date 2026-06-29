from __future__ import annotations

from field_practice.activity_quality import assess_activity


def test_assess_activity_when_red_time_pattern_then_bad() -> None:
    result = assess_activity(
        "서울미디어대학원대학교 학생 대상 어플리케이션 개발(600min)", 600
    )

    assert result.is_bad
    assert "time_pattern" in result.issues


def test_assess_activity_when_blue_orientation_detail_then_good() -> None:
    activity = (
        "[창업교육센터] 창업대체학점 인정제 오리엔테이션에서 근무관리 시스템 "
        "사용방법을 습득하고 창업현장실습 아이템 소개 내용을 정리하여 향후 실행계획에 반영함."
    )

    result = assess_activity(activity, 60)

    assert not result.is_bad
    assert not result.needs_review


def test_assess_activity_when_short_qa_then_bad() -> None:
    result = assess_activity("QA", 120)

    assert result.is_bad
    assert "too_short" in result.issues


def test_assess_activity_when_no_result_word_then_review() -> None:
    result = assess_activity(
        "관리자 대시보드 기능 범위와 화면 이동 조건을 상세하게 검토함", 120
    )

    assert result.needs_review
    assert "missing_result" in result.issues


def test_assess_activity_when_activity_contains_minutes_then_bad() -> None:
    result = assess_activity("앱 기능 구현과 QA 결과 정리(300min)", 300)

    assert result.is_bad
    assert "time_pattern" in result.issues
