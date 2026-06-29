from __future__ import annotations

import re
from collections.abc import Iterable

from field_practice.config import SENSITIVE_MARKERS
from field_practice.models import Confidence, Evidence, SourceType, Workstream

GITHUB_SOURCES = frozenset(
    {
        SourceType.GITHUB_COMMIT,
        SourceType.GITHUB_COMMIT_LOCAL,
        SourceType.GITHUB_PR,
        SourceType.GITHUB_ISSUE,
    }
)

WORKSTREAM_LABELS: dict[Workstream, str] = {
    Workstream.A: "제품기획·요구사항",
    Workstream.B: "개발·구축",
    Workstream.C: "QA·검증",
    Workstream.D: "외부협력·고객대응",
    Workstream.E: "사업화·운영",
    Workstream.F: "조직·계약·거버넌스",
    Workstream.G: "보고서·성과정리",
}

KEYWORDS: dict[Workstream, tuple[str, ...]] = {
    Workstream.C: ("bug", "fix", "hotfix", "test", "qa", "spec", "오류", "검증"),
    Workstream.D: (
        "mit",
        "cooperation",
        "customer",
        "client",
        "feedback",
        "partner",
        "협력",
        "고객",
    ),
    Workstream.F: ("contract", "cto", "equity", "investor", "계약", "투자", "조직"),
    Workstream.E: ("pricing", "business", "kpi", "ops", "market", "사업", "운영"),
    Workstream.G: ("docs", "readme", "notion", "report", "final", "문서", "보고서"),
    Workstream.B: (
        "auth",
        "login",
        "signup",
        "dashboard",
        "admin",
        "api",
        "server",
        "controller",
        "service",
        "db",
        "schema",
        "migration",
        "model",
        "deploy",
        "release",
        "ci",
        "build",
        "개발",
        "대시보드",
    ),
    Workstream.A: ("requirement", "flow", "planning", "priority", "기획", "요구사항"),
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
TOKEN_RE = re.compile(r"(?i)(token|password|secret)\s*[:=]\s*\S+")


def classify_text(text: str) -> Workstream:
    normalized = text.casefold()
    for workstream, keywords in KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return workstream
    return Workstream.A


def has_sensitive_text(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in SENSITIVE_MARKERS)


def redact_sensitive(text: str) -> str:
    redacted = EMAIL_RE.sub("[이메일 비식별]", text)
    return TOKEN_RE.sub("[민감정보 비식별]", redacted)


def report_phrase(workstream: Workstream, title: str) -> str:
    safe_title = redact_sensitive(title).strip() or "관련 업무"
    match workstream:
        case Workstream.A:
            return (
                "기관 고객 대상 서비스 요구사항 정리를 위해 "
                f"{safe_title} 항목을 검토하고 사용자 흐름과 기능 우선순위를 문서화함."
            )
        case Workstream.B:
            return (
                "학생 및 관리자 대상 서비스 기능 구현을 위해 "
                f"{safe_title} 관련 개발 작업을 수행하고 반영 결과를 정리함."
            )
        case Workstream.C:
            return (
                "서비스 안정성 검증을 위해 "
                f"{safe_title} 항목의 오류 조건과 수정 결과를 확인하고 QA 기록으로 정리함."
            )
        case Workstream.D:
            return (
                "외부 협력 및 고객 대응을 위해 "
                f"{safe_title} 관련 논의사항을 정리하고 공유 가능한 후속 자료로 구성함."
            )
        case Workstream.E:
            return (
                "사업화 및 운영 가능성 검토를 위해 "
                f"{safe_title} 관련 운영 기준과 기대효과를 정리하여 사업 자료에 반영함."
            )
        case Workstream.F:
            return (
                "조직 운영과 거버넌스 정비를 위해 "
                f"{safe_title} 관련 역할, 계약, 검토사항을 정리하고 내부 의사결정 자료로 구성함."
            )
        case Workstream.G:
            return (
                "창업현장실습 성과 정리를 위해 "
                f"{safe_title} 관련 산출물과 증빙자료를 취합하고 제출 초안에 반영함."
            )


def assign_confidence(evidence: Iterable[Evidence]) -> tuple[Evidence, ...]:
    items = tuple(evidence)
    sources_by_date: dict[str, set[SourceType]] = {}
    for item in items:
        key = item.date.isoformat()
        sources_by_date.setdefault(key, set()).add(item.source_type)
    updated: list[Evidence] = []
    for item in items:
        sources = sources_by_date[item.date.isoformat()]
        updated.append(_with_confidence(item, _confidence_for_sources(sources)))
    return tuple(updated)


def _confidence_for_sources(sources: set[SourceType]) -> Confidence:
    has_github = bool(sources & GITHUB_SOURCES)
    has_calendar = SourceType.CALENDAR in sources
    has_alog = SourceType.ALOG in sources
    has_document = SourceType.DOCUMENT in sources
    if has_github and has_calendar and has_alog:
        return Confidence.A_PLUS
    if has_github and has_alog:
        return Confidence.A
    if has_github:
        return Confidence.A_CANDIDATE
    if has_calendar and has_document:
        return Confidence.B
    if has_calendar:
        return Confidence.C
    return Confidence.D


def _with_confidence(item: Evidence, confidence: Confidence) -> Evidence:
    return Evidence(
        evidence_id=item.evidence_id,
        source_type=item.source_type,
        source_ref=item.source_ref,
        date=item.date,
        week=item.week,
        title=item.title,
        description=item.description,
        workstream=item.workstream,
        confidence=confidence,
        sensitive=item.sensitive,
        report_phrase=item.report_phrase,
        repo=item.repo,
    )
