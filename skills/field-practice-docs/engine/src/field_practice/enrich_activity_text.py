from __future__ import annotations

from datetime import date

from field_practice.enrich_models import WEEK_NARRATIVES, EvidenceRecord, MutableRow


def blue_activity(row: MutableRow, evidence: tuple[EvidenceRecord, ...]) -> str:
    target = _target(evidence)
    topic = _topic(row, evidence)
    artifact = _artifact(evidence)
    detail = _evidence_detail(evidence)
    return (
        f"{target}의 {topic}을 위해 {detail}을 검토하고, 주요 요구사항과 "
        f"오류·운영 조건을 정리하여 {artifact}에 반영함."
    )


def best_confidence(evidence: tuple[EvidenceRecord, ...]) -> str:
    ranks = {"A+": 5, "A": 4, "A_candidate": 3, "B": 3, "C": 2, "D": 1}
    if len(evidence) == 0:
        return "D"
    return max(evidence, key=lambda item: ranks.get(item.confidence, 0)).confidence


def evidence_dates_for_week(
    week: int,
    evidence_by_date: dict[date, tuple[EvidenceRecord, ...]],
) -> tuple[date, ...]:
    dates = [
        record_date
        for record_date, evidence in evidence_by_date.items()
        if len(evidence) > 0 and any(item.week == week for item in evidence)
    ]
    return tuple(
        sorted(dates, key=lambda value: (_date_rank(evidence_by_date[value]), value))
    )


def _target(evidence: tuple[EvidenceRecord, ...]) -> str:
    text = _combined_text(evidence)
    if "TIPS" in text or "IR" in text:
        return "예시컴퍼니 사업화 자료"
    if "대시보드" in text or "dashboard" in text.lower() or "admin" in text.lower():
        return "기관 고객 대상 관리자 대시보드"
    if "QA" in text or "test" in text.lower() or "fix" in text.lower():
        return "예시컴퍼니 서비스 QA"
    if "CTO" in text or "계약" in text or "온보딩" in text:
        return "예시컴퍼니 기술조직 운영"
    if "미팅" in text or "협력" in text or "MIT" in text:
        return "기관 고객·외부 협력"
    return "예시컴퍼니 앱·관리자 대시보드"


def _topic(row: MutableRow, evidence: tuple[EvidenceRecord, ...]) -> str:
    text = _combined_text(evidence)
    if "오리엔테이션" in text:
        return "창업현장실습 운영 방식 숙지와 초기 실행계획 수립"
    if "api" in text.lower() or "server" in text.lower():
        return "백엔드 API와 데이터 처리 구조 개선"
    if "test" in text.lower() or "QA" in text or "fix" in text.lower():
        return "오류 재현과 기능 검증"
    return WEEK_NARRATIVES.get(row.week, "창업현장실습 수행 내용 구체화")


def _artifact(evidence: tuple[EvidenceRecord, ...]) -> str:
    text = _combined_text(evidence)
    if "TIPS" in text or "IR" in text:
        return "제안자료와 사업화 검토 결과"
    if "미팅" in text or "협력" in text:
        return "회의록과 협력자료"
    if "QA" in text or "test" in text.lower() or "fix" in text.lower():
        return "QA 결과와 체크리스트"
    if "docs" in text.lower() or "보고서" in text:
        return "산출물 문서와 보고서 초안"
    return "개발 이슈와 기능 명세"


def _evidence_detail(evidence: tuple[EvidenceRecord, ...]) -> str:
    if len(evidence) == 0:
        return "동일 주차의 증빙 흐름"
    titles = tuple(dict.fromkeys(item.title for item in evidence if item.title))
    if len(titles) == 0:
        return "증빙 원장에 기록된 작업"
    return "·".join(titles[:2])


def _combined_text(evidence: tuple[EvidenceRecord, ...]) -> str:
    return " ".join(f"{item.title} {item.description}" for item in evidence)


def _date_rank(evidence: tuple[EvidenceRecord, ...]) -> int:
    if any(item.source_type.startswith("github") for item in evidence):
        return 0
    return 1
