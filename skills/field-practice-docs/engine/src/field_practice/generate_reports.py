from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from field_practice.allocate_time import allocate_scenario
from field_practice.classify import assign_confidence
from field_practice.config import (
    COMPANY_NAME,
    DEPARTMENT,
    SEMESTER,
    STUDENT_ID,
    STUDENT_NAME,
    FillStep,
    scenario_defaults,
)
from field_practice.ingest_alog import (
    fill_steps_from_preferences,
    ingest_alog,
    ingest_alog_baselines,
    ingest_alog_fill_strategy,
    ingest_alog_weekly,
)
from field_practice.ingest_calendar import ingest_calendar
from field_practice.ingest_github import ingest_github, ingest_local_git_repos
from field_practice.models import (
    AllocationRequest,
    AllocationResult,
    ALogBaseline,
    FillPreference,
    Scenario,
    WeeklyRow,
)
from field_practice.validate import validation_markdown
from field_practice.writers import (
    weekly_markdown,
    write_evidence_csv,
    write_markdown,
    write_time_csv,
    write_weekly_csv,
)


@dataclass(frozen=True, slots=True)
class PipelineInputs:
    github_path: Path
    calendar_path: Path
    alog_path: Path
    out_dir: Path
    scenarios: tuple[Scenario, ...]
    repo_root: Path | None
    since: str
    until: str
    alog_weekly_path: Path
    alog_baselines_path: Path
    alog_fill_strategy_path: Path


def run_pipeline(inputs: PipelineInputs) -> tuple[AllocationResult, ...]:
    github_evidence = ingest_github(inputs.github_path)
    local_git_evidence = (
        tuple(ingest_local_git_repos(inputs.repo_root, inputs.since, inputs.until))
        if inputs.repo_root is not None
        else ()
    )
    calendar_evidence = ingest_calendar(inputs.calendar_path)
    alog_evidence, alog_records = ingest_alog(inputs.alog_path)
    weekly_records = ingest_alog_weekly(inputs.alog_weekly_path)
    baselines = ingest_alog_baselines(inputs.alog_baselines_path)
    fill_preferences = ingest_alog_fill_strategy(inputs.alog_fill_strategy_path)
    evidence = assign_confidence(
        (*github_evidence, *local_git_evidence, *calendar_evidence, *alog_evidence)
    )
    inputs.out_dir.mkdir(parents=True, exist_ok=True)
    write_evidence_csv(inputs.out_dir / "evidence_ledger.csv", evidence)
    results: list[AllocationResult] = []
    all_time_entries = []
    for scenario in inputs.scenarios:
        defaults = scenario_defaults(scenario)
        request = _allocation_request(scenario, baselines)
        fill_steps = _fill_steps(scenario, fill_preferences, defaults.fill_steps)
        result = allocate_scenario(
            request,
            fill_steps,
            evidence,
            alog_records,
            weekly_records,
        )
        results.append(result)
        all_time_entries.extend(result.time_entries)
        _write_weekly_outputs(inputs.out_dir, result)
    result_tuple = tuple(results)
    write_time_csv(inputs.out_dir / "time_ledger.csv", all_time_entries)
    write_markdown(
        inputs.out_dir / "monthly_report_draft.md", monthly_report(result_tuple)
    )
    write_markdown(
        inputs.out_dir / "final_result_report_draft.md", final_report(result_tuple)
    )
    write_markdown(
        inputs.out_dir / "validation_report.md", validation_markdown(result_tuple)
    )
    return result_tuple


def _allocation_request(
    scenario: Scenario, baselines: tuple[ALogBaseline, ...]
) -> AllocationRequest:
    defaults = scenario_defaults(scenario)
    baseline = next(
        (item for item in baselines if item.scenario == "with_week1"),
        None,
    )
    if baseline is None:
        return AllocationRequest(
            scenario=scenario,
            base_current_minutes=defaults.base_current_minutes,
            target_minutes=defaults.target_minutes,
        )
    match scenario:
        case Scenario.TARGET_480:
            return AllocationRequest(
                scenario=scenario,
                base_current_minutes=baseline.current_minutes,
                target_minutes=baseline.target_480_minutes,
            )
        case Scenario.TARGET_640:
            return AllocationRequest(
                scenario=scenario,
                base_current_minutes=baseline.current_minutes,
                target_minutes=baseline.target_640_minutes,
            )


def _fill_steps(
    scenario: Scenario,
    preferences: tuple[FillPreference, ...],
    default_steps: tuple[FillStep, ...],
) -> tuple[FillStep, ...]:
    if len(preferences) == 0:
        return default_steps
    match scenario:
        case Scenario.TARGET_480:
            return fill_steps_from_preferences(preferences, ("480_with_week1",))
        case Scenario.TARGET_640:
            return fill_steps_from_preferences(
                preferences,
                ("480_with_week1", "640_after_480"),
            )


def _write_weekly_outputs(out_dir: Path, result: AllocationResult) -> None:
    suffix = result.scenario.value
    write_weekly_csv(out_dir / f"weekly_report_{suffix}.csv", result.rows)
    write_markdown(
        out_dir / f"weekly_report_{suffix}.md",
        weekly_markdown(f"주차별 활동보고서 {suffix}시간 시나리오", result.rows),
    )


def monthly_report(results: tuple[AllocationResult, ...]) -> str:
    selected = _largest_result(results)
    grouped: dict[int, list[WeeklyRow]] = defaultdict(list)
    for row in selected.rows:
        grouped[row.record_date.month].append(row)
    lines = [
        "# 창업현장실습 월별 보고서 초안",
        "",
        f"- 성명: {STUDENT_NAME}",
        f"- 학과: {DEPARTMENT}",
        f"- 학번: {STUDENT_ID}",
        f"- 사업체: {COMPANY_NAME}",
        f"- 대상학기: {SEMESTER}",
        "",
    ]
    for month in (3, 4, 5, 6):
        lines.append(f"## {month}월")
        month_rows = grouped.get(month, [])
        if len(month_rows) == 0:
            lines.append("- 증빙 기반 자동 작성 활동 없음")
        for row in month_rows:
            lines.append(
                f"- {row.activity} ({row.minutes}분, 증빙: {';'.join(row.evidence_ids)})"
            )
        lines.append("")
    return "\n".join(lines)


def final_report(results: tuple[AllocationResult, ...]) -> str:
    selected = _largest_result(results)
    total = selected.base_current_minutes + selected.allocated_minutes
    lines = [
        "# 창업현장실습 최종 결과보고서 초안",
        "",
        "## 1. 신청자",
        f"- 성명: {STUDENT_NAME}",
        f"- 학과: {DEPARTMENT}",
        f"- 학번: {STUDENT_ID}",
        f"- 대상학기: {SEMESTER}",
        "",
        "## 2. 사업체 인원현황",
        f"- 사업체명: {COMPANY_NAME}",
        "- 사업자등록번호: 000-00-00000",
        "",
        "## 3. 국가사업 및 기타 교내·외 창업유관 행사 참여 현황",
        "- 증빙 원장을 기준으로 검토 후 기재 필요",
        "",
        "## 4. 전공과의 연계성",
        "- 경영학 전공 기반으로 고객 요구사항, 사업화 가능성, 운영정책, 조직 운영을 제품 개발 활동과 연결하여 수행함.",
        "",
        "## 5. 창업현장실습 수행 실적",
        f"- 자동 배정 시나리오: {selected.scenario.value}시간",
        f"- 기존 인정 가능 시간 기준: {selected.base_current_minutes}분",
        f"- 증빙 기반 추가 배정 시간: {selected.allocated_minutes}분",
        f"- 합계: {total}분",
        "",
        "## 6. 창업현장실습 월별 보고서",
        "- `monthly_report_draft.md` 참조",
        "",
        "## 7. 창업현장실습 참여 결과",
        "- GitHub, Calendar, aLog 증빙에 기반하여 제품기획, 개발, QA, 외부협력, 사업화, 조직 운영, 성과 정리 업무를 주차별로 재구성함.",
        "",
        "## 8. 별첨",
        "- 사업자등록증 및 증빙 원장 별첨 필요",
        "",
    ]
    return "\n".join(lines)


def _largest_result(results: tuple[AllocationResult, ...]) -> AllocationResult:
    if len(results) == 0:
        msg = "at least one allocation result is required"
        raise ValueError(msg)
    return max(results, key=lambda result: result.target_minutes)
