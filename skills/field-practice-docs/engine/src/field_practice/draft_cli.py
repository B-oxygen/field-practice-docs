from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from field_practice.enrich_activities import EnrichmentInputs, enrich_weekly_reports
from field_practice.generate_reports import PipelineInputs, run_pipeline
from field_practice.ingest_calendar import ingest_calendar_to_csv
from field_practice.ingest_github import ingest_github_to_csv, ingest_local_git_repos
from field_practice.models import Scenario
from field_practice.validate import validate_weekly_csv
from field_practice.weekly_full_report import write_enrichment_outputs
from field_practice.writers import write_evidence_csv, write_markdown

draft_app = typer.Typer(
    help="Build report drafts from evidence.",
    no_args_is_help=True,
)


@draft_app.command("run")
def run_command(
    scenario: Annotated[
        str,
        typer.Option(help="480, 640, or both"),
    ] = "both",
    github: Annotated[
        Path,
        typer.Option(help="GitHub raw export directory or file"),
    ] = Path("data/raw/github"),
    calendar: Annotated[
        Path,
        typer.Option(help="Calendar CSV, JSON, or ICS export"),
    ] = Path("data/raw/calendar/calendar_seed_events.csv"),
    alog: Annotated[
        Path,
        typer.Option(help="aLog daily CSV"),
    ] = Path("data/raw/alog/alog_daily.csv"),
    repo_root: Annotated[
        Path,
        typer.Option(help="Root directory for local git repository discovery"),
    ] = Path(),
    since: Annotated[
        str,
        typer.Option(help="Git log start date"),
    ] = "2026-03-02",
    until: Annotated[
        str,
        typer.Option(help="Git log end datetime"),
    ] = "2026-06-21 23:59:59",
    alog_weekly: Annotated[
        Path,
        typer.Option(help="aLog weekly summary CSV"),
    ] = Path("data/raw/alog/alog_weekly_summary.csv"),
    alog_baselines: Annotated[
        Path,
        typer.Option(help="aLog baseline scenario CSV"),
    ] = Path("data/raw/alog/alog_baselines.csv"),
    alog_fill_strategy: Annotated[
        Path,
        typer.Option(help="aLog fill strategy preference CSV"),
    ] = Path("data/raw/alog/alog_fill_strategy.csv"),
    out: Annotated[
        Path,
        typer.Option(help="Output reports directory"),
    ] = Path("reports"),
) -> None:
    scenarios = _parse_scenarios(scenario)
    results = run_pipeline(
        PipelineInputs(
            github_path=github,
            calendar_path=calendar,
            alog_path=alog,
            out_dir=out,
            scenarios=scenarios,
            repo_root=repo_root,
            since=since,
            until=until,
            alog_weekly_path=alog_weekly,
            alog_baselines_path=alog_baselines,
            alog_fill_strategy_path=alog_fill_strategy,
        )
    )
    for result in results:
        total = result.base_current_minutes + result.allocated_minutes
        typer.echo(
            f"{result.scenario.value}: {total}/{result.target_minutes}분, "
            f"부족 {result.shortage_minutes}분",
        )


@draft_app.command("ingest-github")
def ingest_github_command(
    input_path: Annotated[Path, typer.Option("--input")],
    out: Annotated[Path, typer.Option()],
) -> None:
    evidence = ingest_github_to_csv(input_path, out)
    typer.echo(f"wrote {len(evidence)} GitHub evidence rows to {out}")


@draft_app.command("ingest-calendar")
def ingest_calendar_command(
    input_path: Annotated[Path, typer.Option("--input")],
    out: Annotated[Path, typer.Option()],
) -> None:
    evidence = ingest_calendar_to_csv(input_path, out)
    typer.echo(f"wrote {len(evidence)} Calendar evidence rows to {out}")


@draft_app.command("ingest-local-git")
def ingest_local_git_command(
    repo_root: Annotated[Path, typer.Option()],
    since: Annotated[str, typer.Option()] = "2026-03-02",
    until: Annotated[str, typer.Option()] = "2026-06-21 23:59:59",
    out: Annotated[Path, typer.Option()] = Path(
        "data/intermediate/github_local_evidence.csv"
    ),
) -> None:
    evidence = ingest_local_git_repos(repo_root, since, until)
    write_evidence_csv(out, evidence)
    typer.echo(f"wrote {len(evidence)} local Git evidence rows to {out}")


@draft_app.command("validate")
def validate_command(
    weekly: Annotated[Path, typer.Option()],
    evidence: Annotated[Path, typer.Option()],
    out: Annotated[Path, typer.Option()],
) -> None:
    issues = validate_weekly_csv(weekly, evidence)
    lines = ["# 검증 보고서", ""]
    if len(issues) == 0:
        lines.append("- 오류 없음")
    for issue in issues:
        lines.append(f"- {issue.level}: {issue.message}")
    write_markdown(out, "\n".join(lines) + "\n")
    typer.echo(f"wrote validation report to {out}")


@draft_app.command("enrich-weekly")
def enrich_weekly_command(
    scenario: Annotated[str, typer.Option(help="480 or 640")],
    weekly: Annotated[Path, typer.Option(help="Allocated weekly report CSV")],
    time_ledger: Annotated[Path, typer.Option(help="Time ledger CSV")],
    evidence: Annotated[Path, typer.Option(help="Evidence ledger CSV")],
    calendar: Annotated[Path, typer.Option(help="Calendar seed/export CSV")],
    alog_weekly: Annotated[Path, typer.Option(help="aLog weekly summary CSV")],
    out: Annotated[Path, typer.Option(help="Output directory")],
) -> None:
    match scenario:
        case "480" | "640":
            pass
        case _:
            msg = "--scenario must be 480 or 640"
            raise typer.BadParameter(msg)
    result = enrich_weekly_reports(
        EnrichmentInputs(
            scenario=scenario,
            weekly=weekly,
            time_ledger=time_ledger,
            evidence=evidence,
            calendar=calendar,
            alog_weekly=alog_weekly,
            out_dir=out,
        )
    )
    write_enrichment_outputs(
        out,
        scenario,
        result.rows,
        result.rewrite_logs,
        result.shortage_before,
    )
    typer.echo(f"wrote enriched weekly report to {out}")


def _parse_scenarios(raw: str) -> tuple[Scenario, ...]:
    normalized = raw.strip()
    match normalized:
        case "both":
            return (Scenario.TARGET_480, Scenario.TARGET_640)
        case "480":
            return (Scenario.TARGET_480,)
        case "640":
            return (Scenario.TARGET_640,)
        case _:
            msg = "--scenario must be 480, 640, or both"
            raise typer.BadParameter(msg)
