from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Final

from field_practice.models import Scenario

STUDENT_NAME: Final = "홍길동"
DEPARTMENT: Final = "예시학과"
STUDENT_ID: Final = "0000000000"
COMPANY_NAME: Final = "주식회사 예시컴퍼니"
SEMESTER: Final = "2026-1"
TIMEZONE: Final = "Asia/Seoul"
PERIOD_START: Final = date(2026, 3, 2)
PERIOD_END: Final = date(2026, 6, 21)
MAX_DAY_MINUTES: Final = 600
MAX_WEEK_MINUTES: Final = 3120
TARGET_480_MINUTES: Final = 28800
TARGET_640_MINUTES: Final = 38400
CONSERVATIVE_CURRENT_MINUTES: Final = 25519
WITH_WEEK1_CURRENT_MINUTES: Final = 27019
SENSITIVE_MARKERS: Final = ("비밀", "confidential", "secret", "token", "password")


@dataclass(frozen=True, slots=True)
class FillStep:
    week: int
    minutes: int


@dataclass(frozen=True, slots=True)
class ScenarioDefaults:
    base_current_minutes: int
    target_minutes: int
    fill_steps: tuple[FillStep, ...]


FILL_480: Final = (
    FillStep(week=16, minutes=1452),
    FillStep(week=14, minutes=71),
    FillStep(week=3, minutes=258),
)
FILL_640_EXTENSION: Final = (
    FillStep(week=3, minutes=1339),
    FillStep(week=4, minutes=2209),
    FillStep(week=7, minutes=2125),
    FillStep(week=8, minutes=2706),
    FillStep(week=9, minutes=1221),
)


def scenario_defaults(scenario: Scenario, with_week1: bool = True) -> ScenarioDefaults:
    base = WITH_WEEK1_CURRENT_MINUTES if with_week1 else CONSERVATIVE_CURRENT_MINUTES
    match scenario:
        case Scenario.TARGET_480:
            return ScenarioDefaults(
                base_current_minutes=base,
                target_minutes=TARGET_480_MINUTES,
                fill_steps=FILL_480,
            )
        case Scenario.TARGET_640:
            return ScenarioDefaults(
                base_current_minutes=base,
                target_minutes=TARGET_640_MINUTES,
                fill_steps=(*FILL_480, *FILL_640_EXTENSION),
            )
