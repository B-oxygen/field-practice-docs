from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class SourceType(StrEnum):
    GITHUB_COMMIT = "github_commit"
    GITHUB_COMMIT_LOCAL = "github_commit_local"
    GITHUB_PR = "github_pr"
    GITHUB_ISSUE = "github_issue"
    CALENDAR = "calendar"
    ALOG = "alog"
    DOCUMENT = "document"


class Workstream(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


class Confidence(StrEnum):
    A_PLUS = "A+"
    A = "A"
    A_CANDIDATE = "A_candidate"
    B = "B"
    C = "C"
    D = "D"


class Scenario(StrEnum):
    TARGET_480 = "480"
    TARGET_640 = "640"


@dataclass(frozen=True, slots=True)
class Week:
    number: int
    start: date
    end: date


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    source_type: SourceType
    source_ref: str
    date: date
    week: int
    title: str
    description: str
    workstream: Workstream
    confidence: Confidence
    sensitive: bool
    report_phrase: str
    repo: str = ""


@dataclass(frozen=True, slots=True)
class ALogRecord:
    record_date: date
    raw_minutes: int
    capped_minutes_day: int
    week: int
    source: str
    confidence: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class WeeklyALogRecord:
    week: int
    start_date: date
    end_date: date
    capped_minutes_week: int
    capped_hhmm: str
    remaining_to_52h_minutes: int
    source_note: str


@dataclass(frozen=True, slots=True)
class ALogBaseline:
    scenario: str
    current_minutes: int
    target_480_minutes: int
    target_640_minutes: int


@dataclass(frozen=True, slots=True)
class FillPreference:
    scenario: str
    week: int
    preferred_additional_minutes: int
    reason: str


@dataclass(frozen=True, slots=True)
class AllocationRequest:
    scenario: Scenario
    base_current_minutes: int
    target_minutes: int


@dataclass(frozen=True, slots=True)
class TimeEntry:
    record_date: date
    week: int
    raw_minutes: int
    proposed_minutes: int
    capped_day_minutes: int
    capped_week_minutes: int
    scenario: Scenario
    evidence_ids: tuple[str, ...]
    needs_review: bool
    reason: str


@dataclass(frozen=True, slots=True)
class WeeklyRow:
    week: int
    record_date: date
    weekday_ko: str
    minutes: int
    activity: str
    evidence_ids: tuple[str, ...]
    confidence: Confidence
    scenario: Scenario
    needs_review: bool


@dataclass(frozen=True, slots=True)
class AllocationResult:
    scenario: Scenario
    rows: tuple[WeeklyRow, ...]
    time_entries: tuple[TimeEntry, ...]
    base_current_minutes: int
    target_minutes: int
    allocated_minutes: int
    shortage_minutes: int


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    level: str
    message: str
