from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from field_practice.activity_quality import assess_activity
from field_practice.config import MAX_DAY_MINUTES, MAX_WEEK_MINUTES, STUDENT_ID
from field_practice.enrich_models import EnrichedWeeklyRow, RewriteLog
from field_practice.weeks import WEEKS, report_date
from field_practice.writers import ensure_parent, write_markdown


def write_enriched_weekly_csv(path: Path, rows: tuple[EnrichedWeeklyRow, ...]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "week",
                "student_id",
                "date",
                "weekday_ko",
                "minutes",
                "activity",
                "evidence_ids",
                "confidence",
                "scenario",
                "needs_review",
                "quality_status",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.week,
                    STUDENT_ID,
                    row.date_text,
                    row.weekday_ko,
                    row.minutes,
                    row.activity,
                    ";".join(row.evidence_ids),
                    row.confidence,
                    row.scenario,
                    str(row.needs_review).lower(),
                    row.quality_status,
                ]
            )


def render_enriched_weekly_markdown(rows: tuple[EnrichedWeeklyRow, ...]) -> str:
    lines = [
        "# 주차별 활동보고서 상세화본",
        "",
        f"- 학번: {STUDENT_ID}",
        "",
    ]
    by_week: defaultdict[int, list[EnrichedWeeklyRow]] = defaultdict(list)
    for row in rows:
        by_week[row.week].append(row)
    for week in WEEKS:
        lines.append(
            f"## {week.number}주차 ({report_date(week.start)}-{report_date(week.end)})"
        )
        lines.append("")
        lines.append("| 주차 | 날짜 | 요일 | 근무시간(분) | 활동내역 |")
        lines.append("|---:|---|---|---:|---|")
        for row in by_week[week.number]:
            minutes = "-" if row.minutes == 0 else str(row.minutes)
            lines.append(
                f"| {row.week} | {row.date_text} | {row.weekday_ko} | "
                f"{minutes} | {row.activity} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_activity_quality_report(
    rows: tuple[EnrichedWeeklyRow, ...],
    shortage_before: int,
) -> str:
    text = "\n".join(row.activity for row in rows)
    counters = _quality_counters(rows, text)
    total_minutes = sum(row.minutes for row in rows)
    shortage_after = max(38400 - total_minutes, 0)
    lines = [
        "# 활동내역 품질 검증 보고서",
        "",
        f"- 전체 행 수: {len(rows)}",
        f"- nonzero rows: {counters['nonzero']}",
        f"- nonzero row인데 활동내역 blank: {counters['blank_nonzero']}",
        f"- 괄호형 분 단위 표기 포함: {counters['time_pattern']}",
        f"- 학번 오타 잔존: {counters['student_typo']}",
        f"- 날짜 이중 슬래시 잔존: {counters['date_typo']}",
        f"- 너무 짧은 활동내역: {counters['too_short']}",
        f"- 산출물/결과 없는 활동내역: {counters['missing_result']}",
        f"- 16주차 포함: {'예' if any(row.week == 16 for row in rows) else '아니오'}",
        f"- 일일 상한 초과: {counters['day_cap']}",
        f"- 주간 상한 초과: {counters['week_cap']}",
        f"- 총 근무시간: {total_minutes}분",
        f"- enrich 전 640 부족분: {shortage_before}분",
        f"- enrich 후 640 부족분: {shortage_after}분",
        "",
    ]
    return "\n".join(lines)


def write_rewrite_log_csv(path: Path, logs: tuple[RewriteLog, ...]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["week", "date", "minutes", "before", "after", "reason"])
        for log in logs:
            writer.writerow(
                [
                    log.week,
                    log.date_text,
                    log.minutes,
                    log.before,
                    log.after,
                    log.reason,
                ]
            )


def render_week8_shortage_report(
    rows: tuple[EnrichedWeeklyRow, ...],
    shortage_before: int,
) -> str:
    week8_rows = tuple(row for row in rows if row.week == 8 and row.minutes > 0)
    allocated = sum(row.minutes for row in week8_rows)
    used = tuple(evidence_id for row in week8_rows for evidence_id in row.evidence_ids)
    before_supported = max(MAX_WEEK_MINUTES - shortage_before, 0)
    auto_minutes = max(min(allocated - before_supported, shortage_before), 0)
    remaining = max(shortage_before - auto_minutes, 0)
    lines = [
        "# 8주차 부족분 후보 검토",
        "",
        "- week 8 기간: 2026-04-20 ~ 2026-04-26",
        f"- 현재 week 8 allocated minutes: {allocated}분",
        f"- week 8 remaining needed: {shortage_before}분",
        f"- 자동 반영 가능 여부: {'가능' if auto_minutes > 0 else '불가'}",
        f"- 자동 반영 가능분: {auto_minutes}분",
        f"- 남은 수동 증빙 필요분: {remaining}분",
        f"- manual_evidence_required: {'예' if remaining > 0 else '아니오'}",
        "",
        "## week 8 GitHub evidence 목록",
    ]
    github_ids = tuple(item for item in used if item.startswith("GH-"))
    calendar_ids = tuple(item for item in used if item.startswith("CAL-"))
    lines.extend(f"- {item}" for item in github_ids[:30])
    if len(github_ids) == 0:
        lines.append("- 없음")
    lines.append("")
    lines.append("## week 8 Calendar evidence 목록")
    lines.extend(f"- {item}" for item in calendar_ids[:30])
    if len(calendar_ids) == 0:
        lines.append("- 없음")
    lines.extend(
        [
            "",
            "## allocator가 사용하지 않은 이유",
            "- 기존 allocator는 Calendar-only 날짜를 120분으로 제한하여 같은 주차의 GitHub/aLog 보강 증빙을 추가 용량으로 반영하지 못했음.",
            "- enrichment는 같은 주차 GitHub 및 aLog 주간 증빙이 있는 날짜의 잔여 일일 용량만 사용하며, 600분/일 및 3,120분/주 상한을 유지함.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_enrichment_outputs(
    out_dir: Path,
    scenario: str,
    rows: tuple[EnrichedWeeklyRow, ...],
    logs: tuple[RewriteLog, ...],
    shortage_before: int,
) -> None:
    csv_path = out_dir / f"weekly_report_{scenario}_all_weeks.csv"
    md_path = out_dir / f"weekly_report_{scenario}_all_weeks.md"
    write_enriched_weekly_csv(csv_path, rows)
    write_markdown(md_path, render_enriched_weekly_markdown(rows))
    write_markdown(
        out_dir / "activity_quality_report.md",
        render_activity_quality_report(rows, shortage_before),
    )
    write_markdown(
        out_dir / "week8_shortage_candidates.md",
        render_week8_shortage_report(rows, shortage_before),
    )
    write_rewrite_log_csv(out_dir / "red_to_blue_rewrite_log.csv", logs)


def _quality_counters(rows: tuple[EnrichedWeeklyRow, ...], text: str) -> Counter[str]:
    counters: Counter[str] = Counter()
    day_minutes: defaultdict[str, int] = defaultdict(int)
    week_minutes: defaultdict[int, int] = defaultdict(int)
    for row in rows:
        day_minutes[row.date_text] += row.minutes
        week_minutes[row.week] += row.minutes
        if row.minutes <= 0:
            continue
        counters["nonzero"] += 1
        quality = assess_activity(row.activity, row.minutes)
        for issue in quality.issues:
            counters[issue] += 1
    counters["student_typo"] = 1 if "000000001" in text else 0
    counters["date_typo"] = 1 if "26//" in text else 0
    counters["day_cap"] = sum(
        1 for minutes in day_minutes.values() if minutes > MAX_DAY_MINUTES
    )
    counters["week_cap"] = sum(
        1 for minutes in week_minutes.values() if minutes > MAX_WEEK_MINUTES
    )
    return counters
