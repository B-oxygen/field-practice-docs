from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

BAD_EXACT_PHRASES: Final = frozenset(
    {
        "개발",
        "QA",
        "자료 준비",
        "서류 준비",
        "온보딩",
        "미팅",
        "검토",
        "대시보드 개발_BE",
        "어플리케이션 개발",
        "버그 수정",
        "보고서 작성",
    }
)
BAD_SUBSTRINGS: Final = (
    "어플리케이션 개발",
    "대시보드 개발_BE",
)
RESULT_WORDS: Final = (
    "정리",
    "반영",
    "문서화",
    "기능 명세",
    "개발 이슈",
    "QA 결과",
    "체크리스트",
    "회의록",
    "제안자료",
    "협력자료",
    "운영안",
    "백로그",
    "수정 요청",
    "검토 결과",
    "산출물",
)
TIME_PATTERN = re.compile(r"\(\s*\d+\s*min\s*\)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ActivityQuality:
    issues: tuple[str, ...]
    is_bad: bool
    needs_review: bool


def assess_activity(activity: str, minutes: int) -> ActivityQuality:
    normalized = activity.strip()
    issues: list[str] = []
    if minutes > 0 and normalized == "":
        issues.append("blank_nonzero")
    if minutes > 0 and len(normalized) < 45:
        issues.append("too_short")
    if TIME_PATTERN.search(normalized) is not None:
        issues.append("time_pattern")
    if normalized in BAD_EXACT_PHRASES:
        issues.append("bad_exact_phrase")
    if any(pattern in normalized for pattern in BAD_SUBSTRINGS):
        issues.append("bad_substring")
    if normalized.startswith("- ") and len(normalized) < 60:
        issues.append("leading_hyphen_short")
    has_result = any(word in normalized for word in RESULT_WORDS)
    if minutes > 0 and not has_result:
        issues.append("missing_result")
    issue_tuple = tuple(dict.fromkeys(issues))
    bad_markers = {
        "blank_nonzero",
        "too_short",
        "time_pattern",
        "bad_exact_phrase",
        "bad_substring",
        "leading_hyphen_short",
    }
    return ActivityQuality(
        issues=issue_tuple,
        is_bad=any(issue in bad_markers for issue in issue_tuple),
        needs_review=len(issue_tuple) > 0,
    )
