from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True, slots=True)
class EnrichmentInputs:
    scenario: str
    weekly: Path
    time_ledger: Path
    evidence: Path
    calendar: Path
    alog_weekly: Path
    out_dir: Path


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    source_type: str
    record_date: date
    week: int
    title: str
    description: str
    workstream: str
    confidence: str


@dataclass(frozen=True, slots=True)
class EnrichedWeeklyRow:
    week: int
    record_date: date
    date_text: str
    weekday_ko: str
    minutes: int
    activity: str
    evidence_ids: tuple[str, ...]
    confidence: str
    scenario: str
    needs_review: bool
    quality_status: str


@dataclass(frozen=True, slots=True)
class RewriteLog:
    week: int
    date_text: str
    minutes: int
    before: str
    after: str
    reason: str


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    rows: tuple[EnrichedWeeklyRow, ...]
    rewrite_logs: tuple[RewriteLog, ...]
    shortage_before: int


@dataclass(frozen=True, slots=True)
class MutableRow:
    week: int
    record_date: date
    minutes: int
    activity: str
    evidence_ids: tuple[str, ...]
    confidence: str
    scenario: str
    needs_review: bool


WEEK_NARRATIVES: dict[int, str] = {
    1: "오리엔테이션, CTO 역할 정리, 초기 앱·대시보드 개발 착수",
    2: "CTO 온보딩, 인프라 방향성, MIT/외부협력 자료 준비",
    3: "고객 요구사항 정의, 학생 앱 사용자 플로우, 관리자 기능 범위 정리",
    4: "관리자 대시보드 BE/API/데이터 구조 설계",
    5: "시장·고객 검증, 사업모델 가설, TIPS/IR 자료 정리",
    6: "운영정책, 내부 협업 프로세스, 개발/사업화 자료 정리",
    7: "고객 피드백, 기능 우선순위, 외부 협력 방향성 정리",
    8: "프로토타입 개발, QA, 오류 재현, 파일럿 전 검증",
    9: "파일럿 운영 준비, 협력자료 보완, 서비스 소개자료 정리",
    10: "집중 개발 스프린트, 기능 구현, QA",
    11: "운영 테스트, 고객 대응, 사용자 피드백 반영",
    12: "제품 고도화, API/대시보드 안정화",
    13: "사업화·운영 고도화, KPI/운영자료 정리",
    14: "배포 전 검증, 최종 QA, 체크리스트 보완",
    15: "최종 안정화, 데이터 점검, 보고서 반영자료 정리",
    16: "최종 결과보고서, 주차별 보고서 보완, 산출물 패키징",
}
